from django.urls import path
from rest_framework_simplejwt.views import TokenVerifyView

from .views import (
    LoginView,
    RefreshTokenView,
    LogoutView,
    RegisterView,
    ProfileView,
    ChangePasswordView,
    VerifyEmailView,
    ResendVerificationEmailView,
)

app_name = 'accounts'
urlpatterns = [
    # Auth
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),

    #Tokens
    path('auth/token/refresh/', RefreshTokenView.as_view(), name='token-refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token-verify'),

    #Profil
    path('auth/profile/', ProfileView.as_view(), name='profile'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change-password'),

    #Verification des emails
    path('auth/verify-email/<str:uidb64>/<str:token>/', VerifyEmailView.as_view(), name='verify-email'),
    path('auth/resend-verification/', ResendVerificationEmailView.as_view(), name='resend-verification')
]