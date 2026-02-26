"""
Modèles de l'application Schematics.

Un schéma électrique = document graphique représentant une installation.

Cycle de vie d'un schéma :
    DRAFT → REVIEW → APPROVED → OBSOLETE

Chaque approbation crée une nouvelle SchematicRevision pour l'historique.

Exemple concret (projet EPR2 Penly) :
    schematic = Schematic(
        reference="SCH-EPR-0012",
        title="Armoire TGBT-A — Schéma unifilaire",
        schematic_type=Schematic.TYPE_SINGLE_LINE,
        version="Rev.3",
        status=Schematic.STATUS_APPROVED
    )
    element = SchematicElement(
        schematic=schematic,
        element_type=SchematicElement.TYPE_CIRCUIT_BREAKER,
        label="Q1", x=100, y=50
    )
"""

import uuid
from django.db import models
from core.models import ReferencedModel, BaseModel
from core.constants import ELECTRICAL_STANDARD_CHOICES, STANDARD_IEC


# ============================================================
# MODÈLE 1 : SCHÉMA ÉLECTRIQUE
# ============================================================

class Schematic(ReferencedModel):
    """
    Le schéma électrique — métadonnées et cycle de vie.

    Champs hérités de ReferencedModel :
    - id, reference (unique), name, description
    - created_at, updated_at, is_active, is_deleted, created_by, updated_by
    """

    # Types de schémas
    TYPE_SINGLE_LINE   = 'single_line'    # Unifilaire
    TYPE_WIRING        = 'wiring'         # Câblage détaillé
    TYPE_PRINCIPLE     = 'principle'      # Schéma de principe
    TYPE_LAYOUT        = 'layout'         # Implantation physique
    TYPE_LOOP          = 'loop'           # Schéma de boucle (instrumentation)

    TYPE_CHOICES = [
        (TYPE_SINGLE_LINE, 'Unifilaire'),
        (TYPE_WIRING,      'Câblage'),
        (TYPE_PRINCIPLE,   'Principe'),
        (TYPE_LAYOUT,      'Implantation'),
        (TYPE_LOOP,        'Boucle'),
    ]

    # Statuts du cycle de vie
    STATUS_DRAFT    = 'draft'
    STATUS_REVIEW   = 'review'
    STATUS_APPROVED = 'approved'
    STATUS_OBSOLETE = 'obsolete'

    STATUS_CHOICES = [
        (STATUS_DRAFT,    'Brouillon'),
        (STATUS_REVIEW,   'En révision'),
        (STATUS_APPROVED, 'Approuvé'),
        (STATUS_OBSOLETE, 'Obsolète'),
    ]

    # --- Identification ---
    title          = models.CharField(max_length=300, verbose_name="Titre")
    schematic_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES,
        default=TYPE_SINGLE_LINE, verbose_name="Type"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default=STATUS_DRAFT, verbose_name="Statut", db_index=True
    )
    version = models.CharField(
        max_length=20, default='Rev.0', verbose_name="Version"
    )

    # --- Norme et projet ---
    standard = models.CharField(
        max_length=10, choices=ELECTRICAL_STANDARD_CHOICES,
        default=STANDARD_IEC, verbose_name="Norme"
    )
    project_ref = models.CharField(
        max_length=100, blank=True,
        verbose_name="Référence projet",
        help_text="Ex: EPR2-PENLY, HPC-HINKLEY"
    )
    zone = models.CharField(
        max_length=100, blank=True,
        verbose_name="Zone / Bâtiment",
        help_text="Ex: BEP, BK, BR-DDG"
    )

    # --- Format et dimensions ---
    page_width  = models.FloatField(default=297.0, verbose_name="Largeur page (mm)")
    page_height = models.FloatField(default=210.0, verbose_name="Hauteur page (mm)")
    scale       = models.CharField(
        max_length=20, default='1:1', verbose_name="Échelle"
    )

    # --- Dates de cycle de vie ---
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="En révision le")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Approuvé le")
    approved_by = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approved_schematics',
        verbose_name="Approuvé par"
    )

    # --- Fichier source (optionnel) ---
    source_file = models.FileField(
        upload_to='schematics/sources/',
        null=True, blank=True,
        verbose_name="Fichier source (DWG, SVG...)"
    )

    class Meta:
        verbose_name        = "Schéma électrique"
        verbose_name_plural = "Schémas électriques"
        ordering            = ['reference']

    def __str__(self):
        return f"{self.reference} — {self.title} ({self.version})"

    @property
    def element_count(self):
        return self.elements.count()

    @property
    def link_count(self):
        return self.links.count()

    @property
    def is_approved(self):
        return self.status == self.STATUS_APPROVED

    @property
    def is_editable(self):
        return self.status in [self.STATUS_DRAFT, self.STATUS_REVIEW]


