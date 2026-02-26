"""
Serializers de l'application Connections.
"""

from rest_framework import serializers
from .models import TerminalBlock, Terminal, Connection, ConnectionPoint


class TerminalSerializer(serializers.ModelSerializer):
    block_reference      = serializers.CharField(source='block.reference', read_only=True)
    terminal_type_label  = serializers.CharField(source='get_terminal_type_display', read_only=True)

    class Meta:
        model  = Terminal
        fields = [
            'id', 'block', 'block_reference', 'label', 'position',
            'terminal_type', 'terminal_type_label',
            'max_section_mm2', 'voltage_rating', 'current_rating',
            'recommended_torque_nm', 'is_occupied', 'is_active',
        ]
        read_only_fields = ['id', 'is_occupied']


class TerminalBlockSerializer(serializers.ModelSerializer):
    terminals           = TerminalSerializer(many=True, read_only=True)
    terminal_count      = serializers.IntegerField(read_only=True)
    available_terminal_count = serializers.IntegerField(read_only=True)

    class Meta:
        model  = TerminalBlock
        fields = [
            'id', 'reference', 'name', 'description',
            'location', 'equipment_ref',
            'voltage_rating', 'current_rating', 'max_section_mm2',
            'manufacturer', 'manufacturer_ref',
            'terminal_count', 'available_terminal_count',
            'terminals', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class ConnectionPointSerializer(serializers.ModelSerializer):
    conductor_label         = serializers.CharField(source='get_conductor_display', read_only=True)
    wire_color_label        = serializers.CharField(source='get_wire_color_display', read_only=True)
    terminal_label          = serializers.CharField(source='terminal.label', read_only=True)
    follows_color_convention = serializers.BooleanField(read_only=True)

    class Meta:
        model  = ConnectionPoint
        fields = [
            'id', 'terminal', 'terminal_label',
            'conductor', 'conductor_label',
            'wire_color', 'wire_color_label',
            'tightening_torque_nm', 'has_ferrule', 'ferrule_ref',
            'is_verified', 'follows_color_convention',
        ]
        read_only_fields = ['id']


class ConnectionListSerializer(serializers.ModelSerializer):
    """Version allégée pour les listes."""
    cable_reference         = serializers.CharField(source='cable.reference', read_only=True)
    status_label            = serializers.CharField(source='get_status_display', read_only=True)
    connection_type_label   = serializers.CharField(source='get_connection_type_display', read_only=True)
    origin_label            = serializers.CharField(source='terminal_origin.__str__', read_only=True)
    dest_label              = serializers.CharField(source='terminal_dest.__str__', read_only=True)

    class Meta:
        model  = Connection
        fields = [
            'id', 'reference', 'name',
            'cable', 'cable_reference',
            'terminal_origin', 'origin_label',
            'terminal_dest',   'dest_label',
            'connection_type', 'connection_type_label',
            'status', 'status_label',
            'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class ConnectionDetailSerializer(serializers.ModelSerializer):
    """Version complète avec points de raccordement."""
    cable_reference  = serializers.CharField(source='cable.reference', read_only=True)
    status_label     = serializers.CharField(source='get_status_display', read_only=True)
    connection_points = ConnectionPointSerializer(many=True, read_only=True)
    is_complete      = serializers.BooleanField(read_only=True)
    is_verified      = serializers.BooleanField(read_only=True)

    class Meta:
        model  = Connection
        fields = [
            'id', 'reference', 'name', 'description',
            'cable', 'cable_reference',
            'terminal_origin', 'terminal_dest',
            'connection_type', 'status', 'status_label',
            'connection_points',
            'completed_at', 'verified_at', 'verified_by',
            'installation_notes', 'fault_description',
            'is_complete', 'is_verified',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'completed_at', 'verified_at', 'verified_by',
        ]


class ConnectionCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création d'un raccordement avec validation."""

    class Meta:
        model  = Connection
        fields = [
            'reference', 'name', 'description',
            'cable', 'terminal_origin', 'terminal_dest',
            'connection_type', 'installation_notes',
        ]

    def validate(self, attrs):
        """Validations croisées."""
        terminal_origin = attrs.get('terminal_origin')
        terminal_dest   = attrs.get('terminal_dest')
        cable           = attrs.get('cable')

        # Même borne origine et destination
        if terminal_origin == terminal_dest:
            raise serializers.ValidationError(
                "Les bornes d'origine et de destination doivent être différentes."
            )

        # Borne origine déjà occupée
        if terminal_origin and terminal_origin.is_occupied:
            raise serializers.ValidationError({
                'terminal_origin': f"La borne {terminal_origin} est déjà raccordée."
            })

        # Borne destination déjà occupée
        if terminal_dest and terminal_dest.is_occupied:
            raise serializers.ValidationError({
                'terminal_dest': f"La borne {terminal_dest} est déjà raccordée."
            })

        # Vérification de compatibilité de section
        if cable and terminal_origin:
            cable_section = cable.cable_type.section_mm2
            if cable_section > terminal_origin.max_section_mm2:
                raise serializers.ValidationError({
                    'terminal_origin': (
                        f"Section du câble ({cable_section}mm²) trop grande "
                        f"pour la borne ({terminal_origin.max_section_mm2}mm² max)."
                    )
                })

        return attrs