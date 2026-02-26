"""Serializers de l'application Devices."""

from rest_framework import serializers
from .models import Device, DevicePort, DeviceVulnerability, DeviceScan


class DevicePortSerializer(serializers.ModelSerializer):
    state_label    = serializers.CharField(source='get_state_display', read_only=True)
    protocol_label = serializers.CharField(source='get_protocol_display', read_only=True)

    class Meta:
        model  = DevicePort
        fields = [
            'id', 'port_number', 'protocol', 'protocol_label',
            'state', 'state_label', 'service', 'service_version',
            'is_authorized', 'first_seen', 'last_seen',
        ]
        read_only_fields = ['id', 'first_seen']


class DeviceVulnerabilitySerializer(serializers.ModelSerializer):
    severity_label = serializers.CharField(source='get_severity_display', read_only=True)
    status_label   = serializers.CharField(source='get_status_display', read_only=True)
    patched_by_name = serializers.SerializerMethodField()

    class Meta:
        model  = DeviceVulnerability
        fields = [
            'id', 'cve_id', 'cvss_score',
            'severity', 'severity_label',
            'title', 'description', 'affected_component', 'remediation',
            'status', 'status_label',
            'patched_at', 'patched_by', 'patched_by_name',
            'acceptance_justification', 'detected_at',
        ]
        read_only_fields = ['id', 'detected_at']

    def get_patched_by_name(self, obj):
        return obj.patched_by.full_name if obj.patched_by else None

    def validate_cvss_score(self, value):
        if not (0.0 <= value <= 10.0):
            raise serializers.ValidationError("Le score CVSS doit être entre 0.0 et 10.0.")
        return value

    def validate(self, attrs):
        # Auto-calculer la sévérité depuis le score
        if 'cvss_score' in attrs and 'severity' not in attrs:
            attrs['severity'] = DeviceVulnerability.severity_from_score(attrs['cvss_score'])
        return attrs


class DeviceScanSerializer(serializers.ModelSerializer):
    scan_type_label  = serializers.CharField(source='get_scan_type_display', read_only=True)
    result_label     = serializers.CharField(source='get_result_display', read_only=True)
    launched_by_name = serializers.SerializerMethodField()
    duration_seconds = serializers.FloatField(read_only=True)

    class Meta:
        model  = DeviceScan
        fields = [
            'id', 'scan_type', 'scan_type_label',
            'started_at', 'completed_at', 'duration_seconds',
            'result', 'result_label',
            'launched_by', 'launched_by_name',
            'ports_found', 'open_ports_found', 'unauthorized_ports_found',
            'vulnerabilities_found', 'critical_vulns_found',
            'error_message',
        ]
        read_only_fields = ['id', 'started_at']

    def get_launched_by_name(self, obj):
        return obj.launched_by.full_name if obj.launched_by else 'Automatique'


class DeviceListSerializer(serializers.ModelSerializer):
    """Version allégée pour les listes."""
    device_type_label  = serializers.CharField(source='get_device_type_display', read_only=True)
    status_label       = serializers.CharField(source='get_status_display', read_only=True)
    criticality_label  = serializers.CharField(source='get_criticality_display', read_only=True)
    open_vulnerabilities_count  = serializers.IntegerField(read_only=True)
    critical_vulnerabilities_count = serializers.IntegerField(read_only=True)
    unauthorized_ports_count    = serializers.IntegerField(read_only=True)
    is_online                   = serializers.BooleanField(read_only=True)

    class Meta:
        model  = Device
        fields = [
            'id', 'reference', 'name',
            'device_type', 'device_type_label',
            'ip_address', 'hostname', 'vlan',
            'status', 'status_label', 'criticality', 'criticality_label',
            'is_monitored', 'last_seen',
            'open_vulnerabilities_count',
            'critical_vulnerabilities_count',
            'unauthorized_ports_count',
            'is_online', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class DeviceDetailSerializer(serializers.ModelSerializer):
    """Version complète avec ports, vulnérabilités et scans récents."""
    device_type_label = serializers.CharField(source='get_device_type_display', read_only=True)
    status_label      = serializers.CharField(source='get_status_display', read_only=True)
    criticality_label = serializers.CharField(source='get_criticality_display', read_only=True)
    ports             = DevicePortSerializer(many=True, read_only=True)
    vulnerabilities   = DeviceVulnerabilitySerializer(many=True, read_only=True)
    recent_scans      = serializers.SerializerMethodField()
    owner_name        = serializers.SerializerMethodField()
    open_vulnerabilities_count    = serializers.IntegerField(read_only=True)
    critical_vulnerabilities_count = serializers.IntegerField(read_only=True)
    unauthorized_ports_count      = serializers.IntegerField(read_only=True)
    is_online                     = serializers.BooleanField(read_only=True)

    class Meta:
        model  = Device
        fields = [
            'id', 'reference', 'name', 'description',
            'device_type', 'device_type_label',
            'status', 'status_label', 'criticality', 'criticality_label',
            'ip_address', 'mac_address', 'hostname', 'vlan', 'subnet',
            'manufacturer', 'model_name', 'os', 'firmware_version', 'serial_number',
            'location', 'building', 'room',
            'power_cable_ref', 'power_supply_voltage', 'power_consumption_w',
            'is_monitored', 'last_seen', 'last_scan', 'ping_interval_s',
            'owner', 'owner_name',
            'ports', 'vulnerabilities', 'recent_scans',
            'open_vulnerabilities_count',
            'critical_vulnerabilities_count',
            'unauthorized_ports_count',
            'is_online', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_seen', 'last_scan']

    def get_recent_scans(self, obj):
        scans = obj.scans.order_by('-started_at')[:5]
        return DeviceScanSerializer(scans, many=True).data

    def get_owner_name(self, obj):
        return obj.owner.full_name if obj.owner else None