"""
Permissions personnalisées du projet ElectroSecure Platform.

Une Permission DRF répond à une question simple :
"Est-ce que cet utilisateur a le droit de faire ça ?"

Django REST Framework appelle has_permission() AVANT la vue,
et has_object_permission() APRÈS avoir récupéré l'objet.

Hiérarchie des contrôles :
    1. Authentification  → L'utilisateur est-il connecté ?
    2. has_permission()  → A-t-il le droit d'accéder à cette vue ?
    3. has_object_permission() → A-t-il le droit sur CET objet précis ?

Usage dans une vue :
    class CableViewSet(viewsets.ModelViewSet):
        permission_classes = [IsAuthenticated, IsEngineerOrReadOnly]
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS
from .constants import ROLE_ADMIN, ROLE_ENGINEER, ROLE_TECHNICIAN, ROLE_VIEWER


# SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS') → lectures seules


# ============================================================
# PERMISSIONS BASÉES SUR LES RÔLES
# ============================================================

class IsAdmin(BasePermission):
    """
    Autorise uniquement les administrateurs.

    Usage :
        # Seulement les admins peuvent accéder
        permission_classes = [IsAuthenticated, IsAdmin]
    """
    message = "Accès réservé aux administrateurs."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            getattr(request.user, 'role', None) == ROLE_ADMIN
        )


class IsEngineerOrAbove(BasePermission):
    """
    Autorise les ingénieurs et administrateurs.

    Usage :
        # Pour créer/modifier des câbles
        permission_classes = [IsAuthenticated, IsEngineerOrAbove]
    """
    message = "Accès réservé aux ingénieurs et administrateurs."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            getattr(request.user, 'role', None) in [ROLE_ENGINEER, ROLE_ADMIN]
        )


class IsTechnicianOrAbove(BasePermission):
    """
    Autorise les techniciens, ingénieurs et administrateurs.

    Usage :
        # Pour valider des raccordements
        permission_classes = [IsAuthenticated, IsTechnicianOrAbove]
    """
    message = "Accès réservé aux techniciens, ingénieurs et administrateurs."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            getattr(request.user, 'role', None) in [
                ROLE_TECHNICIAN, ROLE_ENGINEER, ROLE_ADMIN
            ]
        )


# ============================================================
# PERMISSIONS LECTURE/ÉCRITURE
# ============================================================

class IsEngineerOrReadOnly(BasePermission):
    """
    Lecture pour tous les authentifiés, écriture pour les ingénieurs+.

    Utilisé pour la majorité des ressources du projet :
    - Tout le monde peut consulter les câbles
    - Seuls les ingénieurs peuvent les modifier

    Usage :
        permission_classes = [IsAuthenticated, IsEngineerOrReadOnly]
    """
    message = "La modification est réservée aux ingénieurs."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Lecture autorisée pour tous
        if request.method in SAFE_METHODS:
            return True

        # Écriture seulement pour ingénieurs et admins
        return getattr(request.user, 'role', None) in [ROLE_ENGINEER, ROLE_ADMIN]


class IsOwnerOrReadOnly(BasePermission):
    """
    Lecture pour tous, écriture seulement pour le propriétaire.

    Vérifie que l'utilisateur est le créateur de l'objet.

    Usage :
        permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    Note : Nécessite que le modèle ait un champ 'created_by'.
    """
    message = "Vous ne pouvez modifier que vos propres ressources."

    def has_object_permission(self, request, view, obj):
        # Lecture autorisée pour tous
        if request.method in SAFE_METHODS:
            return True

        # Écriture seulement pour le propriétaire ou un admin
        owner = getattr(obj, 'created_by', None)
        is_owner = owner == request.user
        is_admin = getattr(request.user, 'role', None) == ROLE_ADMIN

        return is_owner or is_admin


# ============================================================
# PERMISSIONS SPÉCIFIQUES AU PROJET
# ============================================================

class CanManageElectricalInstallation(BasePermission):
    """
    Permission pour gérer les installations électriques.
    Requiert d'être ingénieur + avoir la certification électrique.

    Usage :
        # Pour modifier des schémas électriques critiques
        permission_classes = [IsAuthenticated, CanManageElectricalInstallation]
    """
    message = "Vous devez être ingénieur certifié pour gérer les installations électriques."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        is_engineer = getattr(request.user, 'role', None) in [ROLE_ENGINEER, ROLE_ADMIN]
        is_certified = getattr(request.user, 'electrical_certified', False)

        return is_engineer and is_certified


class CanViewAuditLogs(BasePermission):
    """
    Permission pour consulter les logs d'audit.
    Réservé aux administrateurs et ingénieurs seniors.

    Usage :
        permission_classes = [IsAuthenticated, CanViewAuditLogs]
    """
    message = "L'accès aux logs d'audit est restreint."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            getattr(request.user, 'role', None) in [ROLE_ADMIN, ROLE_ENGINEER]
        )


class CanManageUsers(BasePermission):
    """
    Permission pour gérer les utilisateurs.
    Réservé aux administrateurs uniquement.

    Usage :
        permission_classes = [IsAuthenticated, CanManageUsers]
    """
    message = "La gestion des utilisateurs est réservée aux administrateurs."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            getattr(request.user, 'role', None) == ROLE_ADMIN
        )