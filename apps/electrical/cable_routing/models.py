"""
Modèles de l'application Cable Routing.

Représentation des câbles et de leurs tracés dans une installation électrique.

Hiérarchie des modèles :

    CableType           → Définit les caractéristiques d'un type de câble
         ↑
       Cable            → Un câble physique dans l'installation
         ↓
    CableRoute          → Le tracé complet du câble (chemin emprunté)
         ↓
    RouteWaypoint[]     → Les points de passage successifs du tracé

    CablePathway        → Un chemin de câbles physique (chemin en acier,
                          conduit, goulotte...) dans lequel passent les câbles

Exemple concret (projet EPR2) :
    type  = CableType(name="U1000R2V", section=6.0, voltage_max=1000)
    cable = Cable(reference="CAB-EPR-0042", type=type, length=150.5)
    route = CableRoute(cable=cable, total_length=150.5)
    wp1   = RouteWaypoint(route=route, order=1, x=10, y=0, z=3)
    wp2   = RouteWaypoint(route=route, order=2, x=10, y=50, z=3)
    wp3   = RouteWaypoint(route=route, order=3, x=85, y=50, z=0)
"""

from django.db import models
from core.models import ReferencedModel, NamedModel, BaseModel
from core.constants import (
    CABLE_TYPE_CHOICES, CABLE_STATUS_CHOICES,
    CABLE_SECTION_CHOICES, VOLTAGE_CHOICES,
    CABLE_STATUS_PLANNED, CABLE_TYPE_POWER,
    ELECTRICAL_STANDARD_CHOICES, STANDARD_IEC,
)
from core.validators import (
    validate_cable_section, validate_voltage,
    validate_cable_length, validate_positive_number,
)


# ============================================================
# MODÈLE 1 : TYPE DE CÂBLE
# ============================================================

class CableType(ReferencedModel):
    """
    Définit un type de câble avec ses caractéristiques techniques.

    Un CableType est un "modèle" dont peuvent hériter plusieurs câbles.
    Exemple : "U1000R2V 3G6" est un type dont on peut avoir 200 câbles.

    Champs hérités de NamedModel :
    - id, name, description, created_at, updated_at, is_active, is_deleted
    """

    # --- Caractéristiques électriques ---
    cable_category = models.CharField(
        max_length=20,
        choices=CABLE_TYPE_CHOICES,
        default=CABLE_TYPE_POWER,
        verbose_name="Catégorie"
    )
    section_mm2 = models.FloatField(
        validators=[validate_cable_section],
        verbose_name="Section (mm²)",
        help_text="Section nominale selon norme IEC (ex: 1.5, 2.5, 6, 16...)"
    )
    voltage_max = models.IntegerField(
        validators=[validate_voltage],
        default=1000,
        verbose_name="Tension maximale (V)"
    )
    conductor_count = models.PositiveSmallIntegerField(
        default=3,
        verbose_name="Nombre de conducteurs",
        help_text="Ex: 3G6 → 3 conducteurs de 6mm²"
    )
    conductor_material = models.CharField(
        max_length=10,
        choices=[('copper', 'Cuivre'), ('aluminum', 'Aluminium')],
        default='copper',
        verbose_name="Matière conducteur"
    )

    # --- Normes ---
    standard = models.CharField(
        max_length=10,
        choices=ELECTRICAL_STANDARD_CHOICES,
        default=STANDARD_IEC,
        verbose_name="Norme"
    )
    standard_reference = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Référence norme",
        help_text="Ex: IEC 60502-1, NF C 32-102"
    )

    # --- Propriétés physiques ---
    outer_diameter_mm = models.FloatField(
        null=True, blank=True,
        validators=[validate_positive_number],
        verbose_name="Diamètre extérieur (mm)"
    )
    weight_kg_per_m = models.FloatField(
        null=True, blank=True,
        validators=[validate_positive_number],
        verbose_name="Masse linéique (kg/m)"
    )
    min_bending_radius_mm = models.FloatField(
        null=True, blank=True,
        verbose_name="Rayon de courbure minimum (mm)"
    )

    class Meta:
        verbose_name        = "Type de câble"
        verbose_name_plural = "Types de câbles"
        ordering            = ['name']

    def __str__(self):
        return f"{self.name} ({self.section_mm2}mm² - {self.voltage_max}V)"


# ============================================================
# MODÈLE 2 : CHEMIN DE CÂBLES (PATHWAY)
# ============================================================

