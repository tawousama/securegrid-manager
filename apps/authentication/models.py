"""
Modèles de l'application Authentication.

Trois modèles :
- User         → L'utilisateur (remplace le User Django par défaut)
- MFADevice    → Dispositif d'authentification à deux facteurs
- UserSession  → Historique des connexions (audit de sécurité)

Pourquoi remplacer le User Django ?
Le User par défaut utilise 'username' comme identifiant.
On veut utiliser l'email + ajouter des champs métier (rôle, MFA, etc.).

Pour dire à Django d'utiliser notre User :
    # Dans settings/base.py
    AUTH_USER_MODEL = 'authentication.User'
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone

from core.models import BaseModel
from core.constants import USER_ROLE_CHOICES, ROLE_VIEWER


# ============================================================
# MANAGER PERSONNALISÉ POUR LE USER
# ============================================================

class UserManager(BaseUserManager):
    """
    Manager pour créer des utilisateurs via email (pas username).

    Django exige un manager custom quand on remplace AbstractBaseUser.
    Il fournit les méthodes create_user() et create_superuser().
    """

    def create_user(self, email, password=None, **extra_fields):
        """
        Crée un utilisateur standard.

        Usage :
            user = User.objects.create_user(
                email='john@example.com',
                password='SecurePass123!'
            )
        """
        if not email:
            raise ValueError("L'adresse email est obligatoire.")

        email = self.normalize_email(email)  # minuscules, domaine normalisé
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # hash bcrypt automatique
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Crée un superutilisateur (accès admin complet).

        Usage (ligne de commande) :
            python manage.py createsuperuser
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Le superutilisateur doit avoir is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Le superutilisateur doit avoir is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


# ============================================================
# MODÈLE USER PERSONNALISÉ
# ============================================================

class User(AbstractBaseUser, PermissionsMixin):
    """
    Modèle User personnalisé — remplace le User Django par défaut.

    Identifiant : email (pas username)
    Champs ajoutés : role, mfa_enabled, electrical_certified, avatar

    AbstractBaseUser fournit :
    - password (hashé automatiquement)
    - last_login
    - is_active
    - Méthodes : set_password(), check_password()

    PermissionsMixin fournit :
    - is_superuser
    - groups
    - user_permissions
    """

    # --- Identité ---
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    email = models.EmailField(
        unique=True,
        verbose_name="Adresse email"
    )
    first_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Prénom"
    )
    last_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Nom"
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        verbose_name="Avatar"
    )

    # --- Rôle et permissions ---
    role = models.CharField(
        max_length=20,
        choices=USER_ROLE_CHOICES,
        default=ROLE_VIEWER,
        verbose_name="Rôle"
    )

    # --- Statut du compte ---
    is_active = models.BooleanField(
        default=True,
        verbose_name="Compte actif"
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name="Accès admin"
    )

    # --- Sécurité ---
    mfa_enabled = models.BooleanField(
        default=False,
        verbose_name="MFA activé"
    )
    email_verified = models.BooleanField(
        default=False,
        verbose_name="Email vérifié"
    )
    failed_login_attempts = models.PositiveIntegerField(
        default=0,
        verbose_name="Tentatives de connexion échouées"
    )
    locked_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Compte bloqué jusqu'au"
    )

    # --- Certification électrique (Assystem) ---
    electrical_certified = models.BooleanField(
        default=False,
        verbose_name="Certifié électricité"
    )
    certification_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Numéro de certification"
    )

    # --- Dates ---
    date_joined = models.DateTimeField(
        default=timezone.now,
        verbose_name="Date d'inscription"
    )
    last_login = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Dernière connexion"
    )

    # Manager personnalisé
    objects = UserManager()

    # Champ utilisé comme identifiant de connexion
    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name      = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering          = ['-date_joined']

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

    # --- Propriétés calculées ---

    @property
    def full_name(self):
        """Retourne le nom complet de l'utilisateur."""
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.email

    @property
    def is_locked(self):
        """Retourne True si le compte est temporairement bloqué."""
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        return False

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_engineer(self):
        return self.role in ['engineer', 'admin']

    # --- Méthodes ---

    def reset_failed_attempts(self):
        """Réinitialise le compteur de tentatives échouées."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save(update_fields=['failed_login_attempts', 'locked_until'])

    def increment_failed_attempts(self, max_attempts=5, lockout_minutes=30):
        """
        Incrémente le compteur d'échecs.
        Bloque le compte après max_attempts tentatives.
        """
        from datetime import timedelta
        self.failed_login_attempts += 1

        if self.failed_login_attempts >= max_attempts:
            self.locked_until = timezone.now() + timedelta(minutes=lockout_minutes)

        self.save(update_fields=['failed_login_attempts', 'locked_until'])


# ============================================================
# MODÈLE MFA DEVICE
# ============================================================

class MFADevice(BaseModel):
    """
    Dispositif d'authentification à deux facteurs (MFA).

    Un utilisateur peut avoir plusieurs dispositifs :
    - Application TOTP (Google Authenticator, Authy)
    - SMS
    - Email

    Fonctionnement TOTP :
    1. On génère une clé secrète unique (secret_key)
    2. L'utilisateur la scanne avec Google Authenticator
    3. L'app génère un code à 6 chiffres toutes les 30 secondes
    4. On vérifie ce code lors de la connexion
    """

    DEVICE_TYPE_TOTP  = 'totp'
    DEVICE_TYPE_SMS   = 'sms'
    DEVICE_TYPE_EMAIL = 'email'

    DEVICE_TYPE_CHOICES = [
        (DEVICE_TYPE_TOTP,  'Application TOTP (Google Authenticator)'),
        (DEVICE_TYPE_SMS,   'SMS'),
        (DEVICE_TYPE_EMAIL, 'Email'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='mfa_devices',
        verbose_name="Utilisateur"
    )
    device_type = models.CharField(
        max_length=10,
        choices=DEVICE_TYPE_CHOICES,
        default=DEVICE_TYPE_TOTP,
        verbose_name="Type de dispositif"
    )
    name = models.CharField(
        max_length=100,
        default='Mon téléphone',
        verbose_name="Nom du dispositif"
    )
    secret_key = models.CharField(
        max_length=64,
        verbose_name="Clé secrète"
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Vérifié"
    )
    is_primary = models.BooleanField(
        default=False,
        verbose_name="Dispositif principal"
    )
    last_used = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Dernière utilisation"
    )

    class Meta:
        verbose_name        = "Dispositif MFA"
        verbose_name_plural = "Dispositifs MFA"
        unique_together     = [('user', 'device_type', 'name')]

    def __str__(self):
        return f"{self.user.email} - {self.get_device_type_display()}"


# ============================================================
# MODÈLE USER SESSION
# ============================================================

class UserSession(BaseModel):
    """
    Historique des sessions utilisateurs.

    Enregistre chaque connexion pour :
    - Audit de sécurité
    - Détection d'activités suspectes
    - Informations légales

    Données collectées :
    - IP de l'utilisateur
    - Navigateur/OS (user agent)
    - Date/heure de connexion et déconnexion
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name="Utilisateur"
    )
    ip_address = models.GenericIPAddressField(
        verbose_name="Adresse IP"
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name="User Agent (navigateur/OS)"
    )
    location = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Localisation approximative"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Session active"
    )
    logged_out_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Déconnecté le"
    )

    class Meta:
        verbose_name        = "Session utilisateur"
        verbose_name_plural = "Sessions utilisateurs"
        ordering            = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.ip_address} - {self.created_at}"

    def logout(self):
        """Marque la session comme terminée."""
        self.is_active    = False
        self.logged_out_at = timezone.now()
        self.save(update_fields=['is_active', 'logged_out_at'])