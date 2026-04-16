from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()

# JWT Payload personnalisé
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Ajoute des claims supplémentaires dans le payload du token."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email']      = user.email
        token['full_name']  = user.full_name
        token['is_staff']   = user.is_staff
        return token


# Inscription
class RegisterSerializer(serializers.ModelSerializer):

    password  = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model  = User
        fields = ('email', 'first_name', 'last_name', 'password', 'password2')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError(
                {'password': "Les deux mots de passe ne correspondent pas."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        # is_active=False jusqu'à vérification email
        user = User.objects.create_user(is_active=False, **validated_data)
        return user

#Profil (lecture)
class UserProfileSerializer(serializers.ModelSerializer):

    full_name = serializers.CharField(read_only=True)

    class Meta:
        model  = User
        fields = (
            'id', 'email', 'first_name', 'last_name',
            'full_name', 'is_staff', 'created_at',
        )
        read_only_fields = ('id', 'email', 'is_staff', 'created_at')


# Mise à jour du profil
class UpdateProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model  = User
        fields = ('first_name', 'last_name')

    def update(self, instance, validated_data):
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name  = validated_data.get('last_name',  instance.last_name)
        instance.save()
        return instance


#Changement de mot de passe
class ChangePasswordSerializer(serializers.Serializer):

    old_password  = serializers.CharField(required=True, write_only=True)
    new_password  = serializers.CharField(
        required=True, write_only=True, validators=[validate_password]
    )
    new_password2 = serializers.CharField(required=True, write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Mot de passe actuel incorrect.")
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError(
                {'new_password': "Les deux nouveaux mots de passe ne correspondent pas."}
            )
        return attrs

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user