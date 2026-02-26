from django.contrib import admin
from .models import Device, DevicePort, DeviceVulnerability, DeviceScan


class DevicePortInline(admin.TabularInline):
    model   = DevicePort
    extra   = 0
    fields  = ['port_number', 'protocol', 'state', 'service', 'is_authorized', 'last_seen']


class DeviceVulnerabilityInline(admin.TabularInline):
    model   = DeviceVulnerability
    extra   = 0
    fields  = ['cve_id', 'cvss_score', 'severity', 'title', 'status', 'patched_at']
    readonly_fields = ['patched_at']


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display  = [
        'reference', 'name', 'device_type', 'ip_address',
        'status', 'criticality', 'is_monitored',
        'open_vulnerabilities_count', 'unauthorized_ports_count',
        'last_seen'
    ]
    list_filter   = ['device_type', 'status', 'criticality', 'is_monitored', 'vlan']
    search_fields = ['reference', 'name', 'ip_address', 'mac_address', 'hostname']
    inlines       = [DevicePortInline, DeviceVulnerabilityInline]
    readonly_fields = ['last_seen', 'last_scan', 'created_at', 'updated_at']

    fieldsets = (
        ('Identité',         {'fields': ('reference', 'name', 'description',
                                          'device_type', 'status', 'criticality')}),
        ('Réseau',           {'fields': ('ip_address', 'mac_address', 'hostname',
                                          'vlan', 'subnet')}),
        ('Système',          {'fields': ('manufacturer', 'model_name', 'os',
                                          'firmware_version', 'serial_number')}),
        ('Localisation',     {'fields': ('location', 'building', 'room')}),
        ('Électrique',       {'fields': ('power_cable_ref', 'power_supply_voltage',
                                          'power_consumption_w')}),
        ('Supervision',      {'fields': ('is_monitored', 'ping_interval_s',
                                          'last_seen', 'last_scan', 'owner')}),
    )


@admin.register(DeviceVulnerability)
class DeviceVulnerabilityAdmin(admin.ModelAdmin):
    list_display  = ['cve_id', 'device', 'cvss_score', 'severity', 'status', 'detected_at']
    list_filter   = ['severity', 'status']
    search_fields = ['cve_id', 'title', 'device__reference']
    readonly_fields = ['detected_at', 'patched_at']


@admin.register(DeviceScan)
class DeviceScanAdmin(admin.ModelAdmin):
    list_display  = ['device', 'scan_type', 'result', 'started_at',
                     'ports_found', 'vulnerabilities_found', 'critical_vulns_found']
    list_filter   = ['scan_type', 'result']
    search_fields = ['device__reference', 'device__ip_address']
    readonly_fields = ['started_at', 'completed_at']