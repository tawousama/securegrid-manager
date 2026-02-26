"""
Tests unitaires pour core/utils.py

Philosophie des tests :
- Chaque fonction a au moins un test
- On teste les cas normaux ET les cas limites
- Les tests servent aussi de documentation
"""

from django.test import TestCase
from core.utils import (
    generate_unique_code,
    generate_reference,
    calculate_cable_length,
    calculate_voltage_drop,
    calculate_power,
    format_file_size,
    format_duration,
    truncate_text,
    mask_sensitive_data,
)


class GenerateUniqueCodeTest(TestCase):

    def test_returns_string(self):
        """Le code généré est une chaîne de caractères."""
        code = generate_unique_code()
        self.assertIsInstance(code, str)

    def test_prefix_is_applied(self):
        """Le préfixe est bien ajouté au code."""
        code = generate_unique_code(prefix='CAB-')
        self.assertTrue(code.startswith('CAB-'))

    def test_length_is_correct(self):
        """La partie aléatoire a la bonne longueur."""
        code = generate_unique_code(prefix='CAB-', length=6)
        self.assertEqual(len(code), len('CAB-') + 6)

    def test_two_codes_are_different(self):
        """Deux codes générés ne sont (quasi) jamais identiques."""
        code1 = generate_unique_code()
        code2 = generate_unique_code()
        self.assertNotEqual(code1, code2)


class GenerateReferenceTest(TestCase):

    def test_format_is_correct(self):
        """La référence suit le format CATEGORY-NNNNN."""
        ref = generate_reference('CAB', 42)
        self.assertEqual(ref, 'CAB-00042')

    def test_category_is_uppercase(self):
        """La catégorie est en majuscules."""
        ref = generate_reference('cab', 1)
        self.assertTrue(ref.startswith('CAB-'))

    def test_sequence_is_padded(self):
        """Le numéro est padé sur 5 chiffres."""
        ref = generate_reference('EPR', 1)
        self.assertEqual(ref, 'EPR-00001')


class CalculateCableLengthTest(TestCase):

    def test_simple_horizontal_distance(self):
        """Distance sur l'axe X uniquement."""
        length = calculate_cable_length(
            {'x': 0, 'y': 0, 'z': 0},
            {'x': 10, 'y': 0, 'z': 0}
        )
        self.assertEqual(length, 10.0)

    def test_3d_distance(self):
        """Distance en 3 dimensions."""
        length = calculate_cable_length(
            {'x': 0, 'y': 0, 'z': 0},
            {'x': 3, 'y': 4, 'z': 0}
        )
        self.assertEqual(length, 5.0)  # Triangle 3-4-5

    def test_zero_distance(self):
        """Distance nulle entre deux points identiques."""
        length = calculate_cable_length(
            {'x': 5, 'y': 5, 'z': 5},
            {'x': 5, 'y': 5, 'z': 5}
        )
        self.assertEqual(length, 0.0)


class CalculateVoltageDrop(TestCase):

    def test_returns_float(self):
        """La chute de tension est un nombre flottant."""
        drop = calculate_voltage_drop(16, 50, 2.5)
        self.assertIsInstance(drop, float)

    def test_longer_cable_more_drop(self):
        """Un câble plus long a une plus grande chute de tension."""
        drop_short = calculate_voltage_drop(16, 10, 2.5)
        drop_long  = calculate_voltage_drop(16, 100, 2.5)
        self.assertGreater(drop_long, drop_short)

    def test_bigger_section_less_drop(self):
        """Une section plus grande réduit la chute de tension."""
        drop_small = calculate_voltage_drop(16, 50, 1.5)
        drop_large = calculate_voltage_drop(16, 50, 16.0)
        self.assertGreater(drop_small, drop_large)


class FormatFileSizeTest(TestCase):

    def test_bytes(self):
        self.assertEqual(format_file_size(500), '500.0 B')

    def test_kilobytes(self):
        self.assertEqual(format_file_size(1024), '1.0 KB')

    def test_megabytes(self):
        self.assertEqual(format_file_size(1024 * 1024), '1.0 MB')

    def test_gigabytes(self):
        self.assertEqual(format_file_size(1024 ** 3), '1.0 GB')


class FormatDurationTest(TestCase):

    def test_seconds_only(self):
        self.assertEqual(format_duration(45), '45s')

    def test_minutes_and_seconds(self):
        self.assertEqual(format_duration(90), '1m 30s')

    def test_hours_minutes_seconds(self):
        self.assertEqual(format_duration(3661), '1h 01m 01s')


class TruncateTextTest(TestCase):

    def test_short_text_unchanged(self):
        """Un texte court n'est pas modifié."""
        text = "Bonjour"
        self.assertEqual(truncate_text(text, max_length=50), text)

    def test_long_text_is_truncated(self):
        """Un texte trop long est tronqué."""
        text = "Un texte très très très long"
        result = truncate_text(text, max_length=10)
        self.assertLessEqual(len(result), 10)
        self.assertTrue(result.endswith('...'))


class MaskSensitiveDataTest(TestCase):

    def test_last_chars_visible(self):
        """Les derniers caractères restent visibles."""
        result = mask_sensitive_data("password123", visible_chars=3)
        self.assertTrue(result.endswith("123"))

    def test_rest_is_masked(self):
        """Le reste est masqué avec des étoiles."""
        result = mask_sensitive_data("password123", visible_chars=3)
        masked_part = result[:-3]
        self.assertTrue(all(c == '*' for c in masked_part))