"""
Tests unitaires pour core/validators.py
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from core.validators import (
    validate_ip_address,
    validate_mac_address,
    validate_port_number,
    validate_cable_section,
    validate_voltage,
    validate_cable_length,
    validate_electrical_reference,
    validate_positive_number,
    validate_percentage,
)


class ValidateIPAddressTest(TestCase):

    def test_valid_ipv4(self):
        """Une IPv4 valide ne lève pas d'exception."""
        validate_ip_address("192.168.1.1")   # Pas d'exception

    def test_valid_ipv6(self):
        """Une IPv6 valide ne lève pas d'exception."""
        validate_ip_address("::1")

    def test_invalid_ip_raises(self):
        """Une IP invalide lève ValidationError."""
        with self.assertRaises(ValidationError):
            validate_ip_address("999.999.999.999")

    def test_text_raises(self):
        """Un texte quelconque lève ValidationError."""
        with self.assertRaises(ValidationError):
            validate_ip_address("pas-une-ip")


class ValidateMacAddressTest(TestCase):

    def test_valid_mac_colon(self):
        """MAC avec deux-points valide."""
        validate_mac_address("00:1A:2B:3C:4D:5E")

    def test_valid_mac_dash(self):
        """MAC avec tirets valide."""
        validate_mac_address("00-1A-2B-3C-4D-5E")

    def test_invalid_mac_raises(self):
        """MAC incomplète lève ValidationError."""
        with self.assertRaises(ValidationError):
            validate_mac_address("00:1A:2B:3C")


class ValidateCableSectionTest(TestCase):

    def test_valid_section(self):
        """Une section standard est valide."""
        validate_cable_section(2.5)
        validate_cable_section(16.0)
        validate_cable_section(95.0)

    def test_invalid_section_raises(self):
        """Une section non standard lève ValidationError."""
        with self.assertRaises(ValidationError):
            validate_cable_section(3.0)

    def test_zero_section_raises(self):
        """Une section nulle lève ValidationError."""
        with self.assertRaises(ValidationError):
            validate_cable_section(0)


class ValidateVoltageTest(TestCase):

    def test_common_voltages_valid(self):
        """Les tensions courantes sont valides."""
        for voltage in [12, 24, 230, 400, 20000]:
            validate_voltage(voltage)

    def test_zero_voltage_raises(self):
        """Tension à 0V lève ValidationError."""
        with self.assertRaises(ValidationError):
            validate_voltage(0)

    def test_negative_voltage_raises(self):
        """Tension négative lève ValidationError."""
        with self.assertRaises(ValidationError):
            validate_voltage(-230)

    def test_excessive_voltage_raises(self):
        """Tension trop élevée lève ValidationError."""
        with self.assertRaises(ValidationError):
            validate_voltage(500_000)


class ValidateElectricalReferenceTest(TestCase):

    def test_valid_references(self):
        """Références au bon format sont valides."""
        validate_electrical_reference("CAB-001")
        validate_electrical_reference("EPR-12345")
        validate_electrical_reference("HPC-0042-A")

    def test_lowercase_raises(self):
        """Référence en minuscules lève ValidationError."""
        with self.assertRaises(ValidationError):
            validate_electrical_reference("cab-001")

    def test_no_dash_raises(self):
        """Référence sans tiret lève ValidationError."""
        with self.assertRaises(ValidationError):
            validate_electrical_reference("CAB001")


class ValidatePercentageTest(TestCase):

    def test_valid_percentages(self):
        """Pourcentages valides."""
        for value in [0, 50, 100, 99.9]:
            validate_percentage(value)

    def test_negative_raises(self):
        with self.assertRaises(ValidationError):
            validate_percentage(-1)

    def test_over_100_raises(self):
        with self.assertRaises(ValidationError):
            validate_percentage(101)