"""
Serializers de l'application Authentication.

Un serializer fait deux choses :
1. DÉSÉRIALISER  : JSON entrant → validation → objet Python
2. SÉRIALISER    : Objet Python → JSON sortant

Flux complet :
    Client → POST /auth/login/ {"email": "...", "password": "..."}
    → LoginSerializer.is_valid()   # Valide les données
    → LoginSerializer.validated_data  # Données propres
    → AuthService.login()          # Logique métier
    → UserSerializer(user).data    # Formater la réponse
    → {"id": "...", "email": "...", "tokens": {...}}
"""

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User, MFADevice


# ============================================================
# SERIALIZER : AFFICHAGE UTILISATEUR
# ============================================================

class UserSerializer(serializers.ModelSerializer):
    """
    Sérialise un utilisateur pour l'affichage dans l'API.

    Utilisé pour :
    - GET /auth/me/  → Profil de l'utilisateur connecté
    - Réponse après login réussi
    - Liste des utilisateurs (admin)
    """
    full_name = serializers.CharField(read_only=True)
    is_locked = serializers.BooleanField(read_only=True)

    class Meta:
        model  = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'is_active', 'mfa_enabled', 'email_verified',
            'electrical_certified', 'avatar', 'date_joined',
            'last_login', 'is_locked',
        ]
        # Ces champs ne peuvent jamais être modifiés via l'API
        read_only_fields = [
            'id', 'date_joined', 'last_login',
            'mfa_enabled', 'email_verified', 'is_locked',
        ]


class UserPublicSerializer(serializers.ModelSerializer):
    """
    Version publique du profil utilisateur (données minimales).
    Utilisé quand on affiche l'auteur d'un élément.
    """
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model  = User
        fields = ['id', 'full_name', 'role', 'avatar']


# ============================================================
# SERIALIZER : INSCRIPTION
# ============================================================

class RegisterSerializer(serializers.ModelSerializer):
    """
    Valide et crée un nouvel utilisateur.

    Règles de validation :
    - email unique
    - password min 12 caractères + critères Django
    - password2 doit correspondre à password
    """
    password  = serializers.CharField(
        write_only=True,   # Jamais retourné dans la réponse
        required=True,
        validators=[validate_password],  # Règles Django (longueur, complexité)
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model  = User
        fields = [
            'email', 'password', 'password2',
            'first_name', 'last_name'
        ]

    def validate_email(self, value):
        """Vérifie que l'email n'est pas déjà utilisé."""
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError(
                "Un compte avec cet email existe déjà."
            )
        return value.lower()

    def validate(self, attrs):
        """Vérifie que les deux mots de passe correspondent."""
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                'password': "Les mots de passe ne correspondent pas."
            })
        return attrs

    def create(self, validated_data):
        """Crée l'utilisateur (sans le champ password2)."""
        validated_data.pop('password2')
        return User.objects.create_user(**validated_data)


# ============================================================
# SERIALIZER : CONNEXION
# ============================================================

class LoginSerializer(serializers.Serializer):
    """
    Valide les credentials de connexion.

    Note : On hérite de Serializer (pas ModelSerializer)
    car on ne crée pas d'objet en base de données.
    """
    email    = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        """
        Vérifie que l'email + mot de passe sont corrects.
        Retourne l'utilisateur si valide.
        """
        email    = attrs.get('email', '').lower()
        password = attrs.get('password')

        # Chercher l'utilisateur
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "Email ou mot de passe incorrect."
            )

        # Vérifier si le compte est bloqué
        if user.is_locked:
            raise serializers.ValidationError(
                "Compte temporairement bloqué suite à trop de tentatives. "
                "Réessayez dans 30 minutes."
            )

        # Vérifier le mot de passe
        if not user.check_password(password):
            user.increment_failed_attempts()
            raise serializers.ValidationError(
                "Email ou mot de passe incorrect."
            )

        # Vérifier que le compte est actif
        if not user.is_active:
            raise serializers.ValidationError(
                "Ce compte est désactivé. Contactez l'administrateur."
            )

        # Réinitialiser les tentatives échouées
        user.reset_failed_attempts()

        attrs['user'] = user
        return attrs


# ============================================================
# SERIALIZER : CHANGEMENT DE MOT DE PASSE
# ============================================================

class PasswordChangeSerializer(serializers.Serializer):
    """
    Valide le changement de mot de passe.
    L'utilisateur doit fournir son ancien mot de passe.
    """
    old_password  = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password  = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password2 = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate_old_password(self, value):
        """Vérifie que l'ancien mot de passe est correct."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(
                "L'ancien mot de passe est incorrect."
            )
        return value

    def validate(self, attrs):
        """Vérifie que les nouveaux mots de passe correspondent."""
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({
                'new_password': "Les mots de passe ne correspondent pas."
            })
        return attrs


# ============================================================
# SERIALIZERS : MFA
# ============================================================

class MFADeviceSerializer(serializers.ModelSerializer):
    """Affiche un dispositif MFA (sans la clé secrète !)."""
    device_type_label = serializers.CharField(
        source='get_device_type_display',
        read_only=True
    )

    class Meta:
        model  = MFADevice
        fields = [
            'id', 'device_type', 'device_type_label',
            'name', 'is_verified', 'is_primary', 'last_used'
        ]
        read_only_fields = ['id', 'is_verified', 'last_used']


class MFAEnableSerializer(serializers.Serializer):
    """
    Initie l'activation du MFA.
    Retourne le QR Code à scanner avec Google Authenticator.
    """
    device_type = serializers.ChoiceField(
        choices=MFADevice.DEVICE_TYPE_CHOICES,
        default=MFADevice.DEVICE_TYPE_TOTP
    )
    name = serializers.CharField(
        max_length=100,
        default='Mon téléphone'
    )


class MFAVerifySerializer(serializers.Serializer):
    """
    Vérifie un code MFA (6 chiffres).
    Utilisé lors de la connexion ou de l'activation du MFA.
    """
    code = serializers.CharField(
        min_length=6,
        max_length=6,
        help_text="Code à 6 chiffres de votre application d'authentification"
    )

    def validate_code(self, value):
        """Vérifie que le code ne contient que des chiffres."""
        if not value.isdigit():
            raise serializers.ValidationError(
                "Le code doit contenir uniquement des chiffres."
            )
        return value


# ============================================================
# SERIALIZER : MISE À JOUR PROFIL
# ============================================================

class UpdateProfileSerializer(serializers.ModelSerializer):
    """
    Mise à jour du profil utilisateur.
    Seuls certains champs sont modifiables par l'utilisateur.
    """
    class Meta:
        model  = User
        fields = ['first_name', 'last_name', 'avatar']

    def validate_avatar(self, value):
        """Limite la taille de l'avatar à 2 MB."""
        max_size = 2 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                "L'avatar ne peut pas dépasser 2 MB."
            )
        return value