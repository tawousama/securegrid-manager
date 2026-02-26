"""
Vues de l'application Schematics.
"""

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsEngineerOrReadOnly, IsEngineerOrAbove
from core.mixins import AuditMixin
from core.exceptions import BusinessLogicError

from .models import Schematic, SchematicElement, SchematicLink, SchematicRevision
from .serializers import (
    SchematicListSerializer, SchematicDetailSerializer,
    SchematicElementSerializer, SchematicLinkSerializer,
    SchematicRevisionSerializer,
)
from .services.diagram_generator import DiagramGenerator
from .services.export_service import ExportService


class SchematicViewSet(AuditMixin, viewsets.ModelViewSet):
    """
    CRUD + actions métier pour les schémas électriques.

    CRUD :
    GET    /                     → liste (serializer allégé)
    POST   /                     → créer
    GET    /{id}/                → détail complet (éléments + liens)
    PUT    /{id}/                → modifier
    DELETE /{id}/                → supprimer (soft delete)

    Actions métier :
    POST   /{id}/generate/       → Générer automatiquement depuis les câbles
    POST   /{id}/approve/        → Approuver le schéma (Ingénieur requis)
    POST   /{id}/submit-review/  → Soumettre pour révision
    GET    /{id}/export/svg/     → Télécharger le SVG
    GET    /{id}/export/json/    → Télécharger le JSON
    GET    /{id}/export/csv/     → Télécharger le CSV
    GET    /{id}/revisions/      → Historique des révisions
    POST   /{id}/elements/       → Ajouter un élément
    POST   /{id}/links/          → Ajouter un lien
    """
    permission_classes = [IsAuthenticated, IsEngineerOrReadOnly]

    def get_queryset(self):
        qs = Schematic.objects.filter(
            is_deleted=False
        ).prefetch_related('elements', 'links', 'revisions')

        # Filtres optionnels
        project = self.request.query_params.get('project_ref')
        stype   = self.request.query_params.get('type')
        sstatus = self.request.query_params.get('status')

        if project:
            qs = qs.filter(project_ref=project)
        if stype:
            qs = qs.filter(schematic_type=stype)
        if sstatus:
            qs = qs.filter(status=sstatus)

        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return SchematicListSerializer
        return SchematicDetailSerializer

    # --------------------------------------------------------
    # ACTION : GÉNÉRER AUTOMATIQUEMENT
    # --------------------------------------------------------

    @action(detail=True, methods=['post'], url_path='generate')
    def generate(self, request, pk=None):
        """
        POST /{id}/generate/

        Génère automatiquement les éléments et liens du schéma
        à partir des câbles et connexions en base de données.

        Corps optionnel :
        {
            "cable_ids": ["uuid1", "uuid2"],   ← câbles spécifiques
            "project_ref": "EPR2-PENLY"         ← ou tout un projet
        }
        """
        schematic = self.get_object()

        if not schematic.is_editable:
            return Response(
                {'error': 'Un schéma approuvé ne peut pas être régénéré. '
                          'Créez une nouvelle révision.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        generator = DiagramGenerator()
        cable_ids = request.data.get('cable_ids')

        if cable_ids:
            result = generator.generate_from_cables(schematic, cable_ids)
        else:
            project_ref = request.data.get('project_ref', schematic.project_ref)
            result = generator.generate_from_project(schematic, project_ref)

        return Response({
            'message'          : 'Schéma généré avec succès.',
            'elements_created' : result['elements_created'],
            'links_created'    : result['links_created'],
            'schematic'        : SchematicDetailSerializer(schematic).data,
        })

    # --------------------------------------------------------
    # ACTION : SOUMETTRE POUR RÉVISION
    # --------------------------------------------------------

    @action(detail=True, methods=['post'], url_path='submit-review')
    def submit_review(self, request, pk=None):
        """POST /{id}/submit-review/ — Soumet le schéma pour révision."""
        schematic = self.get_object()

        if schematic.status != Schematic.STATUS_DRAFT:
            return Response(
                {'error': 'Seul un brouillon peut être soumis pour révision.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        description = request.data.get('description', 'Soumis pour révision.')

        schematic.status      = Schematic.STATUS_REVIEW
        schematic.reviewed_at = timezone.now()
        schematic.updated_by  = request.user
        schematic.save(update_fields=['status', 'reviewed_at', 'updated_by'])

        # Créer une révision
        self._create_revision(schematic, description, request.user)

        return Response({
            'message' : 'Schéma soumis pour révision.',
            'status'  : schematic.status,
        })

    # --------------------------------------------------------
    # ACTION : APPROUVER
    # --------------------------------------------------------

    @action(
        detail=True,
        methods=['post'],
        url_path='approve',
        permission_classes=[IsAuthenticated, IsEngineerOrAbove]
    )
    def approve(self, request, pk=None):
        """
        POST /{id}/approve/ — Approuve le schéma (Ingénieur requis).
        """
        schematic = self.get_object()

        if schematic.status not in [Schematic.STATUS_DRAFT, Schematic.STATUS_REVIEW]:
            return Response(
                {'error': 'Seul un schéma en brouillon ou en révision peut être approuvé.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if schematic.elements.count() == 0:
            return Response(
                {'error': 'Impossible d\'approuver un schéma vide.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        description = request.data.get('description', 'Approuvé pour exécution.')

        # Incrémenter la version
        new_version = self._increment_version(schematic.version)

        schematic.status      = Schematic.STATUS_APPROVED
        schematic.approved_at = timezone.now()
        schematic.approved_by = request.user
        schematic.version     = new_version
        schematic.updated_by  = request.user
        schematic.save(update_fields=[
            'status', 'approved_at', 'approved_by', 'version', 'updated_by'
        ])

        self._create_revision(schematic, description, request.user)

        return Response({
            'message'    : 'Schéma approuvé.',
            'version'    : schematic.version,
            'approved_at': str(schematic.approved_at),
            'approved_by': request.user.full_name,
        })

    # --------------------------------------------------------
    # ACTIONS : EXPORT
    # --------------------------------------------------------

    @action(detail=True, methods=['get'], url_path='export/svg')
    def export_svg(self, request, pk=None):
        """GET /{id}/export/svg/ — Télécharge le SVG du schéma."""
        schematic    = self.get_object()
        export_svc   = ExportService()
        svg_content  = export_svc.export_to_svg(schematic)

        response = HttpResponse(svg_content, content_type='image/svg+xml')
        response['Content-Disposition'] = (
            f'attachment; filename="{schematic.reference}_{schematic.version}.svg"'
        )
        return response

    @action(detail=True, methods=['get'], url_path='export/json')
    def export_json(self, request, pk=None):
        """GET /{id}/export/json/ — Télécharge le JSON du schéma."""
        schematic    = self.get_object()
        export_svc   = ExportService()
        json_content = export_svc.export_to_json(schematic)

        response = HttpResponse(json_content, content_type='application/json')
        response['Content-Disposition'] = (
            f'attachment; filename="{schematic.reference}_{schematic.version}.json"'
        )
        return response

    @action(detail=True, methods=['get'], url_path='export/csv')
    def export_csv(self, request, pk=None):
        """GET /{id}/export/csv/ — Télécharge le CSV du schéma."""
        schematic   = self.get_object()
        export_svc  = ExportService()
        csv_content = export_svc.export_to_csv(schematic)

        response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = (
            f'attachment; filename="{schematic.reference}_{schematic.version}.csv"'
        )
        return response

    # --------------------------------------------------------
    # ACTIONS : ÉLÉMENTS ET LIENS
    # --------------------------------------------------------

    @action(detail=True, methods=['post', 'get'], url_path='elements')
    def elements(self, request, pk=None):
        """
        GET  /{id}/elements/ → Liste les éléments
        POST /{id}/elements/ → Ajoute un élément
        """
        schematic = self.get_object()

        if request.method == 'GET':
            return Response(
                SchematicElementSerializer(
                    schematic.elements.all(), many=True
                ).data
            )

        if not schematic.is_editable:
            return Response(
                {'error': 'Ce schéma est approuvé et ne peut plus être modifié.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = SchematicElementSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        element = serializer.save(schematic=schematic)
        return Response(
            SchematicElementSerializer(element).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post', 'get'], url_path='links')
    def links(self, request, pk=None):
        """
        GET  /{id}/links/ → Liste les liens
        POST /{id}/links/ → Ajoute un lien
        """
        schematic = self.get_object()

        if request.method == 'GET':
            return Response(
                SchematicLinkSerializer(
                    schematic.links.select_related(
                        'source_element', 'target_element'
                    ).all(),
                    many=True
                ).data
            )

        if not schematic.is_editable:
            return Response(
                {'error': 'Ce schéma est approuvé et ne peut plus être modifié.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = SchematicLinkSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Vérifier que les éléments appartiennent bien à ce schéma
        src = serializer.validated_data['source_element']
        tgt = serializer.validated_data['target_element']
        if src.schematic_id != schematic.id or tgt.schematic_id != schematic.id:
            return Response(
                {'error': 'Les éléments source et cible doivent appartenir à ce schéma.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        link = serializer.save(schematic=schematic)
        return Response(
            SchematicLinkSerializer(link).data,
            status=status.HTTP_201_CREATED
        )

    # --------------------------------------------------------
    # ACTION : HISTORIQUE DES RÉVISIONS
    # --------------------------------------------------------

    @action(detail=True, methods=['get'], url_path='revisions')
    def revisions(self, request, pk=None):
        """GET /{id}/revisions/ — Retourne l'historique des révisions."""
        schematic = self.get_object()
        revisions = schematic.revisions.order_by('-created_at')
        return Response(SchematicRevisionSerializer(revisions, many=True).data)

    # --------------------------------------------------------
    # HELPERS PRIVÉS
    # --------------------------------------------------------

    def _create_revision(self, schematic, description, user):
        """Crée une entrée dans l'historique des révisions."""
        SchematicRevision.objects.create(
            schematic   = schematic,
            version     = schematic.version,
            description = description,
            author      = user,
            snapshot    = {
                'element_count': schematic.elements.count(),
                'link_count'   : schematic.links.count(),
                'status'       : schematic.status,
            }
        )

    @staticmethod
    def _increment_version(version: str) -> str:
        """
        Incrémente le numéro de révision.
        'Rev.0' → 'Rev.1', 'Rev.3' → 'Rev.4'
        """
        try:
            prefix, num = version.rsplit('.', 1)
            return f"{prefix}.{int(num) + 1}"
        except (ValueError, AttributeError):
            return f"{version}.1"