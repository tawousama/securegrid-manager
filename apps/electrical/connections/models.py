"""
Modèles de l'application Connections.

Un raccordement électrique décrit COMMENT un câble est physiquement
connecté à ses équipements aux deux extrémités.

Hiérarchie :

    TerminalBlock (bornier)
        └── Terminal (borne individuelle)
                └── ConnectionPoint (point de raccordement d'un conducteur)
                        ↑
                    Connection (le raccordement d'un câble)
                        ↑
                      Cable (le câble raccordé)

Exemple concret (armoire électrique EPR) :
    block    = TerminalBlock(ref="X1-TGBT", description="Bornier départs moteurs")
    terminal = Terminal(block=block, label="X1:3", section_max=10.0, voltage_rating=400)
    cable    = Cable.objects.get(reference="CAB-EPR-0042")
    conn     = Connection(cable=cable, terminal_origin=terminal_A, terminal_dest=terminal_B)
    pt_L1    = ConnectionPoint(connection=conn, conductor="L1", wire_color="brown",
                               tightening_torque_nm=2.5)
"""

from django.db import models
from core.models import ReferencedModel, NamedModel, BaseModel
from core.constants import (
    CONNECTION_TYPE_CHOICES, CONNECTION_TYPE_TERMINAL,
    CABLE_STATUS_CHOICES, CABLE_STATUS_PLANNED,
)
from core.validators import validate_cable_section, validate_voltage, validate_positive_number
from apps.electrical.cable_routing.models import Cable

# ============================================================
# MODÈLE 1 : BORNIER (TERMINAL BLOCK)
# ============================================================

class TerminalBlock(ReferencedModel):
    """
    Un bornier — groupe de bornes physiques dans une armoire ou équipement.

    Exemple : Bornier X1 dans l'armoire TGBT-A contenant 24 bornes.

    Champs hérités de ReferencedModel :
    - id, reference (unique), name, description
    - created_at, updated_at, is_active, is_deleted, created_by
    """

    # Localisation physique
    location = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Localisation",
        help_text="Ex: Armoire TGBT-A, Rangée 3, Position 2"
    )
    equipment_ref = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Référence équipement",
        help_text="Référence de l'armoire ou équipement hôte"
    )

    # Caractéristiques électriques du bornier
    voltage_rating = models.IntegerField(
        default=400,
        validators=[validate_voltage],
        verbose_name="Tension nominale (V)"
    )
    current_rating = models.FloatField(
        default=32.0,
        validators=[validate_positive_number],
        verbose_name="Courant nominal (A)"
    )
    max_section_mm2 = models.FloatField(
        default=16.0,
        validators=[validate_cable_section],
        verbose_name="Section maximale (mm²)"
    )

    # Fabricant et référence commerciale
    manufacturer = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Fabricant",
        help_text="Ex: Phoenix Contact, Wago, Legrand"
    )
    manufacturer_ref = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Référence fabricant"
    )

    class Meta:
        verbose_name        = "Bornier"
        verbose_name_plural = "Borniers"
        ordering            = ['reference']

    def __str__(self):
        return f"{self.reference} — {self.name}"

    @property
    def terminal_count(self):
        """Nombre de bornes dans ce bornier."""
        return self.terminals.count()

    @property
    def available_terminal_count(self):
        """Nombre de bornes disponibles (non raccordées)."""
        return self.terminals.filter(is_occupied=False, is_active=True).count()


# ============================================================
# MODÈLE 2 : BORNE (TERMINAL)
# ============================================================