# ============================================================
# MODÈLE 2 : ÉLÉMENT DU SCHÉMA (SYMBOLE)
# ============================================================

class SchematicElement(BaseModel):
    """
    Un symbole sur le schéma — représente un équipement électrique.

    Types de symboles :
    - Disjoncteur, fusible, contacteur (protection/commutation)
    - Moteur, transformateur, générateur (machines)
    - Borne, bornier (connexion)
    - Bus, jeu de barres (distribution)
    - Capteur, actionneur (instrumentation)

    Propriétés additionnelles stockées en JSON (properties) :
    {
        "rating": "16A",
        "breaking_capacity": "10kA",
        "manufacturer": "Schneider",
        "reference": "iC60N"
    }
    """

    TYPE_CIRCUIT_BREAKER = 'circuit_breaker'   # Disjoncteur
    TYPE_FUSE            = 'fuse'               # Fusible
    TYPE_CONTACTOR       = 'contactor'          # Contacteur
    TYPE_MOTOR           = 'motor'              # Moteur
    TYPE_TRANSFORMER     = 'transformer'        # Transformateur
    TYPE_GENERATOR       = 'generator'          # Générateur
    TYPE_TERMINAL        = 'terminal'           # Borne
    TYPE_TERMINAL_BLOCK  = 'terminal_block'     # Bornier
    TYPE_BUS             = 'bus'                # Jeu de barres
    TYPE_CABLE           = 'cable'              # Câble (représentation)
    TYPE_SENSOR          = 'sensor'             # Capteur
    TYPE_ACTUATOR        = 'actuator'           # Actionneur
    TYPE_LAMP            = 'lamp'               # Voyant / lampe
    TYPE_SWITCH          = 'switch'             # Interrupteur
    TYPE_SOCKET          = 'socket'             # Prise de courant
    TYPE_EARTH           = 'earth'              # Terre
    TYPE_TEXT            = 'text'               # Texte libre
    TYPE_FRAME           = 'frame'              # Cadre / cartouche

    ELEMENT_TYPE_CHOICES = [
        (TYPE_CIRCUIT_BREAKER, 'Disjoncteur'),
        (TYPE_FUSE,            'Fusible'),
        (TYPE_CONTACTOR,       'Contacteur'),
        (TYPE_MOTOR,           'Moteur'),
        (TYPE_TRANSFORMER,     'Transformateur'),
        (TYPE_GENERATOR,       'Générateur'),
        (TYPE_TERMINAL,        'Borne'),
        (TYPE_TERMINAL_BLOCK,  'Bornier'),
        (TYPE_BUS,             'Jeu de barres'),
        (TYPE_CABLE,           'Câble'),
        (TYPE_SENSOR,          'Capteur'),
        (TYPE_ACTUATOR,        'Actionneur'),
        (TYPE_LAMP,            'Voyant / Lampe'),
        (TYPE_SWITCH,          'Interrupteur'),
        (TYPE_SOCKET,          'Prise de courant'),
        (TYPE_EARTH,           'Terre'),
        (TYPE_TEXT,            'Texte'),
        (TYPE_FRAME,           'Cadre'),
    ]

    schematic    = models.ForeignKey(
        Schematic, on_delete=models.CASCADE,
        related_name='elements', verbose_name="Schéma"
    )

    # Type et identification
    element_type = models.CharField(
        max_length=30, choices=ELEMENT_TYPE_CHOICES,
        verbose_name="Type d'élément"
    )
    label = models.CharField(
        max_length=100, blank=True,
        verbose_name="Étiquette",
        help_text="Ex: 'Q1', 'M-201', 'X1:3'"
    )
    description = models.CharField(
        max_length=300, blank=True,
        verbose_name="Description"
    )

    # Position et dimensions (en mm sur la page)
    x      = models.FloatField(default=0, verbose_name="Position X (mm)")
    y      = models.FloatField(default=0, verbose_name="Position Y (mm)")
    width  = models.FloatField(default=10, verbose_name="Largeur (mm)")
    height = models.FloatField(default=10, verbose_name="Hauteur (mm)")

    # Rotation (en degrés)
    rotation = models.FloatField(default=0, verbose_name="Rotation (°)")

    # Propriétés techniques (JSON libre)
    properties = models.JSONField(
        default=dict, blank=True,
        verbose_name="Propriétés techniques",
        help_text='Ex: {"rating": "16A", "manufacturer": "Schneider"}'
    )

    # Lien vers les modèles métier (optionnel)
    linked_cable_id      = models.UUIDField(null=True, blank=True, verbose_name="Câble lié")
    linked_terminal_id   = models.UUIDField(null=True, blank=True, verbose_name="Borne liée")
    linked_connection_id = models.UUIDField(null=True, blank=True, verbose_name="Raccordement lié")

    # Style visuel
    color       = models.CharField(max_length=20, default='#000000', verbose_name="Couleur")
    font_size   = models.FloatField(default=3.0, verbose_name="Taille police (mm)")
    is_visible  = models.BooleanField(default=True, verbose_name="Visible")

    class Meta:
        verbose_name        = "Élément de schéma"
        verbose_name_plural = "Éléments de schéma"
        ordering            = ['schematic', 'y', 'x']

    def __str__(self):
        return f"{self.schematic.reference} — {self.label} ({self.element_type})"


