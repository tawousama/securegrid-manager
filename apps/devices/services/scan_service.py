"""
Service de scans de sécurité.

En environnement de production, les scans réels utiliseraient :
- ping  : subprocess avec 'ping -c 1 -W 2 <ip>'
- ports : nmap via python-nmap (pip install python-nmap)
- CVE   : API NVD (National Vulnerability Database) NIST

Ici on implémente la logique complète avec des données simulées
pour que le code soit fonctionnel sans dépendances externes.
La structure est conçue pour être remplacée facilement par de vrais appels.
"""

import socket
import random
from datetime import timedelta
from django.utils import timezone

from ..models import Device, DevicePort, DeviceVulnerability, DeviceScan


class ScanService:
    """
    Effectue des scans de sécurité sur les équipements.

    Usage :
        service = ScanService()
        scan    = service.run_full_scan(device, user=request.user)
    """

    # Ports courants dans les installations industrielles
    INDUSTRIAL_PORTS = {
        20 : ('ftp-data', 'tcp'),
        21 : ('ftp',      'tcp'),
        22 : ('ssh',      'tcp'),
        23 : ('telnet',   'tcp'),    # Non sécurisé ! → alerte si ouvert
        25 : ('smtp',     'tcp'),
        80 : ('http',     'tcp'),
        102: ('s7comm',   'tcp'),    # Siemens S7 (IEC 61850)
        161: ('snmp',     'udp'),
        443: ('https',    'tcp'),
        502: ('modbus',   'tcp'),    # Protocole industriel Modbus
        4840:('opc-ua',   'tcp'),    # OPC-UA (standard industrie 4.0)
        20000:('dnp3',    'tcp'),    # DNP3 (SCADA)
        47808:('bacnet',  'udp'),    # BACnet (bâtiment)
    }

    # Ports autorisés par défaut selon le type d'équipement
    DEFAULT_AUTHORIZED_PORTS = {
        'server'     : [22, 80, 443, 8080, 8443],
        'switch'     : [22, 23, 80, 161, 443],
        'iot'        : [80, 443, 8883],
        'plc'        : [102, 502, 4840, 20000],
        'printer'    : [80, 443, 515, 631, 9100],
        'controller' : [102, 502, 4840],
        'sensor'     : [80, 443, 502],
    }

    # Base CVE simulée par OS/firmware
    KNOWN_CVES = {
        'windows server 2019': [
            {
                'cve_id'    : 'CVE-2021-34527',
                'score'     : 8.8,
                'title'     : 'PrintNightmare — Windows Print Spooler RCE',
                'component' : 'Windows Print Spooler',
                'fix'       : 'Appliquer KB5004945 ou désactiver le service Spooler'
            },
        ],
        'windows server 2022': [
            {
                'cve_id'    : 'CVE-2022-30190',
                'score'     : 7.8,
                'title'     : 'Microsoft Support Diagnostic Tool (MSDT) — Follina',
                'component' : 'MSDT',
                'fix'       : 'Appliquer KB5014699'
            },
        ],
        'ubuntu 20.04': [
            {
                'cve_id'    : 'CVE-2022-0847',
                'score'     : 7.8,
                'title'     : 'Dirty Pipe — Linux Kernel Privilege Escalation',
                'component' : 'Linux Kernel < 5.16.11',
                'fix'       : 'Mettre à jour le noyau Linux >= 5.16.11'
            },
        ],
        'cisco ios': [
            {
                'cve_id'    : 'CVE-2023-20198',
                'score'     : 10.0,
                'title'     : 'Cisco IOS XE Web UI — Privilege Escalation Critique',
                'component' : 'Cisco IOS XE Web UI',
                'fix'       : 'Désactiver l\'interface web ou appliquer le patch Cisco'
            },
        ],
    }

    # --------------------------------------------------------
    # SCANS PRINCIPAUX
    # --------------------------------------------------------

    def run_ping_scan(self, device: Device, user=None) -> DeviceScan:
        """
        Vérifie si l'équipement répond (ping / connexion TCP).
        Met à jour le statut ONLINE/OFFLINE du device.
        """
        scan = DeviceScan.objects.create(
            device      = device,
            scan_type   = DeviceScan.SCAN_PING,
            launched_by = user,
        )

        try:
            is_reachable = self._check_reachable(device.ip_address)

            if is_reachable:
                device.mark_online()
                result_data = {'reachable': True, 'latency_ms': random.uniform(0.5, 5.0)}
            else:
                device.mark_offline()
                result_data = {'reachable': False}

            scan.result    = DeviceScan.RESULT_SUCCESS
            scan.scan_data = result_data

        except Exception as e:
            scan.result        = DeviceScan.RESULT_FAILED
            scan.error_message = str(e)

        finally:
            scan.completed_at = timezone.now()
            device.last_scan  = timezone.now()
            device.save(update_fields=['last_scan'])
            scan.save()

        return scan

    def run_port_scan(self, device: Device, user=None) -> DeviceScan:
        """
        Scanne les ports ouverts de l'équipement.
        Compare avec la liste des ports autorisés.
        Crée des alertes pour les ports non autorisés.
        """
        scan = DeviceScan.objects.create(
            device      = device,
            scan_type   = DeviceScan.SCAN_PORT,
            launched_by = user,
        )

        try:
            open_ports = self._discover_ports(device)

            authorized_ports = self.DEFAULT_AUTHORIZED_PORTS.get(
                device.device_type, [22, 80, 443]
            )

            ports_created    = 0
            unauthorized     = 0

            for port_num, protocol in open_ports:
                service, _ = self.INDUSTRIAL_PORTS.get(port_num, ('unknown', 'tcp'))
                is_auth    = port_num in authorized_ports

                DevicePort.objects.update_or_create(
                    device      = device,
                    port_number = port_num,
                    protocol    = protocol,
                    defaults    = {
                        'state'        : DevicePort.STATE_OPEN,
                        'service'      : service,
                        'is_authorized': is_auth,
                        'last_seen'    : timezone.now(),
                    }
                )
                ports_created += 1
                if not is_auth:
                    unauthorized += 1

            # Alerter sur les ports non autorisés
            if unauthorized > 0:
                from .alert_service import AlertService
                AlertService.create_unauthorized_port_alert(device, unauthorized)

            scan.ports_found              = ports_created
            scan.open_ports_found         = ports_created
            scan.unauthorized_ports_found = unauthorized
            scan.result    = DeviceScan.RESULT_SUCCESS
            scan.scan_data = {'open_ports': [p for p, _ in open_ports]}

        except Exception as e:
            scan.result        = DeviceScan.RESULT_FAILED
            scan.error_message = str(e)

        finally:
            scan.completed_at = timezone.now()
            scan.save()

        return scan

    def run_vulnerability_scan(self, device: Device, user=None) -> DeviceScan:
        """
        Analyse les vulnérabilités CVE connues pour l'OS/firmware.
        Compare avec la base CVE simulée (en prod : API NVD NIST).
        """
        scan = DeviceScan.objects.create(
            device      = device,
            scan_type   = DeviceScan.SCAN_VULN,
            launched_by = user,
        )

        try:
            cves_found = self._lookup_cves(device)
            vuln_count = 0
            crit_count = 0

            for cve_data in cves_found:
                severity = DeviceVulnerability.severity_from_score(cve_data['score'])

                DeviceVulnerability.objects.get_or_create(
                    device = device,
                    cve_id = cve_data['cve_id'],
                    defaults={
                        'cvss_score'         : cve_data['score'],
                        'severity'           : severity,
                        'title'              : cve_data['title'],
                        'affected_component' : cve_data['component'],
                        'remediation'        : cve_data['fix'],
                        'status'             : DeviceVulnerability.STATUS_OPEN,
                    }
                )
                vuln_count += 1
                if severity == DeviceVulnerability.SEVERITY_CRITICAL:
                    crit_count += 1

            # Alerter si CVE critiques trouvées
            if crit_count > 0:
                from .alert_service import AlertService
                AlertService.create_critical_vuln_alert(device, crit_count)

            scan.vulnerabilities_found = vuln_count
            scan.critical_vulns_found  = crit_count
            scan.result    = DeviceScan.RESULT_SUCCESS
            scan.scan_data = {'cves_found': [c['cve_id'] for c in cves_found]}

        except Exception as e:
            scan.result        = DeviceScan.RESULT_FAILED
            scan.error_message = str(e)

        finally:
            scan.completed_at = timezone.now()
            scan.save()

        return scan

    def run_full_scan(self, device: Device, user=None) -> DeviceScan:
        """
        Scan complet : ping + ports + vulnérabilités.
        Lance les trois scans séquentiellement.
        Retourne un scan synthétique avec tous les résultats.
        """
        full_scan = DeviceScan.objects.create(
            device      = device,
            scan_type   = DeviceScan.SCAN_FULL,
            launched_by = user,
        )

        ping_scan = self.run_ping_scan(device)
        port_scan = self.run_port_scan(device)
        vuln_scan = self.run_vulnerability_scan(device)

        all_success = all(
            s.result == DeviceScan.RESULT_SUCCESS
            for s in [ping_scan, port_scan, vuln_scan]
        )

        full_scan.result                   = (
            DeviceScan.RESULT_SUCCESS if all_success
            else DeviceScan.RESULT_PARTIAL
        )
        full_scan.ports_found              = port_scan.ports_found
        full_scan.open_ports_found         = port_scan.open_ports_found
        full_scan.unauthorized_ports_found = port_scan.unauthorized_ports_found
        full_scan.vulnerabilities_found    = vuln_scan.vulnerabilities_found
        full_scan.critical_vulns_found     = vuln_scan.critical_vulns_found
        full_scan.completed_at             = timezone.now()
        full_scan.scan_data                = {
            'ping'  : ping_scan.scan_data,
            'ports' : port_scan.scan_data,
            'vulns' : vuln_scan.scan_data,
        }
        full_scan.save()

        device.last_scan = timezone.now()
        device.save(update_fields=['last_scan'])

        return full_scan

    # --------------------------------------------------------
    # MÉTHODES PRIVÉES (simulées — à remplacer en production)
    # --------------------------------------------------------

    def _check_reachable(self, ip: str) -> bool:
        """
        Vérifie si une IP répond.
        Simulation : tente une connexion TCP sur le port 80 ou 443.
        En production : utiliser subprocess ping ou icmplib.
        """
        for port in [80, 443, 22]:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((ip, port))
                sock.close()
                if result == 0:
                    return True
            except (socket.error, OSError):
                continue
        return False

    def _discover_ports(self, device: Device) -> list:
        """
        Découvre les ports ouverts sur un équipement.
        Simulation : retourne les ports typiques du type d'équipement.
        En production : utiliser nmap via python-nmap.

        Returns:
            list[tuple] : [(port_number, protocol), ...]
        """
        base_ports = self.DEFAULT_AUTHORIZED_PORTS.get(device.device_type, [22, 80])
        # Simuler quelques ports supplémentaires aléatoirement
        extra = [p for p in [23, 8080, 4444] if random.random() < 0.1]
        all_ports = list(set(base_ports + extra))
        return [(p, 'tcp') for p in all_ports]

    def _lookup_cves(self, device: Device) -> list:
        """
        Cherche les CVE connues pour l'OS/firmware du device.
        Simulation : lookup dans notre base statique.
        En production : appel à l'API NVD NIST
            GET https://services.nvd.nist.gov/rest/json/cves/2.0
                ?keywordSearch=<os_name>&cvssV3Severity=HIGH

        Returns:
            list[dict] : Liste de CVE trouvées
        """
        if not device.os:
            return []

        os_lower = device.os.lower()
        for key, cves in self.KNOWN_CVES.items():
            if key in os_lower:
                return cves
        return []