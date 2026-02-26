"""
Vues de l'application Devices.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.permissions import IsEngineerOrReadOnly, IsEngineerOrAbove
from core.mixins import AuditMixin
from core.exceptions import ConflictError, BusinessLogicError

from .models import Device, DevicePort, DeviceVulnerability, DeviceScan
from .serializers import (
    DeviceListSerializer, DeviceDetailSerializer,
    DevicePortSerializer, DeviceVulnerabilitySerializer,
    DeviceScanSerializer,
)
from .services.device_service import DeviceService
from .services.scan_service import ScanService


# ============================================================
# VIEWSET : ÉQUIPEMENTS
# ============================================================

class DeviceViewSet(AuditMixin, viewsets.ModelViewSet):
    """
    CRUD + supervision pour les équipements.

    CRUD :
    GET    /                        → liste
    POST   /                        → enregistrer un équipement
    GET    /{id}/                   → détail complet
    PUT    /{id}/                   → modifier
    DELETE /{id}/                   → supprimer (soft delete)

    Supervision :
    POST   /{id}/scan/              → lancer un scan (ping/port/vuln/full)
    POST   /{id}/status/            → mettre à jour le statut
    GET    /{id}/ports/             → ports réseau
    GET    /{id}/vulnerabilities/   → vulnérabilités CVE
    POST   /{id}/vulnerabilities/{vuln_id}/patch/ → marquer CVE comme corrigée
    GET    /{id}/scans/             → historique des scans
    """
    permission_classes = [IsAuthenticated, IsEngineerOrReadOnly]

    def get_queryset(self):
        qs = Device.objects.filter(
            is_deleted=False
        ).select_related('owner').prefetch_related(
            'ports', 'vulnerabilities', 'scans'
        )

        # Filtres
        device_type = self.request.query_params.get('type')
        dstatus     = self.request.query_params.get('status')
        vlan        = self.request.query_params.get('vlan')
        criticality = self.request.query_params.get('criticality')

        if device_type:
            qs = qs.filter(device_type=device_type)
        if dstatus:
            qs = qs.filter(status=dstatus)
        if vlan:
            qs = qs.filter(vlan=vlan)
        if criticality:
            qs = qs.filter(criticality=criticality)

        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return DeviceListSerializer
        return DeviceDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            device = DeviceService.register_device(
                validated_data=serializer.validated_data,
                user=request.user,
            )
            return Response(
                DeviceDetailSerializer(device).data,
                status=status.HTTP_201_CREATED
            )
        except ConflictError as e:
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)

    # --------------------------------------------------------
    # ACTION : LANCER UN SCAN
    # --------------------------------------------------------

    @action(detail=True, methods=['post'], url_path='scan')
    def scan(self, request, pk=None):
        """
        POST /{id}/scan/

        Corps :
        {
            "scan_type": "full"   ← "ping" | "port_scan" | "vuln_scan" | "full"
        }
        """
        device    = self.get_object()
        scan_type = request.data.get('scan_type', DeviceScan.SCAN_FULL)
        service   = ScanService()

        scan_map = {
            DeviceScan.SCAN_PING : service.run_ping_scan,
            DeviceScan.SCAN_PORT : service.run_port_scan,
            DeviceScan.SCAN_VULN : service.run_vulnerability_scan,
            DeviceScan.SCAN_FULL : service.run_full_scan,
        }

        run_scan = scan_map.get(scan_type)
        if not run_scan:
            return Response(
                {'error': f"Type de scan invalide : '{scan_type}'. "
                          f"Valeurs : ping, port_scan, vuln_scan, full."},
                status=status.HTTP_400_BAD_REQUEST
            )

        scan = run_scan(device, user=request.user)
        return Response(DeviceScanSerializer(scan).data)

    # --------------------------------------------------------
    # ACTION : METTRE À JOUR LE STATUT
    # --------------------------------------------------------

    @action(detail=True, methods=['post'], url_path='status')
    def update_status(self, request, pk=None):
        """
        POST /{id}/status/
        {"status": "maintenance"}
        """
        device     = self.get_object()
        new_status = request.data.get('status')

        valid = [s[0] for s in Device.CRITICALITY_CHOICES]
        from core.constants import DEVICE_STATUS_CHOICES
        valid_statuses = [s[0] for s in DEVICE_STATUS_CHOICES]

        if new_status not in valid_statuses:
            return Response(
                {'error': f"Statut invalide. Valeurs : {valid_statuses}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        device = DeviceService.update_status(device, new_status, user=request.user)
        return Response({'status': device.status, 'message': 'Statut mis à jour.'})

    # --------------------------------------------------------
    # ACTION : PORTS
    # --------------------------------------------------------

    @action(detail=True, methods=['get'], url_path='ports')
    def ports(self, request, pk=None):
        """GET /{id}/ports/ — Liste les ports réseau de l'équipement."""
        device = self.get_object()
        ports  = device.ports.order_by('port_number')
        return Response(DevicePortSerializer(ports, many=True).data)

    # --------------------------------------------------------
    # ACTION : VULNÉRABILITÉS
    # --------------------------------------------------------

    @action(detail=True, methods=['get'], url_path='vulnerabilities')
    def vulnerabilities(self, request, pk=None):
        """GET /{id}/vulnerabilities/ — Liste les CVE de l'équipement."""
        device  = self.get_object()
        qs      = device.vulnerabilities.order_by('-cvss_score')

        # Filtre optionnel par statut
        vuln_status = request.query_params.get('status')
        if vuln_status:
            qs = qs.filter(status=vuln_status)

        return Response(DeviceVulnerabilitySerializer(qs, many=True).data)

    @action(
        detail=True,
        methods=['post'],
        url_path=r'vulnerabilities/(?P<cve_id>[^/.]+)/patch',
        permission_classes=[IsAuthenticated, IsEngineerOrAbove]
    )
    def patch_vulnerability(self, request, pk=None, cve_id=None):
        """
        POST /{id}/vulnerabilities/{cve_id}/patch/
        Marque une CVE comme corrigée (rôle Ingénieur requis).
        """
        device = self.get_object()
        from django.utils import timezone

        try:
            vuln = device.vulnerabilities.get(cve_id=cve_id)
        except DeviceVulnerability.DoesNotExist:
            return Response(
                {'error': f"CVE {cve_id} non trouvée sur cet équipement."},
                status=status.HTTP_404_NOT_FOUND
            )

        vuln.status     = DeviceVulnerability.STATUS_PATCHED
        vuln.patched_at = timezone.now()
        vuln.patched_by = request.user
        vuln.save(update_fields=['status', 'patched_at', 'patched_by'])

        return Response({
            'message'   : f"CVE {cve_id} marquée comme corrigée.",
            'patched_at': str(vuln.patched_at),
            'patched_by': request.user.full_name,
        })

    # --------------------------------------------------------
    # ACTION : HISTORIQUE DES SCANS
    # --------------------------------------------------------

    @action(detail=True, methods=['get'], url_path='scans')
    def scans(self, request, pk=None):
        """GET /{id}/scans/ — Historique des scans de l'équipement."""
        device = self.get_object()
        scans  = device.scans.order_by('-started_at')[:20]
        return Response(DeviceScanSerializer(scans, many=True).data)


# ============================================================
# VUE : CARTOGRAPHIE RÉSEAU
# ============================================================

class NetworkMapView(APIView):
    """
    GET /api/v1/devices/network-map/

    Retourne la cartographie complète du réseau.
    Utilisé par le frontend pour la visualisation topologique.

    Query params :
    - vlan : filtrer par VLAN (ex: ?vlan=10)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        vlan = request.query_params.get('vlan')
        if vlan:
            try:
                vlan = int(vlan)
            except ValueError:
                return Response(
                    {'error': 'Le VLAN doit être un entier.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        data = DeviceService.get_network_map(vlan=vlan)
        return Response(data)


# ============================================================
# VUE : STATISTIQUES GLOBALES
# ============================================================

class DeviceStatsView(APIView):
    """
    GET /api/v1/devices/stats/

    Statistiques globales pour le tableau de bord de supervision.

    Exemple de réponse :
    {
        "total_devices": 47,
        "online_devices": 42,
        "monitored_devices": 45,
        "open_vulnerabilities": 12,
        "critical_vulns": 3,
        "devices_with_unauth_ports": 2
    }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stats = DeviceService.get_global_stats()
        return Response(stats)