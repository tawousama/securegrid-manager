"""
Mixins réutilisables du projet ElectroSecure Platform.

Un Mixin est une classe Python qui apporte des fonctionnalités spécifiques
sans être un modèle complet. On les "colle" sur les modèles par héritage multiple.

Analogie : Les mixins sont comme des accessoires Lego.
- TimestampMixin    → ajoute une horloge
- SoftDeleteMixin   → ajoute une gomme magique (suppression logique)
- ActivableMixin    → ajoute un interrupteur on/off
- OwnerMixin        → ajoute un badge propriétaire

Usage :
    class Device(TimestampMixin, SoftDeleteMixin, ActivableMixin, models.Model):
        name = models.CharField(max_length=100)
        # Device aura automatiquement :
        # created_at, updated_at (TimestampMixin)
        # is_deleted, deleted_at + méthode delete() (SoftDeleteMixin)
        # is_active + méthodes activate/deactivate() (ActivableMixin)
"""

from django.db import models
from django.utils import timezone
from django.conf import settings

from .managers import SoftDeleteManager, DeletedObjectsManager, ActiveManager


# ============================================================
# MIXIN TIMESTAMPS
# ============================================================

class TimestampMixin(models.Model):
    """
    Ajoute created_at et updated_at automatiquement.

    created_at : rempli UNE SEULE FOIS à la création (auto_now_add)
    updated_at : mis à jour À CHAQUE save() (auto_now)

    Usage :
        class Cable(TimestampMixin, models.Model):
            name = models.CharField(max_length=100)

        cable = Cable.objects.create(name="CAB-001")
        print(cable.created_at)  # 2024-01-15 10:30:00
        print(cable.updated_at)  # 2024-01-15 10:30:00

        cable.name = "CAB-001-V2"
        cable.save()
        print(cable.updated_at)  # 2024-01-15 11:45:00  ← mis à jour !
    """
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Créé le"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Modifié le"
    )

    class Meta:
        abstract = True  # ← Pas de table en base de données


# ============================================================
# MIXIN SOFT DELETE
# ============================================================

class SoftDeleteMixin(models.Model):
    """
    Ajoute la suppression logique (soft delete).

    Pourquoi soft delete ?
    - Conservation des données pour audit/historique
    - Possibilité de restaurer
    - Évite les problèmes de clés étrangères
    - Conformité RGPD (traçabilité)

    Usage :
        cable = Cable.objects.get(id=123)

        cable.delete()                    # Soft delete → is_deleted=True
        cable.hard_delete()               # Vrai delete → ligne supprimée en DB
        cable.restore()                   # Restauration → is_deleted=False

        Cable.objects.all()               # Exclut les supprimés (SoftDeleteManager)
        Cable.all_objects.all()           # Inclut tout
        Cable.deleted_objects.all()       # Seulement les supprimés
    """
    is_deleted = models.BooleanField(
        default=False,
        verbose_name="Supprimé",
        db_index=True  # Index pour des requêtes rapides
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Supprimé le"
    )

    # Managers
    objects         = SoftDeleteManager()   # Par défaut : exclut supprimés
    all_objects     = models.Manager()      # Tout inclus
    deleted_objects = DeletedObjectsManager()  # Seulement supprimés

    def delete(self, using=None, keep_parents=False):
        """
        Surcharge delete() : suppression logique au lieu de physique.
        """
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def hard_delete(self):
        """
        Suppression physique réelle et irréversible.
        """
        super().delete()

    def restore(self):
        """
        Restaure un objet supprimé.
        """
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])

    @property
    def is_alive(self):
        """Retourne True si l'objet n'est pas supprimé."""
        return not self.is_deleted

    class Meta:
        abstract = True


# ============================================================
# MIXIN ACTIVABLE
# ============================================================

class ActivableMixin(models.Model):
    """
    Ajoute la gestion de l'état actif/inactif.

    Différence avec SoftDelete :
    - SoftDelete = suppression (irréversible logiquement)
    - Activable  = état on/off (réversible facilement)

    Usage :
        device = Device.objects.get(id=123)
        device.deactivate()    # is_active = False
        device.activate()      # is_active = True

        Device.objects.active()    # Seulement actifs
        Device.objects.inactive()  # Seulement inactifs
    """
    is_active = models.BooleanField(
        default=True,
        verbose_name="Actif",
        db_index=True
    )

    def activate(self):
        """Active l'objet."""
        self.is_active = True
        self.save(update_fields=['is_active'])

    def deactivate(self):
        """Désactive l'objet."""
        self.is_active = False
        self.save(update_fields=['is_active'])

    def toggle(self):
        """Bascule entre actif et inactif."""
        self.is_active = not self.is_active
        self.save(update_fields=['is_active'])

    @property
    def status_label(self):
        """Retourne un label lisible pour l'état."""
        return "Actif" if self.is_active else "Inactif"

    class Meta:
        abstract = True


# ============================================================
# MIXIN PROPRIÉTAIRE
# ============================================================

class OwnerMixin(models.Model):
    """
    Ajoute la traçabilité du créateur et du modificateur.

    Utile pour :
    - Savoir qui a créé/modifié un objet
    - Permissions basées sur la propriété
    - Audit trail

    Usage :
        cable = Cable.objects.create(
            name="CAB-001",
            created_by=request.user
        )
        print(cable.created_by.username)  # "john_doe"
    """
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created',
        verbose_name="Créé par"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_updated',
        verbose_name="Modifié par"
    )

    class Meta:
        abstract = True


# ============================================================
# MIXIN POUR L'API REST (Serializer)
# ============================================================

class ReadOnlyFieldsMixin:
    """
    Mixin pour les Serializers DRF.
    Rend certains champs en lecture seule automatiquement.

    Usage :
        class CableSerializer(ReadOnlyFieldsMixin, serializers.ModelSerializer):
            read_only_fields = ('id', 'created_at', 'created_by')
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        read_only_fields = getattr(self.Meta, 'read_only_fields', [])
        for field_name in read_only_fields:
            if field_name in self.fields:
                self.fields[field_name].read_only = True


# ============================================================
# MIXIN POUR LES VUES API (ViewSet)
# ============================================================

class AuditMixin:
    """
    Mixin pour les ViewSets DRF.
    Enregistre automatiquement created_by et updated_by.

    Usage :
        class CableViewSet(AuditMixin, viewsets.ModelViewSet):
            queryset = Cable.objects.all()
            serializer_class = CableSerializer
    """

    def perform_create(self, serializer):
        """Enregistre le créateur lors de la création."""
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        """Enregistre le modificateur lors de la mise à jour."""
        serializer.save(updated_by=self.request.user)