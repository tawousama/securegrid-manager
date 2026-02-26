"""
Serializers de l'application Schematics.
"""

from rest_framework import serializers
from .models import Schematic, SchematicElement, SchematicLink, SchematicRevision


class SchematicElementSerializer(serializers.ModelSerializer):
    element_type_label = serializers.CharField(
        source='get_element_type_display', read_only=True
    )

    class Meta:
        model  = SchematicElement
        fields = [
            'id', 'element_type', 'element_type_label',
            'label', 'description',
            'x', 'y', 'width', 'height', 'rotation',
            'properties',
            'linked_cable_id', 'linked_terminal_id', 'linked_connection_id',
            'color', 'font_size', 'is_visible',
        ]
        read_only_fields = ['id']


class SchematicLinkSerializer(serializers.ModelSerializer):
    source_label = serializers.CharField(
        source='source_element.label', read_only=True
    )
    target_label = serializers.CharField(
        source='target_element.label', read_only=True
    )
    line_style_label = serializers.CharField(
        source='get_line_style_display', read_only=True
    )

    class Meta:
        model  = SchematicLink
        fields = [
            'id', 'source_element', 'source_label',
            'target_element', 'target_label',
            'line_style', 'line_style_label',
            'line_width', 'color', 'label',
            'linked_cable_id', 'waypoints',
        ]
        read_only_fields = ['id']

    def validate(self, attrs):
        if attrs.get('source_element') == attrs.get('target_element'):
            raise serializers.ValidationError(
                "La source et la cible d'un lien doivent être différentes."
            )
        return attrs


class SchematicRevisionSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.full_name', read_only=True)

    class Meta:
        model  = SchematicRevision
        fields = [
            'id', 'version', 'description',
            'author', 'author_name',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class SchematicListSerializer(serializers.ModelSerializer):
    """Version allégée pour les listes — sans éléments ni liens."""
    schematic_type_label = serializers.CharField(
        source='get_schematic_type_display', read_only=True
    )
    status_label  = serializers.CharField(source='get_status_display', read_only=True)
    element_count = serializers.IntegerField(read_only=True)
    link_count    = serializers.IntegerField(read_only=True)
    is_approved   = serializers.BooleanField(read_only=True)

    class Meta:
        model  = Schematic
        fields = [
            'id', 'reference', 'title',
            'schematic_type', 'schematic_type_label',
            'status', 'status_label', 'version',
            'standard', 'project_ref', 'zone',
            'element_count', 'link_count', 'is_approved',
            'approved_at', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class SchematicDetailSerializer(serializers.ModelSerializer):
    """Version complète avec tous les éléments, liens et révisions."""
    schematic_type_label = serializers.CharField(
        source='get_schematic_type_display', read_only=True
    )
    status_label  = serializers.CharField(source='get_status_display', read_only=True)
    elements      = SchematicElementSerializer(many=True, read_only=True)
    links         = SchematicLinkSerializer(many=True, read_only=True)
    revisions     = SchematicRevisionSerializer(many=True, read_only=True)
    approved_by_name = serializers.SerializerMethodField()
    element_count = serializers.IntegerField(read_only=True)
    link_count    = serializers.IntegerField(read_only=True)
    is_approved   = serializers.BooleanField(read_only=True)
    is_editable   = serializers.BooleanField(read_only=True)

    class Meta:
        model  = Schematic
        fields = [
            'id', 'reference', 'title', 'description',
            'schematic_type', 'schematic_type_label',
            'status', 'status_label', 'version',
            'standard', 'project_ref', 'zone',
            'page_width', 'page_height', 'scale',
            'reviewed_at', 'approved_at',
            'approved_by', 'approved_by_name',
            'elements', 'links', 'revisions',
            'element_count', 'link_count',
            'is_approved', 'is_editable',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'reviewed_at', 'approved_at', 'approved_by',
        ]

    def get_approved_by_name(self, obj):
        return obj.approved_by.full_name if obj.approved_by else None