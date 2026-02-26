"""
Serializers de l'application Cable Routing.

Convertissent les modèles Python ↔ JSON pour l'API REST.
Chaque serializer valide aussi les données entrantes.
"""

from rest_framework import serializers
from .models import CableType, Cable, CablePathway, CableRoute, RouteWaypoint


# ============================================================
# SERIALIZER : TYPE DE CÂBLE
# ============================================================

class CableTypeSerializer(serializers.ModelSerializer):
    """Sérialise un type de câble pour l'API."""

    cable_category_label = serializers.CharField(
        source='get_cable_category_display',
        read_only=True
    )
    standard_label = serializers.CharField(
        source='get_standard_display',
        read_only=True
    )

    class Meta:
        model  = CableType
        fields = [
            'id', 'name', 'description',
            'cable_category', 'cable_category_label',
            'section_mm2', 'voltage_max', 'conductor_count',
            'conductor_material', 'standard', 'standard_label',
            'standard_reference', 'outer_diameter_mm',
            'weight_kg_per_m', 'min_bending_radius_mm',
            'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


# ============================================================
# SERIALIZER : CHEMIN DE CÂBLES
# ============================================================

class CablePathwaySerializer(serializers.ModelSerializer):
    """Sérialise un chemin de câbles."""

    length_m          = serializers.FloatField(read_only=True)
    cross_section_mm2 = serializers.FloatField(read_only=True)
    usable_section_mm2 = serializers.FloatField(read_only=True)
    pathway_type_label = serializers.CharField(
        source='get_pathway_type_display',
        read_only=True
    )

    class Meta:
        model  = CablePathway
        fields = [
            'id', 'name', 'description',
            'pathway_type', 'pathway_type_label',
            'width_mm', 'height_mm', 'max_fill_ratio',
            'start_x', 'start_y', 'start_z',
            'end_x',   'end_y',   'end_z',
            'length_m', 'cross_section_mm2', 'usable_section_mm2',
            'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


# ============================================================
# SERIALIZER : WAYPOINT
# ============================================================

class RouteWaypointSerializer(serializers.ModelSerializer):
    """Sérialise un point de passage d'un tracé."""

    class Meta:
        model  = RouteWaypoint
        fields = ['id', 'order', 'x', 'y', 'z', 'pathway', 'label']


# ============================================================
# SERIALIZER : TRACÉ DE CÂBLE
# ============================================================

class CableRouteSerializer(serializers.ModelSerializer):
    """Sérialise un tracé complet avec ses waypoints."""

    waypoints = RouteWaypointSerializer(many=True, read_only=True)

    class Meta:
        model  = CableRoute
        fields = [
            'id', 'cable', 'is_active', 'is_optimized',
            'total_length_m', 'calculation_notes',
            'waypoints', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


# ============================================================
# SERIALIZER : CÂBLE (liste)
# ============================================================

class CableListSerializer(serializers.ModelSerializer):
    """
    Serializer allégé pour la liste des câbles.
    N'inclut pas les détails du tracé pour de meilleures performances.
    """

    cable_type_name = serializers.CharField(
        source='cable_type.name',
        read_only=True
    )
    status_label = serializers.CharField(
        source='get_status_display',
        read_only=True
    )

    class Meta:
        model  = Cable
        fields = [
            'id', 'reference', 'name',
            'cable_type', 'cable_type_name',
            'status', 'status_label',
            'designed_length_m', 'actual_length_m',
            'origin_label', 'destination_label',
            'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


# ============================================================
# SERIALIZER : CÂBLE (détail)
# ============================================================

class CableDetailSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour le détail d'un câble.
    Inclut les infos du type de câble et le tracé actif.
    """

    cable_type_detail = CableTypeSerializer(source='cable_type', read_only=True)
    active_route      = serializers.SerializerMethodField()
    status_label      = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    effective_length  = serializers.FloatField(read_only=True)

    class Meta:
        model  = Cable
        fields = [
            'id', 'reference', 'name', 'description',
            'cable_type', 'cable_type_detail',
            'status', 'status_label',
            'designed_length_m', 'actual_length_m', 'effective_length',
            'origin_label', 'destination_label',
            'origin_x', 'origin_y', 'origin_z',
            'dest_x',   'dest_y',   'dest_z',
            'design_current_a', 'operating_voltage',
            'installation_notes',
            'active_route',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_active_route(self, obj):
        """Retourne le tracé actif du câble."""
        route = obj.routes.filter(is_active=True).first()
        if route:
            return CableRouteSerializer(route).data
        return None


# ============================================================
# SERIALIZER : DEMANDE DE ROUTAGE AUTOMATIQUE
# ============================================================

class CableRouteRequestSerializer(serializers.Serializer):
    """
    Valide une demande de calcul automatique de tracé.

    L'utilisateur fournit les coordonnées d'origine et de destination,
    le routing engine calcule le chemin optimal.
    """

    # Point de départ
    origin_x = serializers.FloatField(help_text="Coordonnée X de l'origine (m)")
    origin_y = serializers.FloatField(help_text="Coordonnée Y de l'origine (m)")
    origin_z = serializers.FloatField(default=0, help_text="Coordonnée Z de l'origine (m)")

    # Point d'arrivée
    dest_x = serializers.FloatField(help_text="Coordonnée X de la destination (m)")
    dest_y = serializers.FloatField(help_text="Coordonnée Y de la destination (m)")
    dest_z = serializers.FloatField(default=0, help_text="Coordonnée Z de la destination (m)")

    # Options
    optimize   = serializers.BooleanField(
        default=True,
        help_text="Optimiser le tracé après calcul"
    )
    max_length = serializers.FloatField(
        required=False,
        help_text="Longueur maximale acceptable (m). Optionnel."
    )

    def validate(self, attrs):
        """Vérifie que l'origine et la destination sont différentes."""
        same_x = attrs['origin_x'] == attrs['dest_x']
        same_y = attrs['origin_y'] == attrs['dest_y']
        same_z = attrs['origin_z'] == attrs['dest_z']
        if same_x and same_y and same_z:
            raise serializers.ValidationError(
                "L'origine et la destination ne peuvent pas être identiques."
            )
        return attrs