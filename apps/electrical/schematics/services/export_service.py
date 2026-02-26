"""
Service d'export des schémas électriques.

Formats supportés :
- SVG  : Scalable Vector Graphics (vectoriel, impression haute qualité)
- JSON : Données structurées pour le frontend interactif
- CSV  : Liste des éléments et liens (tableur de vérification)

SVG (Scalable Vector Graphics) :
    Format vectoriel XML — les formes sont décrites mathématiquement.
    Avantages :
    - Pas de perte de qualité à n'importe quel zoom
    - Lisible et modifiable en texte
    - Supporté par tous les navigateurs
    - Taille de fichier raisonnable
"""

import csv
import json
import io
from ..models import Schematic, SchematicElement, SchematicLink


class ExportService:
    """
    Exporte un schéma dans différents formats.

    Usage :
        service = ExportService()
        svg_content  = service.export_to_svg(schematic)
        json_content = service.export_to_json(schematic)
        csv_content  = service.export_to_csv(schematic)
    """

    # Symboles SVG par type d'élément
    # Chaque symbole est dessiné dans une boîte de 20×12mm
    SVG_SYMBOLS = {
        SchematicElement.TYPE_CIRCUIT_BREAKER: '''
            <rect x="0" y="2" width="20" height="8" fill="white" stroke="black" stroke-width="0.5"/>
            <line x1="5" y1="6" x2="8" y2="2" stroke="black" stroke-width="0.5"/>
            <line x1="8" y1="2" x2="12" y2="10" stroke="black" stroke-width="0.5"/>
            <line x1="12" y1="10" x2="15" y2="6" stroke="black" stroke-width="0.5"/>
        ''',
        SchematicElement.TYPE_MOTOR: '''
            <circle cx="10" cy="6" r="6" fill="white" stroke="black" stroke-width="0.5"/>
            <text x="10" y="8" text-anchor="middle" font-size="5" font-family="Arial">M</text>
        ''',
        SchematicElement.TYPE_TRANSFORMER: '''
            <circle cx="6" cy="6" r="4" fill="white" stroke="black" stroke-width="0.5"/>
            <circle cx="14" cy="6" r="4" fill="white" stroke="black" stroke-width="0.5"/>
        ''',
        SchematicElement.TYPE_TERMINAL_BLOCK: '''
            <rect x="2" y="2" width="16" height="8" fill="white" stroke="black" stroke-width="0.5"/>
            <line x1="2" y1="6" x2="18" y2="6" stroke="black" stroke-width="0.3"/>
        ''',
        SchematicElement.TYPE_FUSE: '''
            <rect x="4" y="4" width="12" height="4" fill="white" stroke="black" stroke-width="0.5"/>
            <line x1="0" y1="6" x2="4" y2="6" stroke="black" stroke-width="0.5"/>
            <line x1="16" y1="6" x2="20" y2="6" stroke="black" stroke-width="0.5"/>
        ''',
    }

    DEFAULT_SYMBOL = '''
        <rect x="2" y="2" width="16" height="8" fill="white" stroke="black" stroke-width="0.5"/>
    '''

    # --------------------------------------------------------
    # EXPORT SVG
    # --------------------------------------------------------

    def export_to_svg(self, schematic: Schematic) -> str:
        """
        Génère le SVG complet du schéma.

        Coordonnées : en mm, converties en pixels (1mm = 3.78px)
        Viewbox : correspond aux dimensions de la page du schéma.

        Returns:
            str : Contenu SVG complet
        """
        MM_TO_PX = 3.7795  # Facteur de conversion mm → pixels (96 DPI)

        w = schematic.page_width  * MM_TO_PX
        h = schematic.page_height * MM_TO_PX

        lines = [
            f'<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg"',
            f'     width="{w:.1f}px" height="{h:.1f}px"',
            f'     viewBox="0 0 {w:.1f} {h:.1f}">',
            f'  <!-- ElectroSecure Platform — {schematic.reference} -->',
            f'  <!-- {schematic.title} — {schematic.version} -->',
            f'  <defs>',
            f'    <style>',
            f'      .element-label {{ font-family: Arial, sans-serif; font-size: 8px; }}',
            f'      .link-label   {{ font-family: Arial, sans-serif; font-size: 6px; fill: #444; }}',
            f'      .title-text   {{ font-family: Arial, sans-serif; font-size: 10px; font-weight: bold; }}',
            f'    </style>',
            f'  </defs>',
            f'',
            f'  <!-- Contour de la page -->',
            f'  <rect x="1" y="1" width="{w-2:.1f}" height="{h-2:.1f}"',
            f'        fill="white" stroke="#ccc" stroke-width="1"/>',
            f'',
            f'  <!-- Cartouche -->',
            f'  {self._svg_title_block(schematic, w, h, MM_TO_PX)}',
            f'',
            f'  <!-- Liens (dessinés avant les éléments pour être en dessous) -->',
        ]

        # Liens
        elements = list(schematic.elements.all())
        elem_map = {e.id: e for e in elements}

        for link in schematic.links.all():
            src = link.source_element
            tgt = link.target_element
            lines.append(self._svg_link(src, tgt, link, MM_TO_PX))

        lines.append('')
        lines.append('  <!-- Éléments -->'.strip())

        # Éléments
        for element in elements:
            if element.is_visible:
                lines.append(self._svg_element(element, MM_TO_PX))

        lines.append('</svg>')
        return '\n'.join(lines)

    def _svg_element(self, element: SchematicElement, scale: float) -> str:
        """Génère le SVG d'un élément (symbole + label)."""
        x  = element.x * scale
        y  = element.y * scale
        w  = element.width  * scale
        h  = element.height * scale
        lx = x + w / 2
        ly = y + h + 5 * scale / 10

        symbol = self.SVG_SYMBOLS.get(element.element_type, self.DEFAULT_SYMBOL)

        return (
            f'  <g transform="translate({x:.1f},{y:.1f}) scale({scale:.4f})"'
            f' id="elem-{element.id}">\n'
            f'    {symbol}\n'
            f'  </g>\n'
            f'  <text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle"'
            f' class="element-label">{element.label}</text>'
        )

    def _svg_link(
        self,
        source : SchematicElement,
        target : SchematicElement,
        link   : SchematicLink,
        scale  : float
    ) -> str:
        """Génère le SVG d'un lien entre deux éléments."""
        x1 = (source.x + source.width)  * scale
        y1 = (source.y + source.height / 2) * scale
        x2 = target.x * scale
        y2 = (target.y + target.height / 2) * scale
        mx = (x1 + x2) / 2  # point milieu pour le label
        my = (y1 + y2) / 2

        dash = ''
        if link.line_style == SchematicLink.STYLE_DASHED:
            dash = ' stroke-dasharray="4,2"'
        elif link.line_style == SchematicLink.STYLE_DOTTED:
            dash = ' stroke-dasharray="1,2"'

        lw = link.line_width * scale

        svg = (
            f'  <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"'
            f' stroke="{link.color}" stroke-width="{lw:.2f}"{dash}/>'
        )
        if link.label:
            svg += (
                f'\n  <text x="{mx:.1f}" y="{my - 2:.1f}"'
                f' text-anchor="middle" class="link-label">{link.label}</text>'
            )
        return svg

    def _svg_title_block(
        self, schematic: Schematic, w: float, h: float, scale: float
    ) -> str:
        """Génère le cartouche du schéma en bas à droite."""
        bw, bh = 120 * scale, 25 * scale
        bx = w - bw - 2
        by = h - bh - 2
        return (
            f'<g id="title-block">'
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}"'
            f' fill="white" stroke="black" stroke-width="0.5"/>'
            f'<text x="{bx+4:.1f}" y="{by+9:.1f}" class="title-text">{schematic.reference}</text>'
            f'<text x="{bx+4:.1f}" y="{by+16:.1f}" class="element-label">{schematic.title}</text>'
            f'<text x="{bx+4:.1f}" y="{by+22:.1f}" class="element-label">'
            f'{schematic.version} | {schematic.standard}</text>'
            f'</g>'
        )

    # --------------------------------------------------------
    # EXPORT JSON
    # --------------------------------------------------------

    def export_to_json(self, schematic: Schematic) -> str:
        """
        Exporte le schéma en JSON structuré pour le frontend.

        Format compatible avec des librairies de schémas interactifs
        comme draw.io, JointJS, Cytoscape.js.

        Returns:
            str : JSON sérialisé
        """
        elements = [
            {
                'id'          : str(e.id),
                'type'        : e.element_type,
                'label'       : e.label,
                'description' : e.description,
                'position'    : {'x': e.x, 'y': e.y},
                'size'        : {'width': e.width, 'height': e.height},
                'rotation'    : e.rotation,
                'properties'  : e.properties,
                'color'       : e.color,
                'visible'     : e.is_visible,
                'linked_cable': str(e.linked_cable_id) if e.linked_cable_id else None,
            }
            for e in schematic.elements.filter(is_visible=True)
        ]

        links = [
            {
                'id'          : str(lk.id),
                'source'      : str(lk.source_element_id),
                'target'      : str(lk.target_element_id),
                'label'       : lk.label,
                'style'       : lk.line_style,
                'line_width'  : lk.line_width,
                'color'       : lk.color,
                'waypoints'   : lk.waypoints,
                'linked_cable': str(lk.linked_cable_id) if lk.linked_cable_id else None,
            }
            for lk in schematic.links.all()
        ]

        data = {
            'schematic': {
                'id'        : str(schematic.id),
                'reference' : schematic.reference,
                'title'     : schematic.title,
                'type'      : schematic.schematic_type,
                'version'   : schematic.version,
                'status'    : schematic.status,
                'page'      : {
                    'width'  : schematic.page_width,
                    'height' : schematic.page_height,
                    'scale'  : schematic.scale,
                },
            },
            'elements' : elements,
            'links'    : links,
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    # --------------------------------------------------------
    # EXPORT CSV
    # --------------------------------------------------------

    def export_to_csv(self, schematic: Schematic) -> str:
        """
        Exporte le schéma en CSV (deux feuilles : éléments + liens).

        Utilisé pour les vérifications en tableur.

        Returns:
            str : Contenu CSV des éléments
        """
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')

        # En-tête
        writer.writerow([
            'Référence schéma', 'Titre', 'Version', 'Statut'
        ])
        writer.writerow([
            schematic.reference, schematic.title,
            schematic.version, schematic.get_status_display()
        ])
        writer.writerow([])

        # Section éléments
        writer.writerow(['=== ÉLÉMENTS ==='])
        writer.writerow(['ID', 'Type', 'Label', 'Description', 'X', 'Y', 'Câble lié'])
        for elem in schematic.elements.order_by('y', 'x'):
            writer.writerow([
                str(elem.id)[:8],
                elem.get_element_type_display(),
                elem.label,
                elem.description,
                elem.x,
                elem.y,
                str(elem.linked_cable_id)[:8] if elem.linked_cable_id else '',
            ])

        writer.writerow([])

        # Section liens
        writer.writerow(['=== LIENS ==='])
        writer.writerow(['ID', 'Source', 'Destination', 'Label', 'Style', 'Câble lié'])
        for link in schematic.links.select_related('source_element', 'target_element'):
            writer.writerow([
                str(link.id)[:8],
                link.source_element.label,
                link.target_element.label,
                link.label,
                link.get_line_style_display(),
                str(link.linked_cable_id)[:8] if link.linked_cable_id else '',
            ])

        return output.getvalue()