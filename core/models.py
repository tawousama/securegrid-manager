"""
Modèles abstraits de base du projet ElectroSecure Platform.

Ces modèles ne créent AUCUNE table en base de données (class Meta: abstract = True).
Ils servent uniquement de "parents" dont les autres modèles héritent.

Hiérarchie d'héritage :
    BaseModel                          → id + timestamps
    ├── SoftDeletableModel             → + soft delete
    │   └── FullFeaturedModel          → + active + owner
    └── NamedModel                     → + name + description
        └── ReferencedModel            → + reference unique

Exemple concret :
    # Avant ce fichier (dans chaque modèle, répété 50 fois)
    class Device(models.Model):
        id         = models.UUIDField(primary_key=True, default=uuid.uuid4)
        created_at = models.DateTimeField(auto_now_add=True)
        updated_at = models.DateTimeField(auto_now=True)
        is_deleted = models.BooleanField(default=False)
        is_active  = models.BooleanField(default=True)
        name       = models.CharField(max_length=255)
        ...

    # Après ce fichier (simple et propre)
    class Device(FullFeaturedModel):
        name = models.CharField(max_length=255)
        # Tout le reste est hérité !
"""

import uuid
from django.db import models

from .mixins import TimestampMixin, SoftDeleteMixin, ActivableMixin, OwnerMixin
from .managers import SoftDeleteManager
from .constants import MAX_NAME_LENGTH, MAX_DESCRIPTION_LENGTH, MAX_REFERENCE_LENGTH


# ============================================================
# MODÈLE 1 : BASE MODEL
# ============================================================

class BaseModel(TimestampMixin):
    """
    Modèle de base minimal pour tous les modèles du projet.

    Fournit :
    - id          : UUID unique (meilleur que l'entier auto pour la sécurité)
    - created_at  : Date/heure de création (automatique)
    - updated_at  : Date/heure de dernière modification (automatique)

    Pourquoi UUID plutôt qu'entier ?
    - Pas de séquence prédictible (sécurité)
    - Pas de collision entre environnements
    - Facilite les migrations de données

    Usage :
        class MyModel(BaseModel):
            name = models.CharField(max_length=100)
            # id, created_at, updated_at sont hérités
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="Identifiant"
    )

    class Meta:
        abstract = True
        ordering = ['-created_at']  # Plus récent en premier par défaut


# ============================================================
# MODÈLE 2 : SOFT DELETABLE MODEL
# ============================================================

class SoftDeletableModel(BaseModel, SoftDeleteMixin):
    """
    Modèle avec soft delete.

    Hérite de :
    - BaseModel      → id, created_at, updated_at
    - SoftDeleteMixin → is_deleted, deleted_at, delete(), restore()

    Usage :
        class AuditLog(SoftDeletableModel):
            action = models.CharField(max_length=100)

        log = AuditLog.objects.create(action="login")
        log.delete()    # Soft delete, pas de perte de données
        log.restore()   # Restauration possible
    """

    class Meta(BaseModel.Meta):
        abstract = True


# ============================================================
# MODÈLE 3 : FULL FEATURED MODEL
# ============================================================

class FullFeaturedModel(SoftDeletableModel, ActivableMixin, OwnerMixin):
    """
    Modèle complet avec toutes les fonctionnalités.
    C'est le modèle de base recommandé pour la majorité des entités.

    Hérite de :
    - BaseModel       → id, created_at, updated_at
    - SoftDeleteMixin → is_deleted, deleted_at, delete(), restore()
    - ActivableMixin  → is_active, activate(), deactivate()
    - OwnerMixin      → created_by, updated_by

    Usage :
        class Device(FullFeaturedModel):
            name = models.CharField(max_length=100)
            ip_address = models.GenericIPAddressField()

        # En utilisation :
        device = Device.objects.create(
            name="Serveur-01",
            ip_address="192.168.1.10",
            created_by=request.user
        )
        device.deactivate()     # Mise hors service
        device.delete()         # Soft delete
        device.restore()        # Restauration
    """

    class Meta(SoftDeletableModel.Meta):
        abstract = True


# ============================================================
# MODÈLE 4 : NAMED MODEL
# ============================================================

class NamedModel(FullFeaturedModel):
    """
    Modèle avec nom et description.
    Pour toutes les entités qui ont un nom lisible.

    Hérite de FullFeaturedModel + ajoute :
    - name        : Nom court (obligatoire)
    - description : Description longue (optionnelle)

    Usage :
        class Project(NamedModel):
            project_type = models.CharField(max_length=50)
            # name, description, id, timestamps, etc. hérités

        project = Project.objects.create(name="EPR2 - Penly")
        print(str(project))  # "EPR2 - Penly"
    """
    name = models.CharField(
        max_length=MAX_NAME_LENGTH,
        verbose_name="Nom"
    )
    description = models.TextField(
        blank=True,
        default='',
        max_length=MAX_DESCRIPTION_LENGTH,
        verbose_name="Description"
    )

    def __str__(self):
        return self.name

    class Meta(FullFeaturedModel.Meta):
        abstract = True


# ============================================================
# MODÈLE 5 : REFERENCED MODEL
# ============================================================

class ReferencedModel(NamedModel):
    """
    Modèle avec référence unique.
    Pour les entités qui ont un code de référence (câbles, équipements, etc.)

    Hérite de NamedModel + ajoute :
    - reference : Code unique de référence

    Usage :
        class Cable(ReferencedModel):
            cable_type = models.CharField(max_length=50)

        cable = Cable.objects.create(
            name="Câble alimentation serveurs",
            reference="CAB-EPR-0042"
        )
        print(str(cable))   # "CAB-EPR-0042 - Câble alimentation serveurs"

        # Recherche par référence
        cable = Cable.objects.get(reference="CAB-EPR-0042")
    """
    reference = models.CharField(
        max_length=MAX_REFERENCE_LENGTH,
        unique=True,
        verbose_name="Référence"
    )

    def __str__(self):
        return f"{self.reference} - {self.name}"

    class Meta(NamedModel.Meta):
        abstract = True


# ============================================================
# MODÈLE 6 : ORDERED MODEL
# ============================================================

class OrderedModel(BaseModel):
    """
    Modèle avec champ d'ordre pour les listes triables.
    Pour les étapes, les phases de projet, etc.

    Usage :
        class ProjectPhase(OrderedModel):
            project = models.ForeignKey(Project, on_delete=models.CASCADE)
            title   = models.CharField(max_length=100)
    """
    order = models.PositiveIntegerField(
        default=0,
        db_index=True,
        verbose_name="Ordre"
    )

    class Meta(BaseModel.Meta):
        abstract = True
        ordering = ['order']