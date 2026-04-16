from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.conf import settings

from .tokens import email_verification_token


def envoyer_email_verification(user, request=None):
    uid   = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token.make_token(user)

    lien  = f"{settings.FRONTEND_URL}/auth/verify-email/{uid}/{token}/"

    #  Contenu texte 
    texte = f"""
        Bonjour {user.first_name or user.email},

        Merci de vous être inscrit. Veuillez confirmer votre adresse email en cliquant sur le lien ci-dessous :

        {lien}

        Ce lien est valable 24 heures.

        Si vous n'avez pas créé de compte, ignorez cet email.
"""

    # Contenu HTML 
    html = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
        <div style="background:#1d4ed8;padding:24px;border-radius:10px 10px 0 0;text-align:center;">
            <h1 style="color:#fff;margin:0;font-size:1.4rem;">Vérification de votre email</h1>
        </div>
        <div style="background:#f9fafb;padding:32px;border:1px solid #e5e7eb;border-radius:0 0 10px 10px;">
            <p style="color:#374151;">Bonjour <strong>{user.first_name or user.email}</strong>,</p>
            <p style="color:#374151;">
            Merci de vous être inscrit. Cliquez sur le bouton ci-dessous pour activer votre compte.
            </p>
            <div style="text-align:center;margin:32px 0;">
            <a href="{lien}"
                style="background:#1d4ed8;color:#fff;padding:14px 32px;
                        border-radius:8px;text-decoration:none;font-weight:bold;
                        font-size:1rem;">
                Vérifier mon email
            </a>
            </div>
            <p style="color:#6b7280;font-size:.85rem;">
            Ce lien est valable <strong>24 heures</strong>.<br>
            Si vous n'avez pas créé de compte, ignorez cet email.
            </p>
            <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
            <p style="color:#9ca3af;font-size:.75rem;text-align:center;">
            Lien alternatif : <a href="{lien}" style="color:#1d4ed8;">{lien}</a>
            </p>
        </div>
        </body>
        </html>
        """

    email = EmailMultiAlternatives(
        subject    = "Vérifiez votre adresse email",
        body       = texte,
        from_email = settings.DEFAULT_FROM_EMAIL,
        to         = [user.email],
    )
    email.attach_alternative(html, "text/html")
    email.send(fail_silently=False)