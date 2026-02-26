"""
Managers personnalisés du projet ElectroSecure Platform.

Un Manager est la classe qui gère les requêtes QuerySet vers la base de données.
Par défaut, Django utilise models.Manager qui expose objects.all(), objects.filter()...

Pourquoi des managers personnalisés ?
- Ajouter des filtres par défaut (ex: exclure les éléments supprimés)
- Ajouter des méthodes de requête réutilisables
- Centraliser la logique de filtrage
- Éviter les bugs dus aux oublis de filtre

Exemple concret sans manager custom :
    # À écrire dans CHAQUE vue, CHAQUE fois → source de bugs
    devices = Device.objects.filter(is_deleted=False, is_active=True)

Exemple avec manager custom :
    # Le filtre est appliqué automatiquement partout
    devices = Device.objects.all()
"""

from django.db import models
from django.utils import timezone


# ============================================================
# MANAGER POUR SOFT DELETE
# ============================================================

class SoftDeleteQuerySet(models.QuerySet):
    """
    QuerySet personnalisé qui ajoute des méthodes de soft delete.

    Un QuerySet est le résultat d'une requête (ex: Device.objects.all()).
    On peut chaîner des méthodes : Device.objects.active().by_type('server')
    """

    def delete(self):
        """
        Surcharge delete() pour faire une suppression logique
        sur tout un QuerySet en une seule requête SQL.

        Au lieu de :
            DELETE FROM devices WHERE id IN (...)
        Exécute :
            UPDATE devices SET is_deleted=True, deleted_at=NOW() WHERE id IN (...)
        """
        return self.update(
            is_deleted=True,
            deleted_at=timezone.now()
        )

    def hard_delete(self):
        """
        Suppression physique réelle (irréversible).
        À utiliser avec précaution.
        """
        return super().delete()

    def alive(self):
        """Retourne uniquement les objets non supprimés."""
        return self.filter(is_deleted=False)

    def dead(self):
        """Retourne uniquement les objets supprimés."""
        return self.filter(is_deleted=True)

    def restore(self):
        """Restaure tous les objets supprimés du QuerySet."""
        return self.update(
            is_deleted=False,
            deleted_at=None
        )


class SoftDeleteManager(models.Manager):
    """
    Manager qui exclut automatiquement les objets supprimés.

    Usage dans un modèle :
        class Device(BaseModel):
            objects     = SoftDeleteManager()       # Exclut supprimés
            all_objects = models.Manager()          # Inclut tout
            deleted     = DeletedObjectsManager()   # Seulement supprimés

        # Dans le code :
        Device.objects.all()          # → Seulement non supprimés
        Device.all_objects.all()      # → Tous les devices
        Device.deleted.all()          # → Seulement supprimés
    """

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()

    def delete(self, *args, **kwargs):
        """Soft delete en masse."""
        return self.get_queryset().delete()


class DeletedObjectsManager(models.Manager):
    """
    Manager qui retourne SEULEMENT les objets supprimés.
    Utile pour l'interface d'administration ou la restauration.
    """

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).dead()


# ============================================================
# MANAGER POUR OBJETS ACTIFS
# ============================================================

class ActiveManager(models.Manager):
    """
    Manager qui filtre automatiquement sur is_active=True.

    Usage :
        class Cable(BaseModel):
            objects = ActiveManager()

        Cable.objects.all()  # → Seulement les câbles actifs
    """

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class ActiveQuerySet(models.QuerySet):
    """
    QuerySet avec méthodes utilitaires pour l'état actif/inactif.
    """

    def active(self):
        """Filtre les objets actifs."""
        return self.filter(is_active=True)

    def inactive(self):
        """Filtre les objets inactifs."""
        return self.filter(is_active=False)

    def activate(self):
        """Active tous les objets du QuerySet."""
        return self.update(is_active=True)

    def deactivate(self):
        """Désactive tous les objets du QuerySet."""
        return self.update(is_active=False)


# ============================================================
# MANAGER COMBINÉ (Soft Delete + Active)
# ============================================================

class BaseManager(models.Manager):
    """
    Manager de base combinant soft delete et filtre actif.

    Applique automatiquement :
    - is_deleted=False  (exclut les supprimés)
    - is_active=True    (seulement les actifs)

    C'est le manager par défaut recommandé pour la majorité des modèles.

    Usage :
        class Project(BaseModel):
            objects = BaseManager()
    """

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(is_deleted=False, is_active=True)
        )


class BaseQuerySet(models.QuerySet):
    """
    QuerySet de base avec toutes les méthodes utilitaires.
    Combinaison de SoftDeleteQuerySet et ActiveQuerySet.
    """

    # --- Soft Delete ---
    def delete(self):
        return self.update(
            is_deleted=True,
            deleted_at=timezone.now()
        )

    def hard_delete(self):
        return super().delete()

    def alive(self):
        return self.filter(is_deleted=False)

    def dead(self):
        return self.filter(is_deleted=True)

    def restore(self):
        return self.update(is_deleted=False, deleted_at=None)

    # --- Active ---
    def active(self):
        return self.filter(is_active=True)

    def inactive(self):
        return self.filter(is_active=False)

    def activate(self):
        return self.update(is_active=True)

    def deactivate(self):
        return self.update(is_active=False)