class CablePathway(ReferencedModel):
    """
    Un chemin de câbles physique dans lequel passent les câbles.

    Types de chemins :
    - Chemin de câbles en acier (le plus courant)
    - Conduit / tube IRO
    - Goulotte
    - Dalle technique
    - Trémie

    Un pathway a une position 3D et une capacité maximale.
    Quand la capacité est atteinte, le routing engine doit chercher un autre chemin.

    Représentation d'un bâtiment :
        [Niveau 0] ──────────── pathway_h1 (horizontal, longueur 80m)
                         |
                    pathway_v1 (vertical, longueur 4m)
                         |
        [Niveau 1] ──────────── pathway_h2 (horizontal, longueur 80m)
    """

    PATHWAY_TYPE_CABLE_TRAY  = 'cable_tray'
    PATHWAY_TYPE_CONDUIT     = 'conduit'
    PATHWAY_TYPE_DUCT        = 'duct'
    PATHWAY_TYPE_TRENCH      = 'trench'
    PATHWAY_TYPE_FREE_AIR    = 'free_air'

    PATHWAY_TYPE_CHOICES = [
        (PATHWAY_TYPE_CABLE_TRAY, 'Chemin de câbles'),
        (PATHWAY_TYPE_CONDUIT,    'Conduit / tube'),
        (PATHWAY_TYPE_DUCT,       'Goulotte'),
        (PATHWAY_TYPE_TRENCH,     'Trémie / fourreau'),
        (PATHWAY_TYPE_FREE_AIR,   'Air libre'),
    ]

    pathway_type = models.CharField(
        max_length=20,
        choices=PATHWAY_TYPE_CHOICES,
        default=PATHWAY_TYPE_CABLE_TRAY,
        verbose_name="Type de chemin"
    )

    # --- Dimensions ---
    width_mm  = models.FloatField(
        default=200,
        validators=[validate_positive_number],
        verbose_name="Largeur (mm)"
    )
    height_mm = models.FloatField(
        default=60,
        validators=[validate_positive_number],
        verbose_name="Hauteur (mm)"
    )

    # --- Capacité ---
    max_fill_ratio = models.FloatField(
        default=0.40,
        verbose_name="Taux de remplissage max",
        help_text="Norme IEC : max 40% de remplissage"
    )

    # --- Position 3D (coordonnées en mètres) ---
    # Point de départ
    start_x = models.FloatField(default=0, verbose_name="Départ X (m)")
    start_y = models.FloatField(default=0, verbose_name="Départ Y (m)")
    start_z = models.FloatField(default=0, verbose_name="Départ Z (m)")

    # Point d'arrivée
    end_x = models.FloatField(default=0, verbose_name="Arrivée X (m)")
    end_y = models.FloatField(default=0, verbose_name="Arrivée Y (m)")
    end_z = models.FloatField(default=0, verbose_name="Arrivée Z (m)")

    # --- Connexions avec d'autres pathways ---
    # Un pathway peut être connecté à d'autres (pour le graphe de routage)
    connected_pathways = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=True,
        verbose_name="Pathways connectés"
    )

    class Meta:
        verbose_name        = "Chemin de câbles"
        verbose_name_plural = "Chemins de câbles"

    @property
    def length_m(self):
        """Calcule la longueur du pathway en mètres."""
        import math
        dx = self.end_x - self.start_x
        dy = self.end_y - self.start_y
        dz = self.end_z - self.start_z
        return round(math.sqrt(dx**2 + dy**2 + dz**2), 2)

    @property
    def cross_section_mm2(self):
        """Surface de la section du chemin de câbles en mm²."""
        return self.width_mm * self.height_mm

    @property
    def usable_section_mm2(self):
        """Surface utilisable selon le taux de remplissage max."""
        return self.cross_section_mm2 * self.max_fill_ratio


# ============================================================
# MODÈLE 3 : CÂBLE
# ============================================================

