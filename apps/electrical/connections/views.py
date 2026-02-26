"""
Vues de l'application Connections.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsEngineerOrReadOnly, IsEngineerOrAbove
from core.mixins import AuditMixin
from core.exceptions import BusinessLogicError, ElectricalComplianceError

from .models import TerminalBlock, Terminal, Connection
from .serializers import (
    TerminalBlockSerializer, TerminalSerializer,
    ConnectionListSerializer, ConnectionDetailSerializer,
    ConnectionCreateSerializer, ConnectionPointSerializer,
)
from .services.connection_service import ConnectionService


# ============================================================
# VIEWSET : BORNIER
# ============================================================

class TerminalBlockViewSet(AuditMixin, viewsets.ModelViewSet):
    """
    CRUD pour les borniers.

    GET    /terminal-blocks/        → liste
    POST   /terminal-blocks/        → créer
    GET    /terminal-blocks/{id}/   → détail avec toutes les bornes
    PUT    /terminal-blocks/{id}/   → modifier
    DELETE /terminal-blocks/{id}/   → supprimer
    """
    queryset           = TerminalBlock.objects.filter(is_active=True, is_deleted=False)
    serializer_class   = TerminalBlockSerializer
    permission_classes = [IsAuthenticated, IsEngineerOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        equipment = self.request.query_params.get('equipment_ref')
        if equipment:
            qs = qs.filter(equipment_ref=equipment)
        return qs.prefetch_related('terminals')


# ============================================================
# VIEWSET : BORNE
# ============================================================

class TerminalViewSet(viewsets.ModelViewSet):
    """
    CRUD pour les bornes individuelles.

    Filtres disponibles :
    GET /terminals/?block=<id>        → bornes d'un bornier
    GET /terminals/?is_occupied=false → bornes libres uniquement
    """
    queryset           = Terminal.objects.filter(is_active=True)
    serializer_class   = TerminalSerializer
    permission_classes = [IsAuthenticated, IsEngineerOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        block_id    = self.request.query_params.get('block')
        is_occupied = self.request.query_params.get('is_occupied')

        if block_id:
            qs = qs.filter(block_id=block_id)
        if is_occupied is not None:
            qs = qs.filter(is_occupied=(is_occupied.lower() == 'true'))

        return qs.select_related('block')


# ============================================================
# VIEWSET : RACCORDEMENT
# ============================================================

class ConnectionViewSet(AuditMixin, viewsets.ModelViewSet):
    """
    CRUD + actions métier pour les raccordements.

    CRUD :
    GET    /                → liste
    POST   /                → créer (avec validation électrique)
    GET    /{id}/           → détail avec points de raccordement
    PUT    /{id}/           → modifier
    DELETE /{id}/           → supprimer (soft delete)

    Actions métier :
    POST   /{id}/complete/  → Marquer comme réalisé
    POST   /{id}/verify/    → Valider la conformité (rôle Ingénieur)
    POST   /{id}/fault/     → Signaler un défaut
    GET    /{id}/diagram/   → Données du schéma de raccordement
    POST   /{id}/points/    → Ajouter un point de raccordement
    """
    permission_classes = [IsAuthenticated, IsEngineerOrReadOnly]

    def get_queryset(self):
        return Connection.objects.filter(
            is_deleted=False
        ).select_related(
            'cable', 'terminal_origin', 'terminal_dest', 'verified_by'
        ).prefetch_related('connection_points__terminal')

    def get_serializer_class(self):
        if self.action == 'list':
            return ConnectionListSerializer
        if self.action == 'create':
            return ConnectionCreateSerializer
        return ConnectionDetailSerializer

    def perform_create(self, serializer):
        """Passe par le service pour la création avec validation."""
        service = ConnectionService()
        connection = service.create_connection(
            validated_data=serializer.validated_data,
            user=self.request.user,
        )
        # Ne pas appeler serializer.save() : le service a déjà créé l'objet
        return connection

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            connection = self.perform_create(serializer)
            out_serializer = ConnectionDetailSerializer(connection)
            return Response(out_serializer.data, status=status.HTTP_201_CREATED)
        except (BusinessLogicError, ElectricalComplianceError) as e:
            return Response({'error': str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    # --------------------------------------------------------
    # ACTION : AJOUTER UN POINT DE RACCORDEMENT
    # --------------------------------------------------------

    @action(detail=True, methods=['post'], url_path='points')
    def add_point(self, request, pk=None):
        """
        POST /{id}/points/

        Corps :
        {
            "conductor": "L1",
            "terminal": "<terminal_id>",
            "wire_color": "brown",
            "tightening_torque_nm": 2.5,
            "has_ferrule": true
        }
        """
        connection = self.get_object()
        serializer = ConnectionPointSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data    = serializer.validated_data
        service = ConnectionService()

        try:
            point = service.add_connection_point(
                connection           = connection,
                conductor            = data['conductor'],
                terminal             = data['terminal'],
                wire_color           = data['wire_color'],
                tightening_torque_nm = data.get('tightening_torque_nm'),
                has_ferrule          = data.get('has_ferrule', True),
            )
            return Response(
                ConnectionPointSerializer(point).data,
                status=status.HTTP_201_CREATED
            )
        except (BusinessLogicError, ElectricalComplianceError) as e:
            return Response({'error': str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    # --------------------------------------------------------
    # ACTION : MARQUER COMME RÉALISÉ
    # --------------------------------------------------------

    @action(detail=True, methods=['post'], url_path='complete')
    def complete(self, request, pk=None):
        """POST /{id}/complete/ — Marque le raccordement comme réalisé."""
        connection = self.get_object()
        service    = ConnectionService()

        try:
            connection = service.mark_completed(connection, user=request.user)
            return Response({
                'message'   : 'Raccordement marqué comme réalisé.',
                'status'    : connection.status,
                'completed_at': str(connection.completed_at),
            })
        except BusinessLogicError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # --------------------------------------------------------
    # ACTION : VÉRIFIER ET VALIDER (Ingénieur requis)
    # --------------------------------------------------------

    @action(
        detail=True,
        methods=['post'],
        url_path='verify',
        permission_classes=[IsAuthenticated, IsEngineerOrAbove]
    )
    def verify(self, request, pk=None):
        """
        POST /{id}/verify/ — Valide la conformité électrique (Ingénieur requis).
        """
        connection = self.get_object()
        service    = ConnectionService()

        try:
            connection = service.verify_connection(connection, user=request.user)
            return Response({
                'message'    : 'Raccordement vérifié et conforme.',
                'status'     : connection.status,
                'verified_at': str(connection.verified_at),
                'verified_by': connection.verified_by.full_name,
            })
        except ElectricalComplianceError as e:
            return Response({
                'error'  : str(e),
                'status' : Connection.STATUS_FAULTY,
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except BusinessLogicError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # --------------------------------------------------------
    # ACTION : SIGNALER UN DÉFAUT
    # --------------------------------------------------------

    @action(detail=True, methods=['post'], url_path='fault')
    def report_fault(self, request, pk=None):
        """POST /{id}/fault/ — Signale un défaut sur le raccordement."""
        connection  = self.get_object()
        description = request.data.get('description', '')

        if not description:
            return Response(
                {'error': 'La description du défaut est requise.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service    = ConnectionService()
        connection = service.mark_faulty(connection, description, user=request.user)

        return Response({
            'message'    : 'Défaut signalé.',
            'status'     : connection.status,
            'description': connection.fault_description,
        })

    # --------------------------------------------------------
    # ACTION : DONNÉES DU SCHÉMA
    # --------------------------------------------------------

    @action(detail=True, methods=['get'], url_path='diagram')
    def diagram(self, request, pk=None):
        """GET /{id}/diagram/ — Retourne les données pour le schéma de câblage."""
        connection = self.get_object()
        service    = ConnectionService()
        data       = service.get_connection_diagram_data(connection)
        return Response(data)