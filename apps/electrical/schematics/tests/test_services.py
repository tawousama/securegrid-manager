"""
Tests des services Schematics.
"""

from django.test import TestCase
from unittest.mock import MagicMock, patch
from apps.electrical.schematics.services.export_service import ExportService
from apps.electrical.schematics.views import SchematicViewSet


class ExportServiceTest(TestCase):

    def _make_schematic(self, n_elements=2, n_links=1):
        """Crée un schéma mock avec des éléments et des liens."""
        schematic              = MagicMock()
        schematic.reference    = 'SCH-TEST-001'
        schematic.title        = 'Schéma de test'
        schematic.version      = 'Rev.1'
        schematic.status       = 'approved'
        schematic.page_width   = 297.0
        schematic.page_height  = 210.0
        schematic.scale        = '1:1'
        schematic.standard     = 'IEC'
        schematic.get_status_display.return_value = 'Approuvé'

        # Éléments mock
        elements = []
        for i in range(n_elements):
            e             = MagicMock()
            e.id          = f'elem-{i}'
            e.element_type = 'terminal_block'
            e.label       = f'ELEM-{i}'
            e.description = ''
            e.x, e.y      = float(i * 50), 20.0
            e.width       = 20.0
            e.height      = 12.0
            e.rotation    = 0.0
            e.properties  = {}
            e.color       = '#000000'
            e.font_size   = 3.0
            e.is_visible  = True
            e.linked_cable_id    = None
            e.linked_terminal_id = None
            e.linked_connection_id = None
            e.get_element_type_display.return_value = 'Bornier'
            elements.append(e)

        schematic.elements.filter.return_value = elements
        schematic.elements.order_by.return_value = elements

        # Liens mock
        links = []
        if n_elements >= 2 and n_links > 0:
            lk                   = MagicMock()
            lk.id                = 'link-0'
            lk.source_element    = elements[0]
            lk.source_element_id = 'elem-0'
            lk.target_element    = elements[1]
            lk.target_element_id = 'elem-1'
            lk.label             = 'CAB-001'
            lk.line_style        = 'solid'
            lk.line_width        = 0.5
            lk.color             = '#000000'
            lk.waypoints         = []
            lk.linked_cable_id   = None
            lk.get_line_style_display.return_value = 'Trait plein'
            links.append(lk)

        schematic.links.all.return_value = links
        schematic.links.select_related.return_value = MagicMock()
        schematic.links.select_related.return_value.all.return_value = links

        return schematic, elements, links

    def test_export_svg_returns_string(self):
        """L'export SVG retourne une chaîne de caractères."""
        schematic, _, _ = self._make_schematic()
        service = ExportService()
        result  = service.export_to_svg(schematic)
        self.assertIsInstance(result, str)

    def test_export_svg_contains_svg_tags(self):
        """L'export SVG contient les balises SVG valides."""
        schematic, _, _ = self._make_schematic()
        service = ExportService()
        result  = service.export_to_svg(schematic)
        self.assertIn('<svg', result)
        self.assertIn('</svg>', result)

    def test_export_svg_contains_reference(self):
        """L'export SVG contient la référence du schéma."""
        schematic, _, _ = self._make_schematic()
        service = ExportService()
        result  = service.export_to_svg(schematic)
        self.assertIn('SCH-TEST-001', result)

    def test_export_json_returns_valid_json(self):
        """L'export JSON retourne du JSON valide."""
        import json
        schematic, _, _ = self._make_schematic()
        service = ExportService()
        result  = service.export_to_json(schematic)
        parsed  = json.loads(result)
        self.assertIn('schematic', parsed)
        self.assertIn('elements', parsed)
        self.assertIn('links',    parsed)

    def test_export_json_contains_elements(self):
        """L'export JSON contient tous les éléments."""
        import json
        schematic, elements, _ = self._make_schematic(n_elements=3)
        service = ExportService()
        result  = json.loads(service.export_to_json(schematic))
        self.assertEqual(len(result['elements']), 3)

    def test_export_csv_contains_headers(self):
        """L'export CSV contient les en-têtes attendus."""
        schematic, _, _ = self._make_schematic()
        service = ExportService()
        result  = service.export_to_csv(schematic)
        self.assertIn('ÉLÉMENTS', result)
        self.assertIn('LIENS',    result)
        self.assertIn('SCH-TEST-001', result)


class VersionIncrementTest(TestCase):

    def test_increment_rev0(self):
        """Rev.0 → Rev.1"""
        result = SchematicViewSet._increment_version('Rev.0')
        self.assertEqual(result, 'Rev.1')

    def test_increment_rev3(self):
        """Rev.3 → Rev.4"""
        result = SchematicViewSet._increment_version('Rev.3')
        self.assertEqual(result, 'Rev.4')

    def test_increment_unknown_format(self):
        """Format inconnu → ajoute .1"""
        result = SchematicViewSet._increment_version('v1')
        self.assertIn('1', result)