class Cable(ReferencedModel):
    """
    Un câble physique dans l'installation électrique.

    C'est le modèle central de l'application.
    Il représente un câble réel avec :
    - Ses caractéristiques (type, longueur, statut)
    - Ses extrémités (d'où il part, où il arrive)
    - Son chemin de câbles principal

    Champs hérités de ReferencedModel :
    - id, reference (unique), name, description
    - created_at, updated_at, is_active, is_deleted
    - created_by, updated_by
    """

    # --- Type et caractéristiques ---
    cable_type = models.ForeignKey(
        CableType,
        on_delete=models.PROTECT,  # Interdit de supprimer un type utilisé
        related_name='cables',
        verbose_name="Type de câble"
    )
    status = models.CharField(
        max_length=20,
        choices=CABLE_STATUS_CHOICES,
        default=CABLE_STATUS_PLANNED,
        verbose_name="Statut",
        db_index=True
    )

    # --- Longueur ---
    designed_length_m = models.FloatField(
        null=True, blank=True,
        validators=[validate_cable_length],
        verbose_name="Longueur prévue (m)"
    )
    actual_length_m = models.FloatField(
        null=True, blank=True,
        validators=[validate_cable_length],
        verbose_name="Longueur réelle (m)"
    )

    # --- Extrémités ---
    origin_label = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Origine",
        help_text="Ex: Armoire TGBT-A / Disjoncteur Q3"
    )
    destination_label = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Destination",
        help_text="Ex: Moteur Pompe P-201"
    )

    # --- Localisation ---
    origin_x = models.FloatField(null=True, blank=True, verbose_name="Origine X (m)")
    origin_y = models.FloatField(null=True, blank=True, verbose_name="Origine Y (m)")
    origin_z = models.FloatField(null=True, blank=True, verbose_name="Origine Z (m)")
    dest_x   = models.FloatField(null=True, blank=True, verbose_name="Destination X (m)")
    dest_y   = models.FloatField(null=True, blank=True, verbose_name="Destination Y (m)")
    dest_z   = models.FloatField(null=True, blank=True, verbose_name="Destination Z (m)")

    # --- Données électriques ---
    design_current_a = models.FloatField(
        null=True, blank=True,
        validators=[validate_positive_number],
        verbose_name="Courant de conception (A)"
    )
    operating_voltage = models.IntegerField(
        null=True, blank=True,
        validators=[validate_voltage],
        verbose_name="Tension de service (V)"
    )

    # --- Notes ---
    installation_notes = models.TextField(
        blank=True,
        verbose_name="Notes d'installation"
    )

    class Meta:
        verbose_name        = "Câble"
        verbose_name_plural = "Câbles"
        ordering            = ['reference']

    @property
    def effective_length(self):
        """Retourne la longueur réelle si disponible, sinon la prévue."""
        return self.actual_length_m or self.designed_length_m


# ============================================================
# MODÈLE 4 : TRACÉ D'UN CÂBLE (ROUTE)
# ============================================================

class CableRoute(BaseModel):
    """
    Le tracé complet d'un câble — l'ensemble des points par lesquels il passe.

    Un câble peut n'avoir qu'un seul tracé actif à la fois,
    mais on conserve l'historique des anciens tracés.

    Exemple :
        cable       : CAB-EPR-0042
        total_length: 152.3 m
        is_optimized: True
        waypoints   : [wp1(0,0,3), wp2(0,50,3), wp3(85,50,3), wp4(85,50,0)]
    """

    cable = models.ForeignKey(
        Cable,
        on_delete=models.CASCADE,
        related_name='routes',
        verbose_name="Câble"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Tracé actif"
    )
    is_optimized = models.BooleanField(
        default=False,
        verbose_name="Optimisé"
    )
    total_length_m = models.FloatField(
        null=True, blank=True,
        verbose_name="Longueur totale (m)"
    )
    calculation_notes = models.TextField(
        blank=True,
        verbose_name="Notes de calcul"
    )

    class Meta:
        verbose_name        = "Tracé de câble"
        verbose_name_plural = "Tracés de câbles"
        ordering            = ['-created_at']

    def __str__(self):
        return f"Tracé {self.cable.reference} ({self.total_length_m}m)"


# ============================================================
# MODÈLE 5 : POINT DE PASSAGE (WAYPOINT)
# ============================================================

class RouteWaypoint(BaseModel):
    """
    Un point de passage sur le tracé d'un câble.

    La liste ordonnée des waypoints définit le chemin exact du câble
    dans l'espace 3D du bâtiment.

    Exemple de tracé :
        wp1 : order=1, x=0,   y=0,  z=3  ← départ (armoire)
        wp2 : order=2, x=0,   y=50, z=3  ← virage horizontal
        wp3 : order=3, x=85,  y=50, z=3  ← virage horizontal
        wp4 : order=4, x=85,  y=50, z=0  ← descente verticale (destination)
    """

    route = models.ForeignKey(
        CableRoute,
        on_delete=models.CASCADE,
        related_name='waypoints',
        verbose_name="Tracé"
    )
    order = models.PositiveIntegerField(
        verbose_name="Ordre",
        help_text="Position dans le tracé (1 = départ)"
    )

    # Coordonnées 3D en mètres
    x = models.FloatField(verbose_name="X (m)")
    y = models.FloatField(verbose_name="Y (m)")
    z = models.FloatField(default=0, verbose_name="Z (m)")

    # Pathway emprunté à ce point (optionnel)
    pathway = models.ForeignKey(
        CablePathway,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='waypoints',
        verbose_name="Chemin de câbles"
    )

    label = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Étiquette",
        help_text="Ex: 'Virage armoire A', 'Sortie chemin H1'"
    )

    class Meta:
        verbose_name        = "Point de passage"
        verbose_name_plural = "Points de passage"
        ordering            = ['route', 'order']
        unique_together     = [('route', 'order')]

    def __str__(self):
        return f"WP{self.order} ({self.x}, {self.y}, {self.z})"