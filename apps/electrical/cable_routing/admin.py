from django.contrib import admin
from .models import CableType, Cable, CablePathway, CableRoute, RouteWaypoint


@admin.register(CableType)
class CableTypeAdmin(admin.ModelAdmin):
    list_display  = ['name', 'cable_category', 'section_mm2', 'voltage_max', 'standard', 'is_active']
    list_filter   = ['cable_category', 'standard', 'conductor_material', 'is_active']
    search_fields = ['name', 'standard_reference']


@admin.register(CablePathway)
class CablePathwayAdmin(admin.ModelAdmin):
    list_display  = ['name', 'pathway_type', 'width_mm', 'height_mm', 'is_active']
    list_filter   = ['pathway_type', 'is_active']
    search_fields = ['name']


class RouteWaypointInline(admin.TabularInline):
    """Affiche les waypoints directement dans la page d'un tracé."""
    model  = RouteWaypoint
    extra  = 0
    fields = ['order', 'x', 'y', 'z', 'pathway', 'label']


class CableRouteInline(admin.TabularInline):
    """Affiche les tracés directement dans la page d'un câble."""
    model      = CableRoute
    extra      = 0
    fields     = ['is_active', 'is_optimized', 'total_length_m']
    readonly_fields = ['total_length_m']


@admin.register(Cable)
class CableAdmin(admin.ModelAdmin):
    list_display   = ['reference', 'name', 'cable_type', 'status',
                      'designed_length_m', 'origin_label', 'destination_label']
    list_filter    = ['status', 'cable_type__cable_category', 'is_active']
    search_fields  = ['reference', 'name', 'origin_label', 'destination_label']
    inlines        = [CableRouteInline]
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CableRoute)
class CableRouteAdmin(admin.ModelAdmin):
    list_display  = ['cable', 'is_active', 'is_optimized', 'total_length_m', 'created_at']
    list_filter   = ['is_active', 'is_optimized']
    inlines       = [RouteWaypointInline]
    readonly_fields = ['created_at']