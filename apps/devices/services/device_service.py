"""
Service de gestion des équipements réseau.
"""

from django.db.models import Count, Q
from django.utils import timezone

from core.exceptions import ConflictError, BusinessLogicError
from ..models import Device


class DeviceService:

    # --------------------------------------------------------
    # ENREGISTREMENT
    # --------------------------------------------------------

    @staticmethod
    def register_device(validated_data: dict, user) -> Device:
        """
        Enregistre un nouvel équipement après vérification des conflits.

        Vérifie l'unicité de l'IP et du MAC avant création.
        """
        ip  = validated_data.get('ip_address')
        mac = validated_data.get('mac_address', '')

        if Device.objects.filter(ip_address=ip, is_active=True).exists():
            raise ConflictError(
                f"Un équipement avec l'adresse IP {ip} existe déjà."
            )

        if mac and Device.objects.filter(mac_address=mac, is_active=True).exists():
            raise ConflictError(
                f"Un équipement avec l'adresse MAC {mac} existe déjà."
            )

        return Device.objects.create(**validated_data, created_by=user)

    # --------------------------------------------------------
    # STATUT
    # --------------------------------------------------------

    @staticmethod
    def update_status(device: Device, new_status: str, user=None) -> Device:
        """
        Met à jour le statut d'un équipement.
        Déclenche une alerte si passage vers OFFLINE ou FAULT.
        """
        from core.constants import DEVICE_STATUS_OFFLINE, DEVICE_STATUS_FAULT
        from .alert_service import AlertService

        old_status = device.status
        device.status     = new_status
        device.updated_by = user
        device.save(update_fields=['status', 'updated_by'])

        # Alerter si dégradation du statut
        if new_status in [DEVICE_STATUS_OFFLINE, DEVICE_STATUS_FAULT]:
            if old_status not in [DEVICE_STATUS_OFFLINE, DEVICE_STATUS_FAULT]:
                AlertService.create_status_alert(device, new_status)

        return device

    # --------------------------------------------------------
    # CARTOGRAPHIE RÉSEAU
    # --------------------------------------------------------

    @staticmethod
    def get_network_map(vlan: int = None) -> dict:
        """
        Retourne la cartographie réseau de tous les équipements supervisés.
        Utilisé par le frontend pour afficher la topologie réseau.

        Returns:
            dict : {
                'devices': [...],
                'stats': {
                    'total': int,
                    'online': int,
                    'offline': int,
                    'critical_vulns': int
                }
            }
        """
        from core.constants import DEVICE_STATUS_ONLINE, DEVICE_STATUS_OFFLINE

        qs = Device.objects.filter(
            is_active=True,
            is_deleted=False,
            is_monitored=True,
        ).annotate(
            vuln_count=Count(
                'vulnerabilities',
                filter=Q(vulnerabilities__status='open')
            ),
            unauth_ports=Count(
                'ports',
                filter=Q(ports__is_authorized=False, ports__state='open')
            )
        )

        if vlan is not None:
            qs = qs.filter(vlan=vlan)

        devices = [
            {
                'id'          : str(d.id),
                'reference'   : d.reference,
                'name'        : d.name,
                'ip_address'  : d.ip_address,
                'device_type' : d.device_type,
                'status'      : d.status,
                'criticality' : d.criticality,
                'vlan'        : d.vlan,
                'location'    : d.location,
                'vuln_count'  : d.vuln_count,
                'unauth_ports': d.unauth_ports,
                'last_seen'   : d.last_seen.isoformat() if d.last_seen else None,
            }
            for d in qs
        ]

        total   = qs.count()
        online  = qs.filter(status=DEVICE_STATUS_ONLINE).count()
        offline = qs.filter(status=DEVICE_STATUS_OFFLINE).count()
        crit    = sum(1 for d in qs if d.vuln_count > 0 and d.criticality == 'critical')

        return {
            'devices': devices,
            'stats'  : {
                'total'              : total,
                'online'             : online,
                'offline'            : offline,
                'critical_with_vulns': crit,
            }
        }

    # --------------------------------------------------------
    # STATISTIQUES GLOBALES
    # --------------------------------------------------------

    @staticmethod
    def get_global_stats() -> dict:
        """
        Statistiques globales pour le tableau de bord.
        """
        from core.constants import DEVICE_STATUS_ONLINE
        from ..models import DeviceVulnerability

        devices = Device.objects.filter(is_active=True, is_deleted=False)
        vulns   = DeviceVulnerability.objects.filter(status=DeviceVulnerability.STATUS_OPEN)

        return {
            'total_devices'        : devices.count(),
            'online_devices'       : devices.filter(status=DEVICE_STATUS_ONLINE).count(),
            'monitored_devices'    : devices.filter(is_monitored=True).count(),
            'open_vulnerabilities' : vulns.count(),
            'critical_vulns'       : vulns.filter(
                severity=DeviceVulnerability.SEVERITY_CRITICAL
            ).count(),
            'devices_with_unauth_ports': Device.objects.filter(
                ports__is_authorized=False,
                ports__state='open'
            ).distinct().count(),
        }