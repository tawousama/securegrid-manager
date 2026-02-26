"""
Tests des services Connections — Validations de sécurité électrique.

Ces tests sont critiques : un raccordement incorrect peut être dangereux.
On teste systématiquement les cas d'erreur.
"""

from django.test import TestCase
from unittest.mock import MagicMock

from apps.electrical.connections.services.validation_service import ConnectionValidationService


def make_terminal(max_section=6.0, voltage_rating=400, is_occupied=False):
    """Crée un terminal mock pour les tests."""
    t = MagicMock()
    t.max_section_mm2  = max_section
    t.voltage_rating   = voltage_rating
    t.is_occupied      = is_occupied
    t.__str__          = lambda self: "X1:1"
    return t


def make_cable(section=2.5, voltage=230):
    """Crée un câble mock pour les tests."""
    c = MagicMock()
    c.cable_type.section_mm2 = section
    c.operating_voltage      = voltage
    return c


def make_connection(cable_section=2.5, cable_voltage=230,
                    origin_section_max=6.0, dest_section_max=6.0,
                    origin_voltage=400, dest_voltage=400):
    """Crée un raccordement mock complet pour les tests."""
    conn = MagicMock()
    conn.cable             = make_cable(cable_section, cable_voltage)
    conn.terminal_origin   = make_terminal(origin_section_max, origin_voltage)
    conn.terminal_dest     = make_terminal(dest_section_max, dest_voltage)
    conn.id                = None
    conn.connection_points = MagicMock()
    conn.connection_points.all.return_value = []
    return conn


class SectionCompatibilityTest(TestCase):
    """Tests de validation de compatibilité de section."""

    def setUp(self):
        self.validator = ConnectionValidationService()

    def test_compatible_section_no_error(self):
        """Câble 2.5mm² sur borne max 6mm² → OK."""
        conn   = make_connection(cable_section=2.5, origin_section_max=6.0)
        errors = self.validator.validate_section_compatibility(conn)
        self.assertEqual(errors, [])

    def test_exact_section_no_error(self):
        """Câble 6mm² sur borne max 6mm² → OK (limite exacte)."""
        conn   = make_connection(cable_section=6.0, origin_section_max=6.0)
        errors = self.validator.validate_section_compatibility(conn)
        self.assertEqual(errors, [])

    def test_oversized_cable_origin_error(self):
        """Câble 10mm² sur borne max 6mm² → ERREUR."""
        conn   = make_connection(cable_section=10.0, origin_section_max=6.0)
        errors = self.validator.validate_section_compatibility(conn)
        self.assertEqual(len(errors), 1)
        self.assertIn("10.0mm²", errors[0])

    def test_oversized_cable_both_terminals_error(self):
        """Câble 16mm² sur deux bornes max 6mm² → 2 ERREURS."""
        conn   = make_connection(
            cable_section=16.0,
            origin_section_max=6.0,
            dest_section_max=6.0
        )
        errors = self.validator.validate_section_compatibility(conn)
        self.assertEqual(len(errors), 2)


class VoltageCompatibilityTest(TestCase):
    """Tests de validation de compatibilité de tension."""

    def setUp(self):
        self.validator = ConnectionValidationService()

    def test_compatible_voltage_no_error(self):
        """Câble 230V sur borne 400V → OK."""
        conn   = make_connection(cable_voltage=230, origin_voltage=400)
        errors = self.validator.validate_voltage_compatibility(conn)
        self.assertEqual(errors, [])

    def test_exact_voltage_no_error(self):
        """Câble 400V sur borne 400V → OK."""
        conn   = make_connection(cable_voltage=400, origin_voltage=400)
        errors = self.validator.validate_voltage_compatibility(conn)
        self.assertEqual(errors, [])

    def test_overvoltage_origin_error(self):
        """Câble 1000V sur borne 400V → ERREUR CRITIQUE."""
        conn   = make_connection(cable_voltage=1000, origin_voltage=400)
        errors = self.validator.validate_voltage_compatibility(conn)
        self.assertEqual(len(errors), 1)
        self.assertIn("RISQUE", errors[0])

    def test_no_voltage_on_cable_skipped(self):
        """Pas de tension sur le câble → validation ignorée."""
        conn                      = make_connection()
        conn.cable.operating_voltage = None
        errors = self.validator.validate_voltage_compatibility(conn)
        self.assertEqual(errors, [])


class ColorConventionTest(TestCase):
    """Tests de convention de couleurs IEC 60446."""

    def test_l1_brown_correct(self):
        """L1 en marron est correct selon IEC 60446."""
        from apps.electrical.connections.models import ConnectionPoint
        point = MagicMock(spec=ConnectionPoint)
        point.conductor  = 'L1'
        point.wire_color = 'brown'
        point.STANDARD_COLORS = ConnectionPoint.STANDARD_COLORS
        point.follows_color_convention = property(
            lambda self: self.STANDARD_COLORS.get(self.conductor) == self.wire_color
        ).fget(point)
        self.assertTrue(point.follows_color_convention)

    def test_n_not_blue_incorrect(self):
        """N en marron est INCORRECT selon IEC 60446 (doit être bleu)."""
        from apps.electrical.connections.models import ConnectionPoint
        point = ConnectionPoint.__new__(ConnectionPoint)
        point.conductor  = 'N'
        point.wire_color = 'brown'  # ← mauvaise couleur
        self.assertFalse(point.follows_color_convention)

    def test_pe_yellow_green_correct(self):
        """PE en vert/jaune est correct."""
        from apps.electrical.connections.models import ConnectionPoint
        point = ConnectionPoint.__new__(ConnectionPoint)
        point.conductor  = 'PE'
        point.wire_color = 'yellow_green'
        self.assertTrue(point.follows_color_convention)