class Terminal(BaseModel):
    """
    Une borne physique individuelle sur un bornier ou équipement.

    Exemple : Borne X1:3 (bornier X1, position 3).

    Une borne ne peut accueillir qu'un seul conducteur à la fois.
    is_occupied passe à True quand un ConnectionPoint lui est associé.
    """

    TERMINAL_TYPE_SCREW     = 'screw'
    TERMINAL_TYPE_SPRING    = 'spring'
    TERMINAL_TYPE_CRIMP     = 'crimp'
    TERMINAL_TYPE_BUSBAR    = 'busbar'

    TERMINAL_TYPE_CHOICES = [
        (TERMINAL_TYPE_SCREW,  'Borne à vis'),
        (TERMINAL_TYPE_SPRING, 'Borne à ressort (push-in)'),
        (TERMINAL_TYPE_CRIMP,  'Borne à sertir'),
        (TERMINAL_TYPE_BUSBAR, 'Jeu de barres'),
    ]

    block = models.ForeignKey(
        TerminalBlock,
        on_delete=models.CASCADE,
        related_name='terminals',
        verbose_name="Bornier"
    )

    # Identification
    label = models.CharField(
        max_length=50,
        verbose_name="Étiquette",
        help_text="Ex: 'X1:3', 'L1', 'PE', '+24V'"
    )
    position = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Position",
        help_text="Position physique dans le bornier"
    )

    # Caractéristiques
    terminal_type = models.CharField(
        max_length=20,
        choices=TERMINAL_TYPE_CHOICES,
        default=TERMINAL_TYPE_SCREW,
        verbose_name="Type de borne"
    )
    max_section_mm2 = models.FloatField(
        validators=[validate_cable_section],
        verbose_name="Section maximale (mm²)"
    )
    voltage_rating = models.IntegerField(
        validators=[validate_voltage],
        verbose_name="Tension nominale (V)"
    )
    current_rating = models.FloatField(
        validators=[validate_positive_number],
        verbose_name="Courant nominal (A)"
    )

    # Couple de serrage recommandé (pour les bornes à vis)
    recommended_torque_nm = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Couple de serrage recommandé (N·m)"
    )

    # État
    is_occupied = models.BooleanField(
        default=False,
        verbose_name="Occupée",
        db_index=True
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active"
    )

    class Meta:
        verbose_name        = "Borne"
        verbose_name_plural = "Bornes"
        unique_together     = [('block', 'label')]
        ordering            = ['block', 'position']

    def __str__(self):
        return f"{self.block.reference}:{self.label}"


# ============================================================
# MODÈLE 3 : RACCORDEMENT (CONNECTION)
# ============================================================

class Connection(ReferencedModel):
    """
    Un raccordement — la connexion d'un câble à deux terminaux.

    Un raccordement relie :
    - L'extrémité ORIGINE du câble → terminal_origin
    - L'extrémité DESTINATION du câble → terminal_dest

    Statuts du cycle de vie :
    PLANNED → IN_PROGRESS → COMPLETED → VERIFIED
                                ↓
                            FAULTY (si anomalie)
    """

    STATUS_PLANNED     = 'planned'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED   = 'completed'
    STATUS_VERIFIED    = 'verified'
    STATUS_FAULTY      = 'faulty'

    STATUS_CHOICES = [
        (STATUS_PLANNED,     'Planifié'),
        (STATUS_IN_PROGRESS, 'En cours'),
        (STATUS_COMPLETED,   'Réalisé'),
        (STATUS_VERIFIED,    'Vérifié et conforme'),
        (STATUS_FAULTY,      'Défectueux'),
    ]

    # Câble raccordé
    cable = models.ForeignKey(
        Cable,
        on_delete=models.CASCADE,
        related_name='connections',
        verbose_name="Câble"
    )

    # Bornes d'origine et de destination
    terminal_origin = models.ForeignKey(
        Terminal,
        on_delete=models.PROTECT,
        related_name='connections_as_origin',
        verbose_name="Borne origine"
    )
    terminal_dest = models.ForeignKey(
        Terminal,
        on_delete=models.PROTECT,
        related_name='connections_as_dest',
        verbose_name="Borne destination"
    )

    # Type de raccordement
    connection_type = models.CharField(
        max_length=20,
        choices=CONNECTION_TYPE_CHOICES,
        default=CONNECTION_TYPE_TERMINAL,
        verbose_name="Type de raccordement"
    )

    # Statut
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PLANNED,
        verbose_name="Statut",
        db_index=True
    )

    # Dates de réalisation
    completed_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Réalisé le"
    )
    verified_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Vérifié le"
    )
    verified_by = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='verified_connections',
        verbose_name="Vérifié par"
    )

    # Notes
    installation_notes = models.TextField(
        blank=True,
        verbose_name="Notes d'installation"
    )
    fault_description = models.TextField(
        blank=True,
        verbose_name="Description du défaut"
    )

    class Meta:
        verbose_name        = "Raccordement"
        verbose_name_plural = "Raccordements"
        ordering            = ['reference']

    def __str__(self):
        return f"{self.reference} — {self.cable.reference}"

    @property
    def is_complete(self):
        return self.status in [self.STATUS_COMPLETED, self.STATUS_VERIFIED]

    @property
    def is_verified(self):
        return self.status == self.STATUS_VERIFIED


# ============================================================
# MODÈLE 4 : POINT DE RACCORDEMENT (CONNECTION POINT)
# ============================================================

