"""
Tests des services Devices — Scans et alertes de sécurité.
"""

from django.test import TestCase
from unittest.mock import MagicMock, patch

from apps.devices.services.scan_service import ScanService
from apps.devices.models import DeviceVulnerability


class CvssScoreTest(TestCase):
    """Tests de classification des scores CVSS."""

    def test_score_10_is_critical(self):
        self.assertEqual(
            DeviceVulnerability.severity_from_score(10.0),
            DeviceVulnerability.SEVERITY_CRITICAL
        )

    def test_score_9_is_critical(self):
        self.assertEqual(
            DeviceVulnerability.severity_from_score(9.0),
            DeviceVulnerability.SEVERITY_CRITICAL
        )

    def test_score_8_is_high(self):
        self.assertEqual(
            DeviceVulnerability.severity_from_score(8.5),
            DeviceVulnerability.SEVERITY_HIGH
        )

    def test_score_7_is_high(self):
        self.assertEqual(
            DeviceVulnerability.severity_from_score(7.0),
            DeviceVulnerability.SEVERITY_HIGH
        )

    def test_score_5_is_medium(self):
        self.assertEqual(
            DeviceVulnerability.severity_from_score(5.0),
            DeviceVulnerability.SEVERITY_MEDIUM
        )

    def test_score_2_is_low(self):
        self.assertEqual(
            DeviceVulnerability.severity_from_score(2.0),
            DeviceVulnerability.SEVERITY_LOW
        )

    def test_score_0_is_low(self):
        self.assertEqual(
            DeviceVulnerability.severity_from_score(0.0),
            DeviceVulnerability.SEVERITY_LOW
        )

    def test_threshold_exact_9_critical(self):
        """Score exactement 9.0 → CRITICAL (limite incluse)."""
        self.assertEqual(
            DeviceVulnerability.severity_from_score(9.0),
            DeviceVulnerability.SEVERITY_CRITICAL
        )

    def test_threshold_just_below_9_high(self):
        """Score 8.99 → HIGH (juste en dessous du seuil critique)."""
        self.assertEqual(
            DeviceVulnerability.severity_from_score(8.99),
            DeviceVulnerability.SEVERITY_HIGH
        )


class ScanServiceTest(TestCase):
    """Tests du service de scan."""

    def setUp(self):
        self.service = ScanService()

    def test_cve_lookup_windows_server(self):
        """Trouve des CVE pour Windows Server 2019."""
        device    = MagicMock()
        device.os = 'Windows Server 2019'
        cves      = self.service._lookup_cves(device)
        self.assertGreater(len(cves), 0)
        self.assertTrue(all('cve_id' in c for c in cves))

    def test_cve_lookup_no_os(self):
        """Retourne vide si pas d'OS renseigné."""
        device    = MagicMock()
        device.os = ''
        cves      = self.service._lookup_cves(device)
        self.assertEqual(cves, [])

    def test_cve_lookup_unknown_os(self):
        """Retourne vide pour un OS inconnu."""
        device    = MagicMock()
        device.os = 'Inconnu OS X99'
        cves      = self.service._lookup_cves(device)
        self.assertEqual(cves, [])

    def test_discover_ports_server_type(self):
        """Un serveur a les ports serveur par défaut."""
        device             = MagicMock()
        device.device_type = 'server'
        ports              = self.service._discover_ports(device)
        port_numbers       = [p for p, _ in ports]
        self.assertIn(22,  port_numbers)   # SSH
        self.assertIn(443, port_numbers)   # HTTPS

    def test_discover_ports_plc_type(self):
        """Un automate (PLC) a les ports industriels."""
        device             = MagicMock()
        device.device_type = 'plc'
        ports              = self.service._discover_ports(device)
        port_numbers       = [p for p, _ in ports]
        self.assertIn(502,  port_numbers)  # Modbus
        self.assertIn(4840, port_numbers)  # OPC-UA

    def test_authorized_ports_server(self):
        """Les ports serveur par défaut sont dans la liste autorisée."""
        authorized = self.service.DEFAULT_AUTHORIZED_PORTS.get('server', [])
        self.assertIn(22,  authorized)
        self.assertIn(443, authorized)

    def test_telnet_port_23_not_in_server_defaults(self):
        """Telnet (port 23) ne doit pas être dans les ports serveur autorisés."""
        authorized = self.service.DEFAULT_AUTHORIZED_PORTS.get('server', [])
        self.assertNotIn(23, authorized)


class AlertServiceTest(TestCase):
    """Tests du service d'alertes."""

    def test_check_offline_devices_returns_list(self):
        """check_offline_devices retourne une liste (vide si aucun device)."""
        from apps.devices.services.alert_service import AlertService
        result = AlertService.check_offline_devices(timeout_minutes=10)
        self.assertIsInstance(result, list)

    def test_check_unscanned_devices_returns_list(self):
        """check_unscanned_devices retourne une liste."""
        from apps.devices.services.alert_service import AlertService
        result = AlertService.check_unscanned_devices(days=7)
        self.assertIsInstance(result, list)