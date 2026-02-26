"""
Vues de l'application Cable Routing.

Expose les modèles et services via une API REST.
Utilise des ViewSets DRF pour les CRUD classiques
et des APIViews pour les actions personnalisées.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsEngineerOrReadOnly
from core.mixins import AuditMixin

from .models import Cable, CableType, CablePathway, CableRoute
from .serializers import (
    CableListSerializer, CableDetailSerializer,
    CableTypeSerializer, CablePathwaySerializer,
    CableRouteSerializer, CableRouteRequestSerializer,
)
from .services.routing_engine import RoutingEngine
from .services.path_optimizer import PathOptimizer
from .services.cable_calculator import CableCalculator


# ============================================================
# VIEWSET : TYPE DE CÂBLE
# ============================================================

class CableTypeViewSet(AuditMixin, viewsets.ModelViewSet):
    """
    CRUD complet pour les types de câbles.

    GET    /api/v1/electrical/cables/types/        → liste
    POST   /api/v1/electrical/cables/types/        → créer
    GET    /api/v1/electrical/cables/types/{id}/   → détail
    PUT    /api/v1/electrical/cables/types/{id}/   → modifier
    DELETE /api/v1/electrical/cables/types/{id}/   → supprimer
    """
    queryset           = CableType.objects.filter(is_active=True)
    serializer_class   = CableTypeSerializer
    permission_classes = [IsAuthenticated, IsEngineerOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        # Filtres optionnels via query params
        category = self.request.query_params.get('category')
        section  = self.request.query_params.get('section')
        if category:
            qs = qs.filter(cable_category=category)
        if section:
            qs = qs.filter(section_mm2=section)
        return qs


# ============================================================
# VIEWSET : CHEMIN DE CÂBLES
# ============================================================

class CablePathwayViewSet(AuditMixin, viewsets.ModelViewSet):
    """
    CRUD complet pour les chemins de câbles.

    GET    /api/v1/electrical/cables/pathways/        → liste
    POST   /api/v1/electrical/cables/pathways/        → créer
    GET    /api/v1/electrical/cables/pathways/{id}/   → détail
    PUT    /api/v1/electrical/cables/pathways/{id}/   → modifier
    DELETE /api/v1/electrical/cables/pathways/{id}/   → supprimer
    """
    queryset           = CablePathway.objects.filter(is_active=True)
    serializer_class   = CablePathwaySerializer
    permission_classes = [IsAuthenticated, IsEngineerOrReadOnly]


# ============================================================
# VIEWSET : CÂBLE
# ============================================================

class CableViewSet(AuditMixin, viewsets.ModelViewSet):
    """
    CRUD complet + actions métier pour les câbles.

    CRUD standard :
    GET    /api/v1/electrical/cables/           → liste (serializer allégé)
    POST   /api/v1/electrical/cables/           → créer
    GET    /api/v1/electrical/cables/{id}/      → détail (serializer complet)
    PUT    /api/v1/electrical/cables/{id}/      → modifier
    DELETE /api/v1/electrical/cables/{id}/      → supprimer (soft delete)

    Actions métier :
    POST   /api/v1/electrical/cables/{id}/route/      → Calculer le tracé
    POST   /api/v1/electrical/cables/{id}/optimize/   → Optimiser le tracé
    GET    /api/v1/electrical/cables/{id}/calculate/  → Calculs électriques
    GET    /api/v1/electrical/cables/{id}/routes/     → Historique des tracés
    """
    permission_classes = [IsAuthenticated, IsEngineerOrReadOnly]
    filterset_fields   = ['status', 'cable_type', 'is_active']

    def get_queryset(self):
        return Cable.objects.filter(
            is_deleted=False
        ).select_related('cable_type').prefetch_related('routes')

    def get_serializer_class(self):
        """
        Utilise un serializer différent selon l'action.
        - list    → CableListSerializer (léger, sans tracé)
        - retrieve → CableDetailSerializer (complet, avec tracé)
        """
        if self.action == 'list':
            return CableListSerializer
        return CableDetailSerializer

    # --------------------------------------------------------
    # ACTION : CALCULER LE TRACÉ
    # --------------------------------------------------------

    @action(detail=True, methods=['post'], url_path='route')
    def calculate_route(self, request, pk=None):
        """
        POST /api/v1/electrical/cables/{id}/route/

        Calcule automatiquement le tracé optimal pour ce câble
        en utilisant le BFS routing engine.

        Corps :
        {
            "origin_x": 0, "origin_y": 0, "origin_z": 3,
            "dest_x": 85,  "dest_y": 50,  "dest_z": 0,
            "optimize": true
        }
        """
        cable = self.get_object()

        serializer = CableRouteRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Lancer le routing engine
        engine = RoutingEngine()
        result = engine.calculate_route(
            cable       = cable,
            origin      = {'x': data['origin_x'], 'y': data['origin_y'], 'z': data['origin_z']},
            destination = {'x': data['dest_x'],   'y': data['dest_y'],   'z': data['dest_z']},
        )

        if not result['success']:
            return Response(
                {'error': result['message']},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        # Optimiser si demandé
        if data.get('optimize', True) and result['route']:
            optimizer    = PathOptimizer(tolerance_m=0.1)
            opt_result   = optimizer.optimize(result['route'])
            result['optimization'] = {
                'original_waypoints'  : opt_result['original_waypoints'],
                'optimized_waypoints' : opt_result['optimized_waypoints'],
                'length_saved_m'      : opt_result['length_saved_m'],
            }

        return Response({
            'message'      : result['message'],
            'total_length' : result['total_length'],
            'route'        : CableRouteSerializer(result['route']).data,
            'optimization' : result.get('optimization'),
        }, status=status.HTTP_200_OK)

    # --------------------------------------------------------
    # ACTION : CALCULS ÉLECTRIQUES
    # --------------------------------------------------------

    @action(detail=True, methods=['get'], url_path='calculate')
    def electrical_calculations(self, request, pk=None):
        """
        GET /api/v1/electrical/cables/{id}/calculate/

        Effectue les calculs électriques de conformité IEC pour ce câble.

        Query params optionnels :
        - circuit_type : 'terminal' (défaut, max 3%) ou 'distribution' (max 5%)

        Exemple de réponse :
        {
            "voltage_drop_v": 3.21,
            "voltage_drop_percent": 1.40,
            "max_allowed_percent": 3.0,
            "is_voltage_drop_ok": true,
            "current_capacity_a": 31.0,
            "is_current_capacity_ok": true,
            "resistance_ohm": 0.0893,
            "power_loss_w": 91.3,
            "is_compliant": true,
            "recommendations": []
        }
        """
        cable = self.get_object()

        # Vérifier que les données électriques sont renseignées
        if not cable.design_current_a:
            return Response(
                {'error': 'Le courant de conception (design_current_a) n\'est pas renseigné.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not cable.operating_voltage:
            return Response(
                {'error': 'La tension de service (operating_voltage) n\'est pas renseignée.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not cable.effective_length:
            return Response(
                {'error': 'La longueur du câble n\'est pas renseignée.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        circuit_type = request.query_params.get('circuit_type', 'terminal')
        calculator   = CableCalculator()

        result = calculator.check_cable_sizing(
            current_a    = cable.design_current_a,
            length_m     = cable.effective_length,
            section_mm2  = cable.cable_type.section_mm2,
            voltage_v    = cable.operating_voltage,
            conductor    = cable.cable_type.conductor_material,
            circuit_type = circuit_type,
        )

        return Response({
            'cable'       : cable.reference,
            'section_mm2' : cable.cable_type.section_mm2,
            'length_m'    : cable.effective_length,
            'current_a'   : cable.design_current_a,
            'voltage_v'   : cable.operating_voltage,
            **result
        })

    # --------------------------------------------------------
    # ACTION : HISTORIQUE DES TRACÉS
    # --------------------------------------------------------

    @action(detail=True, methods=['get'], url_path='routes')
    def route_history(self, request, pk=None):
        """
        GET /api/v1/electrical/cables/{id}/routes/

        Retourne l'historique de tous les tracés calculés pour ce câble.
        """
        cable  = self.get_object()
        routes = cable.routes.all().order_by('-created_at')
        return Response(CableRouteSerializer(routes, many=True).data)