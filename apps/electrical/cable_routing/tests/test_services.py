"""
Tests des services Cable Routing — Calculs et algorithmes.

Ces tests vérifient la logique métier indépendamment de l'API.
"""

from django.test import TestCase
from apps.electrical.cable_routing.services.cable_calculator import CableCalculator
from apps.electrical.cable_routing.services.path_optimizer import PathOptimizer


# ============================================================
# TESTS : CABLE CALCULATOR
# ============================================================

class CableCalculatorTest(TestCase):

    def setUp(self):
        self.calc = CableCalculator()

    def test_voltage_drop_formula(self):
        """Vérifie la formule ΔU = 2×ρ×L×I/S pour le cuivre."""
        drop = self.calc.calculate_voltage_drop(
            current_a=16, length_m=50, section_mm2=2.5
        )
        # ΔU = 2 × 0.01786 × 50 × 16 / 2.5 = 11.43V
        self.assertAlmostEqual(drop, 11.43, places=1)

    def test_longer_cable_more_voltage_drop(self):
        """Un câble plus long a une chute de tension plus élevée."""
        drop_short = self.calc.calculate_voltage_drop(16, 10, 2.5)
        drop_long  = self.calc.calculate_voltage_drop(16, 100, 2.5)
        self.assertGreater(drop_long, drop_short)

    def test_bigger_section_less_voltage_drop(self):
        """Une section plus grande réduit la chute de tension."""
        drop_small = self.calc.calculate_voltage_drop(16, 50, 1.5)
        drop_large = self.calc.calculate_voltage_drop(16, 50, 16.0)
        self.assertGreater(drop_small, drop_large)

    def test_current_capacity_known_section(self):
        """Vérifie les valeurs du tableau IEC pour les sections connues."""
        self.assertEqual(self.calc.get_current_capacity(2.5), 18.0)
        self.assertEqual(self.calc.get_current_capacity(6.0),  31.0)
        self.assertEqual(self.calc.get_current_capacity(16.0), 56.0)

    def test_current_capacity_unknown_section(self):
        """Une section inconnue retourne 0."""
        self.assertEqual(self.calc.get_current_capacity(3.0), 0.0)

    def test_compliant_cable(self):
        """Un câble bien dimensionné est conforme IEC."""
        result = self.calc.check_cable_sizing(
            current_a=10,
            length_m=20,
            section_mm2=2.5,
            voltage_v=230,
        )
        self.assertTrue(result['is_compliant'])
        self.assertTrue(result['is_voltage_drop_ok'])
        self.assertTrue(result['is_current_capacity_ok'])
        self.assertEqual(result['recommendations'], [])

    def test_overcurrent_not_compliant(self):
        """Un câble trop petit pour le courant est non conforme."""
        result = self.calc.check_cable_sizing(
            current_a=100,     # 100A sur une section 1.5mm² → trop petit
            length_m=10,
            section_mm2=1.5,
            voltage_v=230,
        )
        self.assertFalse(result['is_current_capacity_ok'])
        self.assertFalse(result['is_compliant'])
        self.assertTrue(len(result['recommendations']) > 0)

    def test_excessive_voltage_drop_not_compliant(self):
        """Chute de tension > 3% est non conforme IEC."""
        result = self.calc.check_cable_sizing(
            current_a=32,
            length_m=500,    # Très long → grande chute de tension
            section_mm2=1.5,
            voltage_v=230,
        )
        self.assertFalse(result['is_voltage_drop_ok'])
        self.assertFalse(result['is_compliant'])

    def test_recommendation_provided_when_not_compliant(self):
        """Des recommandations sont fournies si non conforme."""
        result = self.calc.check_cable_sizing(
            current_a=100,
            length_m=10,
            section_mm2=1.5,
            voltage_v=230,
        )
        self.assertTrue(len(result['recommendations']) > 0)

    def test_resistance_calculation(self):
        """Vérifie le calcul de résistance aller-retour."""
        r = self.calc.calculate_resistance(length_m=100, section_mm2=10.0)
        # R = 2 × 0.01786 × 100 / 10 = 0.3572 Ω
        self.assertAlmostEqual(r, 0.3572, places=3)


# ============================================================
# TESTS : PATH OPTIMIZER
# ============================================================

class PathOptimizerTest(TestCase):

    def setUp(self):
        self.optimizer = PathOptimizer(tolerance_m=0.1)

    def test_collinear_points_removed(self):
        """Des points en ligne droite sont détectés comme colinéaires."""
        # Trois points sur l'axe X : le point du milieu est redondant
        points = [
            {'x': 0,  'y': 0, 'z': 0},
            {'x': 5,  'y': 0, 'z': 0},   # ← redondant
            {'x': 10, 'y': 0, 'z': 0},
        ]
        kept = self.optimizer._ramer_douglas_peucker(points, tolerance=0.1)
        self.assertEqual(kept, [0, 2])  # Seulement le 1er et le dernier

    def test_corner_point_kept(self):
        """Un point formant un virage est conservé."""
        points = [
            {'x': 0,  'y': 0,  'z': 0},
            {'x': 10, 'y': 0,  'z': 0},   # ← virage → doit être conservé
            {'x': 10, 'y': 10, 'z': 0},
        ]
        kept = self.optimizer._ramer_douglas_peucker(points, tolerance=0.1)
        self.assertIn(1, kept)  # Le point du virage doit être conservé

    def test_two_points_unchanged(self):
        """Un tracé avec seulement 2 points n'est pas modifié."""
        points = [
            {'x': 0,  'y': 0, 'z': 0},
            {'x': 10, 'y': 0, 'z': 0},
        ]
        kept = self.optimizer._ramer_douglas_peucker(points, tolerance=0.1)
        self.assertEqual(kept, [0, 1])