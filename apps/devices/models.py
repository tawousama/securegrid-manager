"""
Modèles de l'application Devices.

Représente les équipements physiques de l'installation —
passerelle entre le métier électrique et la cybersécurité.

Chaque Device :
- Est alimenté par un câble (lien vers cable_routing)
- A une adresse IP et MAC (supervision réseau)
- Peut avoir des ports ouverts (surface d'attaque)
- Peut avoir des vulnérabilités CVE connues
- Est scanné périodiquement pour détecter les anomalies

Exemple EPR2 :
    Device(
        reference="DEV-SRV-001",
        name="Serveur supervision SNCC",
        device_type="server",
        ip_address="10.0.1.5",
        mac_address="00:1A:2B:3C:4D:5E",
        os="Windows Server 2022",
        firmware_version="21H2",
        power_cable_ref="CAB-EPR-042",
        status="online",
        location="Salle serveurs B, Rack R3, U12"
    )
"""

from django.db import models
from django.utils import timezone
import uuid
from core.models import ReferencedModel, BaseModel
from core.constants import (
    DEVICE_TYPE_CHOICES, DEVICE_STATUS_CHOICES,
    DEVICE_TYPE_SERVER, DEVICE_STATUS_ONLINE,
    ANOMALY_SEVERITY_CHOICES, ANOMALY_SEVERITY_MEDIUM,
)
from core.validators import validate_ip_address, validate_mac_address, validate_port_number


# ============================================================
# MODÈLE 1 : ÉQUIPEMENT (DEVICE)
# ============================================================

