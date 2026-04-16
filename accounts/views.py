from django.contrib.auth import get_user_model
from rest_framework import status, generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from .tokens import email_verification_token
from .utils  import envoyer_email_verification

from .serializers import (
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    UserProfileSerializer,
    UpdateProfileSerializer,
    ChangePasswordSerializer,
)

User = get_user_model()

class LoginView(TokenObtainPairView):
    permission_classes = (AllowAny,)
    serializer_class   = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        return Response({
            'success': True,
            'data': response.data
        }, status=status.HTTP_200_OK)


class RefreshTokenView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        refresh_token = request.data.get('refresh')

        if not refresh_token:
            return Response(
                {'success': False, 'message': "Le refresh token est requis."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            token  = RefreshToken(refresh_token)
            data = {
                'access': str(token.access_token),
            }
            # ROTATE_REFRESH_TOKENS=True → on retourne aussi le nouveau refresh
            if hasattr(token, 'blacklist'):
                token.blacklist()
            new_refresh = RefreshToken.for_user(
                User.objects.get(id=token['user_id'])
            )
            data['refresh'] = str(new_refresh)

            return Response({'success': True, 'data': data}, status=status.HTTP_200_OK)

        except TokenError as e:
            return Response(
                {'success': False, 'message': str(e)},
                status=status.HTTP_401_UNAUTHORIZED
            )

class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        refresh_token = request.data.get('refresh')

        if not refresh_token:
            return Response(
                {'success': False, 'message': "Le refresh token est requis."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {'success': True, 'message': "Déconnexion réussie."},
                status=status.HTTP_200_OK
            )

        except TokenError as e:
            return Response(
                {'success': False, 'message': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return UpdateProfileSerializer
        return UserProfileSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True  # PATCH par défaut
        return super().update(request, *args, **kwargs)


class ChangePasswordView(APIView):
    permission_classes = (IsAuthenticated,)

    def put(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {'success': True, 'message': "Mot de passe modifié avec succès."},
                status=status.HTTP_200_OK
            )
        return Response(
            {'success': False, 'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

# Inscription
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Envoi de l'email de vérification
        try:
            envoyer_email_verification(user, request)
        except Exception as e:
            # On ne bloque pas l'inscription si l'email échoue
            user.delete()
            return Response({
                'success': False,
                'message': f"Erreur lors de l'envoi de l'email : {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'success': True,
            'message': "Compte créé. Vérifiez votre email pour activer votre compte.",
            'data': {
                'email': user.email,
            }
        }, status=status.HTTP_201_CREATED)


# Vérification email
class VerifyEmailView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, uidb64, token):
        try:
            uid  = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {'success': False, 'message': "Lien invalide."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if user.is_active:
            return Response(
                {'success': False, 'message': "Ce compte est déjà activé."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not email_verification_token.check_token(user, token):
            return Response(
                {'success': False, 'message': "Lien expiré ou invalide."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Active le compte
        user.is_active = True
        user.save()

        # Génère les tokens JWT directement
        refresh = RefreshToken.for_user(user)
        return Response({
            'success': True,
            'message': "Email vérifié. Compte activé avec succès.",
            'data': {
                'user':    UserProfileSerializer(user).data,
                'access':  str(refresh.access_token),
                'refresh': str(refresh),
            }
        }, status=status.HTTP_200_OK)


# Renvoi de l'email de vérification 
class ResendVerificationEmailView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        email = request.data.get('email')

        if not email:
            return Response(
                {'success': False, 'message': "Email requis."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Réponse volontairement identique pour ne pas exposer les emails
            return Response(
                {'success': True, 'message': "Si ce compte existe, un email a été envoyé."},
                status=status.HTTP_200_OK
            )

        if user.is_active:
            return Response(
                {'success': False, 'message': "Ce compte est déjà activé."},
                status=status.HTTP_400_BAD_REQUEST
            )

        envoyer_email_verification(user, request)
        return Response(
            {'success': True, 'message': "Email de vérification renvoyé."},
            status=status.HTTP_200_OK
        )