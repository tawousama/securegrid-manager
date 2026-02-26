"""
Générateur automatique de schémas à partir des câbles et connexions.

Principe :
    1. Récupérer tous les câbles d'un projet / zone
    2. Récupérer leurs raccordements (bornes origine/destination)
    3. Créer un élément SchematicElement pour chaque équipement unique
    4. Créer un SchematicLink pour chaque câble entre deux éléments
    5. Positionner les éléments automatiquement (algorithme de layout)

Algorithme de positionnement (Layout) :
    - Colonne gauche  : équipements source (armoires, TGBT)
    - Colonne droite  : équipements destination (moteurs, prises...)
    - Espacement Y    : 20mm entre chaque élément
    - Espacement X    : 150mm entre source et destination
"""

from ..models import Schematic, SchematicElement, SchematicLink


class DiagramGenerator:
    """
    Génère automatiquement un schéma à partir des données métier.

    Usage :
        generator = DiagramGenerator()
        result = generator.generate_from_project(
            schematic=schematic,
            project_ref="EPR2-PENLY"
        )
        # result = {
        #     'elements_created': 12,
        #     'links_created': 8,
        #     'schematic': <Schematic>
        # }
    """

    # Espacement entre éléments (en mm)
    ELEMENT_WIDTH    = 20.0
    ELEMENT_HEIGHT   = 12.0
    MARGIN_X         = 20.0
    MARGIN_Y         = 20.0
    COLUMN_SPACING   = 150.0
    ROW_SPACING      = 25.0

    def generate_from_project(self, schematic: Schematic, project_ref: str) -> dict:
        """
        Génère un schéma complet à partir de la référence projet.

        Récupère tous les câbles du projet et leurs connexions,
        puis construit automatiquement le schéma.

        Args:
            schematic   : Le schéma à peupler
            project_ref : Référence du projet (ex: "EPR2-PENLY")

        Returns:
            dict : Statistiques de génération
        """
        from apps.electrical.cable_routing.models import Cable

        # Récupérer les câbles du projet
        cables = Cable.objects.filter(
            is_active=True,
            is_deleted=False,
        ).select_related('cable_type').prefetch_related('connections')

        # Si project_ref est fourni, filtrer (si le champ existe sur Cable)
        # cables = cables.filter(project_ref=project_ref)  # à activer quand le champ existe

        return self._build_diagram(schematic, cables)

    def generate_from_cables(self, schematic: Schematic, cable_ids: list) -> dict:
        """
        Génère un schéma à partir d'une liste de câbles spécifiques.

        Args:
            schematic : Le schéma à peupler
            cable_ids : Liste d'UUIDs de câbles

        Returns:
            dict : Statistiques de génération
        """
        from apps.electrical.cable_routing.models import Cable

        cables = Cable.objects.filter(
            id__in=cable_ids,
            is_active=True,
        ).select_related('cable_type').prefetch_related('connections')

        return self._build_diagram(schematic, cables)

    # --------------------------------------------------------
    # CONSTRUCTION DU SCHÉMA
    # --------------------------------------------------------

    def _build_diagram(self, schematic: Schematic, cables) -> dict:
        """
        Construit les éléments et liens du schéma à partir des câbles.

        Étapes :
        1. Collecter tous les équipements uniques (origine + destination)
        2. Créer un élément par équipement
        3. Créer un lien par câble entre son origine et sa destination
        4. Positionner les éléments automatiquement
        """
        # Supprimer les éléments existants si on régénère
        schematic.elements.all().delete()
        schematic.links.all().delete()

        # Dictionnaire des éléments créés : label → SchematicElement
        element_map = {}

        # Collecter les équipements uniques
        origins      = set()
        destinations = set()

        for cable in cables:
            if cable.origin_label:
                origins.add(cable.origin_label)
            if cable.destination_label:
                destinations.add(cable.destination_label)

        # Créer les éléments source (colonne gauche)
        for row_idx, origin_label in enumerate(sorted(origins)):
            element = self._create_element(
                schematic    = schematic,
                label        = origin_label,
                element_type = SchematicElement.TYPE_TERMINAL_BLOCK,
                x            = self.MARGIN_X,
                y            = self.MARGIN_Y + row_idx * self.ROW_SPACING,
            )
            element_map[origin_label] = element

        # Créer les éléments destination (colonne droite)
        for row_idx, dest_label in enumerate(sorted(destinations)):
            if dest_label not in element_map:
                element = self._create_element(
                    schematic    = schematic,
                    label        = dest_label,
                    element_type = self._guess_element_type(dest_label),
                    x            = self.MARGIN_X + self.COLUMN_SPACING,
                    y            = self.MARGIN_Y + row_idx * self.ROW_SPACING,
                )
                element_map[dest_label] = element

        # Créer les liens entre éléments
        links_created = 0
        for cable in cables:
            origin_elem = element_map.get(cable.origin_label)
            dest_elem   = element_map.get(cable.destination_label)

            if origin_elem and dest_elem:
                self._create_link(
                    schematic      = schematic,
                    source_element = origin_elem,
                    target_element = dest_elem,
                    cable          = cable,
                )
                links_created += 1

        return {
            'elements_created' : len(element_map),
            'links_created'    : links_created,
            'schematic'        : schematic,
        }

    # --------------------------------------------------------
    # CRÉATION D'ÉLÉMENTS ET LIENS
    # --------------------------------------------------------

    def _create_element(
        self,
        schematic    : Schematic,
        label        : str,
        element_type : str,
        x            : float,
        y            : float,
    ) -> SchematicElement:
        """Crée et sauvegarde un élément du schéma."""
        return SchematicElement.objects.create(
            schematic    = schematic,
            element_type = element_type,
            label        = label,
            x            = x,
            y            = y,
            width        = self.ELEMENT_WIDTH,
            height       = self.ELEMENT_HEIGHT,
        )

    def _create_link(
        self,
        schematic      : Schematic,
        source_element : SchematicElement,
        target_element : SchematicElement,
        cable,
    ) -> SchematicLink:
        """Crée et sauvegarde un lien entre deux éléments."""
        section_label = f"{cable.cable_type.section_mm2}mm²" if cable.cable_type else ""
        label = f"{cable.reference} ({section_label})" if cable.reference else ""

        return SchematicLink.objects.create(
            schematic       = schematic,
            source_element  = source_element,
            target_element  = target_element,
            label           = label,
            linked_cable_id = cable.id,
            line_style      = SchematicLink.STYLE_SOLID,
            waypoints       = [],
        )

    # --------------------------------------------------------
    # UTILITAIRES
    # --------------------------------------------------------

    def _guess_element_type(self, label: str) -> str:
        """
        Devine le type d'élément à partir du label.
        Heuristique simple basée sur les mots-clés courants.
        """
        label_lower = label.lower()

        if any(k in label_lower for k in ['moteur', 'motor', 'pompe', 'pump']):
            return SchematicElement.TYPE_MOTOR
        if any(k in label_lower for k in ['transfo', 'transform']):
            return SchematicElement.TYPE_TRANSFORMER
        if any(k in label_lower for k in ['disj', 'q', 'cb']):
            return SchematicElement.TYPE_CIRCUIT_BREAKER
        if any(k in label_lower for k in ['capteur', 'sensor', 'detect']):
            return SchematicElement.TYPE_SENSOR
        if any(k in label_lower for k in ['borne', 'bornier', 'x']):
            return SchematicElement.TYPE_TERMINAL_BLOCK

        # Par défaut : borne
        return SchematicElement.TYPE_TERMINAL_BLOCK