class Device(ReferencedModel):
    """
    Un équipement physique dans l'installation.

    Fait le lien entre :
    - L'électrique : alimenté par un câble physique
    - Le réseau    : a une IP, des ports, des services
    - La sécu      : peut avoir des CVE, est scanné

    Champs hérités de ReferencedModel :
    - id, reference, name, description
    - created_at, updated_at, is_active, is_deleted, created_by, updated_by
    """

    # --- Type et statut ---
    device_type = models.CharField(
        max_length=20,
        choices=DEVICE_TYPE_CHOICES,
        default=DEVICE_TYPE_SERVER,
        verbose_name="Type d'équipement",
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=DEVICE_STATUS_CHOICES,
        default=DEVICE_STATUS_ONLINE,
        verbose_name="Statut réseau",
        db_index=True
    )

    # --- Réseau ---
    ip_address = models.GenericIPAddressField(
        unique=True,
        verbose_name="Adresse IP"
    )
    mac_address = models.CharField(
        max_length=17,
        blank=True,
        validators=[validate_mac_address],
        verbose_name="Adresse MAC"
    )
    hostname = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Nom d'hôte (hostname)"
    )
    vlan = models.PositiveSmallIntegerField(
        null=True, blank=True,
        verbose_name="VLAN",
        help_text="Numéro du VLAN (1-4094)"
    )
    subnet = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Sous-réseau",
        help_text="Ex: 10.0.1.0/24"
    )

    # --- Système ---
    manufacturer = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Fabricant",
        help_text="Ex: Dell, Cisco, Schneider Electric"
    )
    model_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Modèle"
    )
    os = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Système d'exploitation"
    )
    firmware_version = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Version firmware/OS"
    )
    serial_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Numéro de série"
    )

    # --- Localisation physique ---
    location = models.CharField(
        max_length=300,
        blank=True,
        verbose_name="Localisation",
        help_text="Ex: Salle serveurs B, Rack R3, Unité 12"
    )
    building = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Bâtiment"
    )
    room = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Salle / Zone"
    )

    # --- Lien électrique ---
    # Référence du câble d'alimentation (lien souple par référence, pas FK)
    power_cable_ref = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Référence câble d'alimentation",
        help_text="Ex: CAB-EPR-042"
    )
    power_supply_voltage = models.IntegerField(
        null=True, blank=True,
        verbose_name="Tension d'alimentation (V)"
    )
    power_consumption_w = models.FloatField(
        null=True, blank=True,
        verbose_name="Consommation (W)"
    )

    # --- Supervision ---
    is_monitored = models.BooleanField(
        default=True,
        verbose_name="Supervisé",
        db_index=True
    )
    last_seen = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Dernière vue"
    )
    last_scan = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Dernier scan"
    )
    ping_interval_s = models.PositiveIntegerField(
        default=300,
        verbose_name="Intervalle de ping (secondes)"
    )

    # --- Criticité ---
    CRITICALITY_LOW      = 'low'
    CRITICALITY_MEDIUM   = 'medium'
    CRITICALITY_HIGH     = 'high'
    CRITICALITY_CRITICAL = 'critical'

    CRITICALITY_CHOICES = [
        (CRITICALITY_LOW,      'Faible'),
        (CRITICALITY_MEDIUM,   'Moyen'),
        (CRITICALITY_HIGH,     'Élevé'),
        (CRITICALITY_CRITICAL, 'Critique'),
    ]

    criticality = models.CharField(
        max_length=10,
        choices=CRITICALITY_CHOICES,
        default=CRITICALITY_MEDIUM,
        verbose_name="Criticité"
    )

    # Responsable de l'équipement
    owner = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='owned_devices',
        verbose_name="Responsable"
    )

    class Meta:
        verbose_name        = "Équipement"
        verbose_name_plural = "Équipements"
        ordering            = ['reference']

    def __str__(self):
        return f"{self.reference} — {self.name} ({self.ip_address})"

    @property
    def is_online(self):
        return self.status == DEVICE_STATUS_ONLINE

    @property
    def open_vulnerabilities_count(self):
        return self.vulnerabilities.filter(
            status__in=[
                DeviceVulnerability.STATUS_OPEN,
                DeviceVulnerability.STATUS_IN_PROGRESS
            ]
        ).count()

    @property
    def critical_vulnerabilities_count(self):
        return self.vulnerabilities.filter(
            severity=DeviceVulnerability.SEVERITY_CRITICAL,
            status=DeviceVulnerability.STATUS_OPEN
        ).count()

    @property
    def unauthorized_ports_count(self):
        return self.ports.filter(
            state=DevicePort.STATE_OPEN,
            is_authorized=False
        ).count()

    def mark_online(self):
        """Marque l'équipement comme en ligne."""
        self.status    = DEVICE_STATUS_ONLINE
        self.last_seen = timezone.now()
        self.save(update_fields=['status', 'last_seen'])

    def mark_offline(self):
        """Marque l'équipement comme hors ligne."""
        from core.constants import DEVICE_STATUS_OFFLINE
        self.status = DEVICE_STATUS_OFFLINE
        self.save(update_fields=['status'])


# ============================================================
# MODÈLE 2 : PORT RÉSEAU
# ============================================================

