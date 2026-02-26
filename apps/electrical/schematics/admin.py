from django.contrib import admin
from .models import Schematic, SchematicElement, SchematicLink, SchematicRevision


class SchematicElementInline(admin.TabularInline):
    model   = SchematicElement
    extra   = 0
    fields  = ['element_type', 'label', 'x', 'y', 'is_visible']


class SchematicLinkInline(admin.TabularInline):
    model   = SchematicLink
    extra   = 0
    fields  = ['source_element', 'target_element', 'label', 'line_style']


class SchematicRevisionInline(admin.TabularInline):
    model        = SchematicRevision
    extra        = 0
    fields       = ['version', 'description', 'author', 'created_at']
    readonly_fields = ['created_at']


@admin.register(Schematic)
class SchematicAdmin(admin.ModelAdmin):
    list_display  = ['reference', 'title', 'schematic_type', 'status',
                     'version', 'project_ref', 'element_count', 'is_active']
    list_filter   = ['schematic_type', 'status', 'standard', 'is_active']
    search_fields = ['reference', 'title', 'project_ref']
    inlines       = [SchematicElementInline, SchematicLinkInline, SchematicRevisionInline]
    readonly_fields = ['reviewed_at', 'approved_at', 'created_at', 'updated_at']


@admin.register(SchematicElement)
class SchematicElementAdmin(admin.ModelAdmin):
    list_display = ['label', 'element_type', 'schematic', 'x', 'y', 'is_visible']
    list_filter  = ['element_type', 'is_visible']
    search_fields = ['label', 'schematic__reference']


@admin.register(SchematicRevision)
class SchematicRevisionAdmin(admin.ModelAdmin):
    list_display = ['schematic', 'version', 'author', 'created_at']
    readonly_fields = ['created_at']