class ConnectionPoint(BaseModel):
    """
    Un point de raccordement précis — un conducteur sur une borne.

    Pour un câble 3G6 (3 conducteurs : L1, N, PE), on a 3 ConnectionPoints :
    - ConnectionPoint(conducteur="L1", couleur="brown",  borne=X1:3)
    - ConnectionPoint(conducteur="N",  couleur="blue",   borne=X1:4)
    - ConnectionPoint(conducteur="PE", couleur="yellow_green", borne=PE_bar)

    Conventions de couleurs (NF C 15-100 / IEC 60446) :
    L1 → Marron (brown)
    L2 → Noir   (black)
    L3 → Gris   (grey)
    N  → Bleu   (blue)
    PE → Vert/Jaune (yellow_green)
    """

    # Conducteurs
    CONDUCTOR_L1  = 'L1'
    CONDUCTOR_L2  = 'L2'
    CONDUCTOR_L3  = 'L3'
    CONDUCTOR_N   = 'N'
    CONDUCTOR_PE  = 'PE'
    CONDUCTOR_PEN = 'PEN'
    CONDUCTOR_P   = '+'
    CONDUCTOR_M   = '-'

    CONDUCTOR_CHOICES = [
        (CONDUCTOR_L1,  'Phase L1'),
        (CONDUCTOR_L2,  'Phase L2'),
        (CONDUCTOR_L3,  'Phase L3'),
        (CONDUCTOR_N,   'Neutre (N)'),
        (CONDUCTOR_PE,  'Terre (PE)'),
        (CONDUCTOR_PEN, 'PEN'),
        (CONDUCTOR_P,   'Positif (+)'),
        (CONDUCTOR_M,   'Négatif (-)'),
    ]

    # Couleurs normalisées IEC 60446
    COLOR_BROWN        = 'brown'
    COLOR_BLACK        = 'black'
    COLOR_GREY         = 'grey'
    COLOR_BLUE         = 'blue'
    COLOR_YELLOW_GREEN = 'yellow_green'
    COLOR_RED          = 'red'
    COLOR_WHITE        = 'white'
    COLOR_ORANGE       = 'orange'

    WIRE_COLOR_CHOICES = [
        (COLOR_BROWN,        'Marron (L1)'),
        (COLOR_BLACK,        'Noir (L2)'),
        (COLOR_GREY,         'Gris (L3)'),
        (COLOR_BLUE,         'Bleu (N)'),
        (COLOR_YELLOW_GREEN, 'Vert/Jaune (PE)'),
        (COLOR_RED,          'Rouge'),
        (COLOR_WHITE,        'Blanc'),
        (COLOR_ORANGE,       'Orange'),
    ]

    # Associations normalisées IEC 60446
    STANDARD_COLORS = {
        CONDUCTOR_L1 : COLOR_BROWN,
        CONDUCTOR_L2 : COLOR_BLACK,
        CONDUCTOR_L3 : COLOR_GREY,
        CONDUCTOR_N  : COLOR_BLUE,
        CONDUCTOR_PE : COLOR_YELLOW_GREEN,
    }

    connection = models.ForeignKey(
        Connection,
        on_delete=models.CASCADE,
        related_name='connection_points',
        verbose_name="Raccordement"
    )
    terminal = models.ForeignKey(
        Terminal,
        on_delete=models.PROTECT,
        related_name='connection_points',
        verbose_name="Borne"
    )

    conductor   = models.CharField(
        max_length=5,
        choices=CONDUCTOR_CHOICES,
        verbose_name="Conducteur"
    )
    wire_color  = models.CharField(
        max_length=20,
        choices=WIRE_COLOR_CHOICES,
        verbose_name="Couleur du fil"
    )
    tightening_torque_nm = models.FloatField(
        null=True, blank=True,
        verbose_name="Couple de serrage réel (N·m)"
    )

    # Ferule (embout de câblage)
    has_ferrule = models.BooleanField(
        default=True,
        verbose_name="Embout de câblage posé"
    )
    ferrule_ref = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Référence embout"
    )

    is_verified = models.BooleanField(
        default=False,
        verbose_name="Point vérifié"
    )

    class Meta:
        verbose_name        = "Point de raccordement"
        verbose_name_plural = "Points de raccordement"
        unique_together     = [('connection', 'conductor')]
        ordering            = ['connection', 'conductor']

    def __str__(self):
        return f"{self.connection.reference} — {self.conductor} ({self.wire_color})"

    @property
    def follows_color_convention(self):
        """Vérifie si la couleur respecte la norme IEC 60446."""
        expected = self.STANDARD_COLORS.get(self.conductor)
        if expected is None:
            return True  # Pas de convention définie → accepté
        return self.wire_color == expected