class DevicePort(BaseModel):
    """
    Un port réseau ouvert sur un équipement.

    Permet d'identifier la surface d'attaque d'un équipement :
    quels services sont exposés, lesquels sont autorisés.

    Exemple pour un serveur de supervision industrielle :
    - Port 22  TCP SSH       → autorisé (administration)
    - Port 443 TCP HTTPS     → autorisé (interface web)
    - Port 502 TCP Modbus    → autorisé (protocole industriel)
    - Port 4444 TCP          → NON AUTORISÉ → alerte critique !
    """

    PROTOCOL_TCP  = 'tcp'
    PROTOCOL_UDP  = 'udp'
    PROTOCOL_SCTP = 'sctp'

    PROTOCOL_CHOICES = [
        (PROTOCOL_TCP,  'TCP'),
        (PROTOCOL_UDP,  'UDP'),
        (PROTOCOL_SCTP, 'SCTP'),
    ]

    STATE_OPEN     = 'open'
    STATE_CLOSED   = 'closed'
    STATE_FILTERED = 'filtered'

    STATE_CHOICES = [
        (STATE_OPEN,     'Ouvert'),
        (STATE_CLOSED,   'Fermé'),
        (STATE_FILTERED, 'Filtré'),
    ]

    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='ports',
        verbose_name="Équipement"
    )
    port_number = models.PositiveIntegerField(
        validators=[validate_port_number],
        verbose_name="Numéro de port"
    )
    protocol = models.CharField(
        max_length=5,
        choices=PROTOCOL_CHOICES,
        default=PROTOCOL_TCP,
        verbose_name="Protocole"
    )
    state = models.CharField(
        max_length=10,
        choices=STATE_CHOICES,
        default=STATE_OPEN,
        verbose_name="État"
    )
    service = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Service",
        help_text="Ex: SSH, HTTPS, Modbus, DNP3, IEC-61850"
    )
    service_version = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Version du service"
    )
    is_authorized = models.BooleanField(
        default=True,
        verbose_name="Autorisé",
        help_text="Port présent dans la liste blanche de sécurité"
    )
    first_seen = models.DateTimeField(
        default=timezone.now,
        verbose_name="Première détection"
    )
    last_seen = models.DateTimeField(
        default=timezone.now,
        verbose_name="Dernière détection"
    )

    class Meta:
        verbose_name        = "Port réseau"
        verbose_name_plural = "Ports réseau"
        unique_together     = [('device', 'port_number', 'protocol')]
        ordering            = ['device', 'port_number']

    def __str__(self):
        auth = "✅" if self.is_authorized else "⚠️"
        return f"{self.device.ip_address}:{self.port_number}/{self.protocol} {auth}"


# ============================================================
# MODÈLE 3 : VULNÉRABILITÉ CVE
# ============================================================

class DeviceVulnerability(BaseModel):
    """
    Une vulnérabilité de sécurité (CVE) sur un équipement.

    CVE = Common Vulnerabilities and Exposures
    CVSS = Common Vulnerability Scoring System (0.0 à 10.0)

    Cycle de vie :
    OPEN → IN_PROGRESS → PATCHED
    OPEN → ACCEPTED (risque accepté avec justification)

    Score CVSS :
    0.0–3.9  : LOW
    4.0–6.9  : MEDIUM
    7.0–8.9  : HIGH
    9.0–10.0 : CRITICAL
    """

    SEVERITY_LOW      = 'low'
    SEVERITY_MEDIUM   = 'medium'
    SEVERITY_HIGH     = 'high'
    SEVERITY_CRITICAL = 'critical'

    SEVERITY_CHOICES = [
        (SEVERITY_LOW,      'Faible (0.0–3.9)'),
        (SEVERITY_MEDIUM,   'Moyen (4.0–6.9)'),
        (SEVERITY_HIGH,     'Élevé (7.0–8.9)'),
        (SEVERITY_CRITICAL, 'Critique (9.0–10.0)'),
    ]

    STATUS_OPEN        = 'open'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_PATCHED     = 'patched'
    STATUS_ACCEPTED    = 'accepted'

    STATUS_CHOICES = [
        (STATUS_OPEN,        'Ouverte'),
        (STATUS_IN_PROGRESS, 'En cours de correction'),
        (STATUS_PATCHED,     'Corrigée'),
        (STATUS_ACCEPTED,    'Risque accepté'),
    ]

    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='vulnerabilities',
        verbose_name="Équipement"
    )

    # Identification CVE
    cve_id = models.CharField(
        max_length=20,
        verbose_name="Identifiant CVE",
        help_text="Ex: CVE-2024-1234"
    )
    instance_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        verbose_name="ID d'instance unique"
    )

    cvss_score = models.FloatField(
        verbose_name="Score CVSS",
        help_text="Score de 0.0 (aucun risque) à 10.0 (critique maximal)"
    )
    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_CHOICES,
        verbose_name="Sévérité"
    )

    # Description et correction
    title = models.CharField(max_length=300, verbose_name="Titre")
    description = models.TextField(blank=True, verbose_name="Description")
    affected_component = models.CharField(
        max_length=200, blank=True,
        verbose_name="Composant affecté",
        help_text="Ex: OpenSSL 3.0.x, Windows SMBv1"
    )
    remediation = models.TextField(
        blank=True,
        verbose_name="Action corrective",
        help_text="Patch disponible, contournement, mise à jour..."
    )

    # Statut et traitement
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN,
        verbose_name="Statut",
        db_index=True
    )
    patched_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Corrigée le"
    )
    patched_by = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='patched_vulnerabilities',
        verbose_name="Corrigée par"
    )
    acceptance_justification = models.TextField(
        blank=True,
        verbose_name="Justification acceptation du risque"
    )
    detected_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Détectée le"
    )

    class Meta:
        verbose_name        = "Vulnérabilité"
        verbose_name_plural = "Vulnérabilités"
        unique_together     = [('device', 'cve_id')]
        ordering            = ['-cvss_score', 'status']

    def __str__(self):
        return f"{self.device.reference} — {self.cve_id} ({self.severity})"

    @classmethod
    def severity_from_score(cls, score: float) -> str:
        """Détermine la sévérité depuis le score CVSS."""
        if score >= 9.0:
            return cls.SEVERITY_CRITICAL
        if score >= 7.0:
            return cls.SEVERITY_HIGH
        if score >= 4.0:
            return cls.SEVERITY_MEDIUM
        return cls.SEVERITY_LOW


