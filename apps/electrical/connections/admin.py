from django.contrib import admin
from .models import TerminalBlock, Terminal, Connection, ConnectionPoint


class TerminalInline(admin.TabularInline):
    model  = Terminal
    extra  = 0
    fields = ['label', 'position', 'terminal_type', 'max_section_mm2',
              'voltage_rating', 'current_rating', 'is_occupied', 'is_active']
    readonly_fields = ['is_occupied']


@admin.register(TerminalBlock)
class TerminalBlockAdmin(admin.ModelAdmin):
    list_display  = ['reference', 'name', 'equipment_ref', 'voltage_rating',
                     'max_section_mm2', 'terminal_count', 'is_active']
    list_filter   = ['voltage_rating', 'is_active']
    search_fields = ['reference', 'name', 'equipment_ref']
    inlines       = [TerminalInline]


@admin.register(Terminal)
class TerminalAdmin(admin.ModelAdmin):
    list_display  = ['__str__', 'terminal_type', 'max_section_mm2',
                     'voltage_rating', 'is_occupied', 'is_active']
    list_filter   = ['terminal_type', 'is_occupied', 'is_active']
    search_fields = ['label', 'block__reference']


class ConnectionPointInline(admin.TabularInline):
    model  = ConnectionPoint
    extra  = 0
    fields = ['conductor', 'wire_color', 'terminal', 'tightening_torque_nm',
              'has_ferrule', 'is_verified']
    readonly_fields = ['follows_color_convention']


@admin.register(Connection)
class ConnectionAdmin(admin.ModelAdmin):
    list_display   = ['reference', 'cable', 'terminal_origin', 'terminal_dest',
                      'connection_type', 'status', 'verified_by']
    list_filter    = ['status', 'connection_type', 'is_active']
    search_fields  = ['reference', 'cable__reference']
    inlines        = [ConnectionPointInline]
    readonly_fields = ['completed_at', 'verified_at', 'created_at', 'updated_at']