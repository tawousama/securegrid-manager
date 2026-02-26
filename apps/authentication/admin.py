"""
Configuration de l'interface admin Django pour l'authentification.

Accessible sur : http://127.0.0.1:8000/admin/
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, MFADevice, UserSession


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Interface admin pour le modèle User personnalisé."""

    list_display  = ['email', 'full_name', 'role', 'is_active', 'mfa_enabled', 'date_joined']
    list_filter   = ['role', 'is_active', 'mfa_enabled', 'electrical_certified']
    search_fields = ['email', 'first_name', 'last_name']
    ordering      = ['-date_joined']

    fieldsets = (
        ('Identité',     {'fields': ('email', 'first_name', 'last_name', 'avatar')}),
        ('Rôle',         {'fields': ('role', 'electrical_certified', 'certification_number')}),
        ('Sécurité',     {'fields': ('password', 'mfa_enabled', 'email_verified',
                                     'failed_login_attempts', 'locked_until')}),
        ('Permissions',  {'fields': ('is_active', 'is_staff', 'is_superuser',
                                     'groups', 'user_permissions')}),
        ('Dates',        {'fields': ('date_joined', 'last_login')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields':  ('email', 'first_name', 'last_name', 'password1', 'password2', 'role'),
        }),
    )

    # Nécessaire car on utilise email et non username
    filter_horizontal = ('groups', 'user_permissions')


@admin.register(MFADevice)
class MFADeviceAdmin(admin.ModelAdmin):
    list_display  = ['user', 'device_type', 'name', 'is_verified', 'is_primary', 'last_used']
    list_filter   = ['device_type', 'is_verified', 'is_primary']
    search_fields = ['user__email']
    readonly_fields = ['secret_key']  # Ne jamais afficher en clair


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display  = ['user', 'ip_address', 'is_active', 'created_at', 'logged_out_at']
    list_filter   = ['is_active']
    search_fields = ['user__email', 'ip_address']
    readonly_fields = ['user', 'ip_address', 'user_agent', 'created_at']