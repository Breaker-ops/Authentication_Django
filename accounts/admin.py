from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.utils.timezone import now
from django.db.models import Count
from django.db.models.functions import TruncMonth
from datetime import timedelta

User = get_user_model()


@admin.action(description="✅ Activer les comptes sélectionnés")
def activer_comptes(modeladmin, request, queryset):
    updated = queryset.update(is_active=True)
    modeladmin.message_user(request, f"{updated} compte(s) activé(s).")


@admin.action(description="🚫 Désactiver les comptes sélectionnés")
def desactiver_comptes(modeladmin, request, queryset):
    # Empêche de désactiver son propre compte
    queryset = queryset.exclude(pk=request.user.pk)
    updated  = queryset.update(is_active=False)
    modeladmin.message_user(request, f"{updated} compte(s) désactivé(s).")


@admin.action(description="🔑 Réinitialiser le mot de passe (lien console)")
def reinitialiser_mot_de_passe(modeladmin, request, queryset):
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode

    for user in queryset:
        uid   = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        lien  = f"/api/v1/auth/reset-password/{uid}/{token}/"
        modeladmin.message_user(
            request,
            f"Lien pour {user.email} → {lien}"
        )


# ══════════════════════════════════════════════════════════════
# INLINE (si tu ajoutes un profil étendu plus tard)
# ══════════════════════════════════════════════════════════════

# class ProfileInline(admin.StackedInline):
#     model   = Profile
#     extra   = 0
#     can_delete = False


# ══════════════════════════════════════════════════════════════
# USER ADMIN
# ══════════════════════════════════════════════════════════════

@admin.register(User)
class UserAdmin(BaseUserAdmin):

    # ─── Liste ────────────────────────────────────────────────
    list_display    = (
        'email', 'full_name', 'statut_badge',
        'is_staff', 'date_inscription', 'derniere_connexion'
    )
    list_filter     = ('is_active', 'is_staff', 'is_superuser', 'created_at')
    search_fields   = ('email', 'first_name', 'last_name')
    ordering        = ('-created_at',)
    list_per_page   = 25
    actions         = [activer_comptes, desactiver_comptes, reinitialiser_mot_de_passe]

    # ─── Détail ───────────────────────────────────────────────
    fieldsets = (
        ("Identifiants", {
            'fields': ('email', 'password')
        }),
        ("Informations personnelles", {
            'fields': ('first_name', 'last_name')
        }),
        ("Permissions", {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',),
        }),
        ("Dates", {
            'fields': ('last_login', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields  = ('last_login', 'created_at', 'updated_at')

    # ─── Formulaire de création ───────────────────────────────
    add_fieldsets = (
        ("Nouvel utilisateur", {
            'classes': ('wide',),
            'fields':  (
                'email', 'first_name', 'last_name',
                'password1', 'password2', 'is_active', 'is_staff'
            ),
        }),
    )

    # ─── Colonnes calculées ───────────────────────────────────
    @admin.display(description="Statut")
    def statut_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color:#16a34a;font-weight:bold;">● Actif</span>'
            )
        return format_html(
            '<span style="color:#dc2626;font-weight:bold;">● Inactif</span>'
        )

    @admin.display(description="Nom complet")
    def full_name(self, obj):
        return obj.full_name

    @admin.display(description="Inscription", ordering='created_at')
    def date_inscription(self, obj):
        return obj.created_at.strftime("%d/%m/%Y %H:%M")

    @admin.display(description="Dernière connexion", ordering='last_login')
    def derniere_connexion(self, obj):
        if obj.last_login:
            return obj.last_login.strftime("%d/%m/%Y %H:%M")
        return "—"


# ══════════════════════════════════════════════════════════════
# DASHBOARD — STATISTIQUES (vue admin personnalisée)
# ══════════════════════════════════════════════════════════════

from django.contrib.admin import AdminSite
from django.template.response import TemplateResponse


class CustomAdminSite(AdminSite):
    site_header = "Administration — Auth JWT"
    site_title  = "Auth JWT Admin"
    index_title = "Tableau de bord"

    def index(self, request, extra_context=None):
        today = now().date()
        trente_j = now() - timedelta(days=30)
        sept_j = now() - timedelta(days=7)

        # Compteurs globaux
        total_users    = User.objects.count()
        actifs         = User.objects.filter(is_active=True).count()
        inactifs       = User.objects.filter(is_active=False).count()
        admins = User.objects.filter(is_staff=True).count()
        nouveaux_30j   = User.objects.filter(created_at__gte=trente_j).count()
        nouveaux_7j    = User.objects.filter(created_at__gte=sept_j).count()
        connectes_30j  = User.objects.filter(last_login__gte=trente_j).count()

        # ── Inscriptions par mois (6 derniers mois) ───────────
        inscriptions_par_mois = (
            User.objects
            .filter(created_at__gte=now() - timedelta(days=180))
            .annotate(mois=TruncMonth('created_at'))
            .values('mois')
            .annotate(total=Count('id'))
            .order_by('mois')
        )

        # ── Derniers inscrits
        derniers_inscrits = User.objects.order_by('-created_at')[:5]

        extra_context = extra_context or {}
        extra_context.update({
            'total_users':           total_users,
            'actifs':                actifs,
            'inactifs':              inactifs,
            'admins':                admins,
            'nouveaux_30j':          nouveaux_30j,
            'nouveaux_7j':           nouveaux_7j,
            'connectes_30j':         connectes_30j,
            'inscriptions_par_mois': inscriptions_par_mois,
            'derniers_inscrits':     derniers_inscrits,
        })

        return super().index(request, extra_context)