# ============================================================
# MODÈLE 3 : LIEN ENTRE ÉLÉMENTS
# ============================================================

class SchematicLink(BaseModel):
    """
    Un lien graphique entre deux éléments du schéma.

    Représente généralement un câble ou une connexion électrique.
    Peut être associé à un câble réel de la base de données.

    Styles de ligne :
    - Solide : connexion standard
    - Pointillé : connexion de commande / signal
    - Tiret-point : limite de batterie / zone
    """

    STYLE_SOLID   = 'solid'
    STYLE_DASHED  = 'dashed'
    STYLE_DOTTED  = 'dotted'
    STYLE_DASHDOT = 'dashdot'

    STYLE_CHOICES = [
        (STYLE_SOLID,   'Trait plein'),
        (STYLE_DASHED,  'Tirets'),
        (STYLE_DOTTED,  'Pointillés'),
        (STYLE_DASHDOT, 'Tiret-point'),
    ]

    schematic      = models.ForeignKey(
        Schematic, on_delete=models.CASCADE,
        related_name='links', verbose_name="Schéma"
    )
    source_element = models.ForeignKey(
        SchematicElement, on_delete=models.CASCADE,
        related_name='links_from', verbose_name="Élément source"
    )
    target_element = models.ForeignKey(
        SchematicElement, on_delete=models.CASCADE,
        related_name='links_to', verbose_name="Élément cible"
    )

    # Style visuel
    line_style  = models.CharField(
        max_length=10, choices=STYLE_CHOICES,
        default=STYLE_SOLID, verbose_name="Style de ligne"
    )
    line_width  = models.FloatField(default=0.5, verbose_name="Épaisseur (mm)")
    color       = models.CharField(max_length=20, default='#000000', verbose_name="Couleur")
    label       = models.CharField(max_length=100, blank=True, verbose_name="Étiquette")

    # Lien vers un câble réel (optionnel)
    linked_cable_id = models.UUIDField(
        null=True, blank=True, verbose_name="Câble lié"
    )

    # Points de passage du lien (JSON : liste de {x, y})
    waypoints = models.JSONField(
        default=list, blank=True,
        verbose_name="Points de passage",
        help_text='Ex: [{"x": 50, "y": 30}, {"x": 50, "y": 80}]'
    )

    class Meta:
        verbose_name        = "Lien de schéma"
        verbose_name_plural = "Liens de schéma"
        ordering            = ['schematic']

    def __str__(self):
        return (
            f"{self.schematic.reference} — "
            f"{self.source_element.label} → {self.target_element.label}"
        )


# ============================================================
# MODÈLE 4 : RÉVISION DU SCHÉMA
# ============================================================

class SchematicRevision(BaseModel):
    """
    Historique des révisions d'un schéma.

    Chaque modification significative crée une révision.
    Permet la traçabilité complète (exigence nucléaire).

    Exemple :
        Rev.0 — Création initiale
        Rev.1 — Ajout disjoncteur Q4 suite à modification projet
        Rev.2 — Correction tension suite à retour client
        Rev.3 — Approuvé pour exécution
    """

    schematic   = models.ForeignKey(
        Schematic, on_delete=models.CASCADE,
        related_name='revisions', verbose_name="Schéma"
    )
    version     = models.CharField(max_length=20, verbose_name="Version")
    description = models.TextField(verbose_name="Description des modifications")
    author      = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True, related_name='schematic_revisions',
        verbose_name="Auteur"
    )
    # Snapshot JSON du schéma à ce moment (pour l'historique complet)
    snapshot    = models.JSONField(
        default=dict, blank=True,
        verbose_name="Snapshot du schéma"
    )

    class Meta:
        verbose_name        = "Révision de schéma"
        verbose_name_plural = "Révisions de schémas"
        ordering            = ['schematic', '-created_at']
        unique_together     = [('schematic', 'version')]

    def __str__(self):
        return f"{self.schematic.reference} — {self.version}"