# ============================================================
# MODÈLE 4 : SCAN DE SÉCURITÉ
# ============================================================

class DeviceScan(BaseModel):
    """
    Un scan de sécurité effectué sur un équipement.

    Types de scans :
    - PING      : Simple vérification de disponibilité
    - PORT_SCAN : Découverte des ports ouverts
    - VULN_SCAN : Analyse des vulnérabilités CVE
    - FULL      : Scan complet (ping + ports + vulnérabilités)

    Les résultats sont stockés en JSON pour flexibilité.
    """

    SCAN_PING  = 'ping'
    SCAN_PORT  = 'port_scan'
    SCAN_VULN  = 'vuln_scan'
    SCAN_FULL  = 'full'

    SCAN_TYPE_CHOICES = [
        (SCAN_PING, 'Ping (disponibilité)'),
        (SCAN_PORT, 'Scan de ports'),
        (SCAN_VULN, 'Scan de vulnérabilités'),
        (SCAN_FULL, 'Scan complet'),
    ]

    RESULT_SUCCESS = 'success'
    RESULT_FAILED  = 'failed'
    RESULT_PARTIAL = 'partial'

    RESULT_CHOICES = [
        (RESULT_SUCCESS, 'Succès'),
        (RESULT_FAILED,  'Échec'),
        (RESULT_PARTIAL, 'Partiel'),
    ]

    device    = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='scans',
        verbose_name="Équipement"
    )
    scan_type = models.CharField(
        max_length=15,
        choices=SCAN_TYPE_CHOICES,
        verbose_name="Type de scan"
    )
    started_at   = models.DateTimeField(default=timezone.now, verbose_name="Début")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Fin")
    result       = models.CharField(
        max_length=10,
        choices=RESULT_CHOICES,
        null=True, blank=True,
        verbose_name="Résultat"
    )
    launched_by  = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Lancé par"
    )

    # Résultats bruts JSON
    scan_data = models.JSONField(
        default=dict, blank=True,
        verbose_name="Données du scan"
    )

    # Statistiques
    ports_found              = models.PositiveIntegerField(default=0)
    open_ports_found         = models.PositiveIntegerField(default=0)
    unauthorized_ports_found = models.PositiveIntegerField(default=0)
    vulnerabilities_found    = models.PositiveIntegerField(default=0)
    critical_vulns_found     = models.PositiveIntegerField(default=0)

    error_message = models.TextField(blank=True, verbose_name="Message d'erreur")

    class Meta:
        verbose_name        = "Scan de sécurité"
        verbose_name_plural = "Scans de sécurité"
        ordering            = ['-started_at']

    def __str__(self):
        return f"{self.device.reference} — {self.scan_type} — {self.started_at:%Y-%m-%d %H:%M}"

    @property
    def duration_seconds(self):
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None