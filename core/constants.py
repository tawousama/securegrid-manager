"""
Constantes globales du projet ElectroSecure Platform.

Ce fichier centralise toutes les valeurs fixes du projet :
- Choix de champs (choices)
- Codes de statut
- Limites et seuils
- Codes métier électricité

Avantages :
- Un seul endroit à modifier
- Pas de "magic strings" éparpillées dans le code
- Auto-complétion dans l'éditeur
- Cohérence garantie partout
"""

# ============================================================
# STATUTS GÉNÉRIQUES
# ============================================================

STATUS_ACTIVE     = 'active'
STATUS_INACTIVE   = 'inactive'
STATUS_PENDING    = 'pending'
STATUS_ARCHIVED   = 'archived'

GENERIC_STATUS_CHOICES = [
    (STATUS_ACTIVE,   'Actif'),
    (STATUS_INACTIVE, 'Inactif'),
    (STATUS_PENDING,  'En attente'),
    (STATUS_ARCHIVED, 'Archivé'),
]


# ============================================================
# RÔLES UTILISATEURS
# ============================================================

ROLE_ADMIN      = 'admin'
ROLE_ENGINEER   = 'engineer'
ROLE_TECHNICIAN = 'technician'
ROLE_VIEWER     = 'viewer'

USER_ROLE_CHOICES = [
    (ROLE_ADMIN,      'Administrateur'),
    (ROLE_ENGINEER,   'Ingénieur'),
    (ROLE_TECHNICIAN, 'Technicien'),
    (ROLE_VIEWER,     'Lecteur'),
]


# ============================================================
# ÉQUIPEMENTS / DEVICES
# ============================================================

DEVICE_TYPE_SERVER     = 'server'
DEVICE_TYPE_PRINTER    = 'printer'
DEVICE_TYPE_IOT        = 'iot'
DEVICE_TYPE_SWITCH     = 'switch'
DEVICE_TYPE_SENSOR     = 'sensor'
DEVICE_TYPE_CONTROLLER = 'controller'

DEVICE_TYPE_CHOICES = [
    (DEVICE_TYPE_SERVER,     'Serveur'),
    (DEVICE_TYPE_PRINTER,    'Imprimante'),
    (DEVICE_TYPE_IOT,        'Dispositif IoT'),
    (DEVICE_TYPE_SWITCH,     'Switch réseau'),
    (DEVICE_TYPE_SENSOR,     'Capteur'),
    (DEVICE_TYPE_CONTROLLER, 'Contrôleur'),
]

DEVICE_STATUS_ONLINE      = 'online'
DEVICE_STATUS_OFFLINE     = 'offline'
DEVICE_STATUS_MAINTENANCE = 'maintenance'
DEVICE_STATUS_FAULT       = 'fault'

DEVICE_STATUS_CHOICES = [
    (DEVICE_STATUS_ONLINE,      'En ligne'),
    (DEVICE_STATUS_OFFLINE,     'Hors ligne'),
    (DEVICE_STATUS_MAINTENANCE, 'En maintenance'),
    (DEVICE_STATUS_FAULT,       'En défaut'),
]


# ============================================================
# MÉTIER ÉLECTRICITÉ — CÂBLES
# ============================================================

CABLE_TYPE_POWER   = 'power'
CABLE_TYPE_DATA    = 'data'
CABLE_TYPE_CONTROL = 'control'
CABLE_TYPE_FIBER   = 'fiber'
CABLE_TYPE_GROUND  = 'ground'

CABLE_TYPE_CHOICES = [
    (CABLE_TYPE_POWER,   'Alimentation'),
    (CABLE_TYPE_DATA,    'Données'),
    (CABLE_TYPE_CONTROL, 'Contrôle'),
    (CABLE_TYPE_FIBER,   'Fibre optique'),
    (CABLE_TYPE_GROUND,  'Terre / Masse'),
]

# Sections de câbles standard (en mm²)
CABLE_SECTION_CHOICES = [
    (1.5,  '1.5 mm²'),
    (2.5,  '2.5 mm²'),
    (4.0,  '4 mm²'),
    (6.0,  '6 mm²'),
    (10.0, '10 mm²'),
    (16.0, '16 mm²'),
    (25.0, '25 mm²'),
    (35.0, '35 mm²'),
    (50.0, '50 mm²'),
    (70.0, '70 mm²'),
    (95.0, '95 mm²'),
    (120.0,'120 mm²'),
    (150.0,'150 mm²'),
    (185.0,'185 mm²'),
    (240.0,'240 mm²'),
]

# Tensions nominales (en Volts)
VOLTAGE_12V    = 12
VOLTAGE_24V    = 24
VOLTAGE_48V    = 48
VOLTAGE_110V   = 110
VOLTAGE_230V   = 230
VOLTAGE_400V   = 400
VOLTAGE_1000V  = 1000
VOLTAGE_6600V  = 6600
VOLTAGE_20000V = 20000

VOLTAGE_CHOICES = [
    (VOLTAGE_12V,    '12 V'),
    (VOLTAGE_24V,    '24 V'),
    (VOLTAGE_48V,    '48 V'),
    (VOLTAGE_110V,   '110 V'),
    (VOLTAGE_230V,   '230 V'),
    (VOLTAGE_400V,   '400 V'),
    (VOLTAGE_1000V,  '1 000 V'),
    (VOLTAGE_6600V,  '6 600 V'),
    (VOLTAGE_20000V, '20 000 V'),
]

# Statut de câble
CABLE_STATUS_PLANNED    = 'planned'
CABLE_STATUS_INSTALLED  = 'installed'
CABLE_STATUS_ACTIVE     = 'active'
CABLE_STATUS_FAULTY     = 'faulty'
CABLE_STATUS_DECOMMISSIONED = 'decommissioned'

CABLE_STATUS_CHOICES = [
    (CABLE_STATUS_PLANNED,        'Planifié'),
    (CABLE_STATUS_INSTALLED,      'Installé'),
    (CABLE_STATUS_ACTIVE,         'Actif'),
    (CABLE_STATUS_FAULTY,         'Défectueux'),
    (CABLE_STATUS_DECOMMISSIONED, 'Mis hors service'),
]


# ============================================================
# MÉTIER ÉLECTRICITÉ — RACCORDEMENTS
# ============================================================

CONNECTION_TYPE_TERMINAL  = 'terminal'
CONNECTION_TYPE_JUNCTION  = 'junction'
CONNECTION_TYPE_PLUG      = 'plug'
CONNECTION_TYPE_CRIMP     = 'crimp'
CONNECTION_TYPE_WELD      = 'weld'

CONNECTION_TYPE_CHOICES = [
    (CONNECTION_TYPE_TERMINAL, 'Borne à vis'),
    (CONNECTION_TYPE_JUNCTION, 'Jonction'),
    (CONNECTION_TYPE_PLUG,     'Connecteur enfichable'),
    (CONNECTION_TYPE_CRIMP,    'Sertissage'),
    (CONNECTION_TYPE_WELD,     'Soudure'),
]


# ============================================================
# NORMES ÉLECTRIQUES
# ============================================================

STANDARD_NF    = 'NF'
STANDARD_IEC   = 'IEC'
STANDARD_IEEE  = 'IEEE'
STANDARD_ISO   = 'ISO'
STANDARD_EN    = 'EN'

ELECTRICAL_STANDARD_CHOICES = [
    (STANDARD_NF,   'Norme Française (NF)'),
    (STANDARD_IEC,  'Commission Électrotechnique Internationale (IEC)'),
    (STANDARD_IEEE, 'Institute of Electrical and Electronics Engineers (IEEE)'),
    (STANDARD_ISO,  'Organisation internationale de normalisation (ISO)'),
    (STANDARD_EN,   'Norme Européenne (EN)'),
]


# ============================================================
# PROJETS ÉNERGÉTIQUES
# ============================================================

PROJECT_TYPE_NUCLEAR    = 'nuclear'
PROJECT_TYPE_RENEWABLE  = 'renewable'
PROJECT_TYPE_GRID       = 'grid'
PROJECT_TYPE_INDUSTRIAL = 'industrial'

PROJECT_TYPE_CHOICES = [
    (PROJECT_TYPE_NUCLEAR,    'Nucléaire'),
    (PROJECT_TYPE_RENEWABLE,  'Énergies renouvelables'),
    (PROJECT_TYPE_GRID,       'Réseau électrique'),
    (PROJECT_TYPE_INDUSTRIAL, 'Industriel'),
]

PROJECT_STATUS_DRAFT      = 'draft'
PROJECT_STATUS_ACTIVE     = 'active'
PROJECT_STATUS_ON_HOLD    = 'on_hold'
PROJECT_STATUS_COMPLETED  = 'completed'
PROJECT_STATUS_CANCELLED  = 'cancelled'

PROJECT_STATUS_CHOICES = [
    (PROJECT_STATUS_DRAFT,     'Brouillon'),
    (PROJECT_STATUS_ACTIVE,    'En cours'),
    (PROJECT_STATUS_ON_HOLD,   'En pause'),
    (PROJECT_STATUS_COMPLETED, 'Terminé'),
    (PROJECT_STATUS_CANCELLED, 'Annulé'),
]


# ============================================================
# ANOMALIES
# ============================================================

ANOMALY_SEVERITY_LOW      = 'low'
ANOMALY_SEVERITY_MEDIUM   = 'medium'
ANOMALY_SEVERITY_HIGH     = 'high'
ANOMALY_SEVERITY_CRITICAL = 'critical'

ANOMALY_SEVERITY_CHOICES = [
    (ANOMALY_SEVERITY_LOW,      'Faible'),
    (ANOMALY_SEVERITY_MEDIUM,   'Moyen'),
    (ANOMALY_SEVERITY_HIGH,     'Élevé'),
    (ANOMALY_SEVERITY_CRITICAL, 'Critique'),
]

ANOMALY_STATUS_OPEN        = 'open'
ANOMALY_STATUS_IN_PROGRESS = 'in_progress'
ANOMALY_STATUS_RESOLVED    = 'resolved'
ANOMALY_STATUS_CLOSED      = 'closed'

ANOMALY_STATUS_CHOICES = [
    (ANOMALY_STATUS_OPEN,        'Ouverte'),
    (ANOMALY_STATUS_IN_PROGRESS, 'En cours de résolution'),
    (ANOMALY_STATUS_RESOLVED,    'Résolue'),
    (ANOMALY_STATUS_CLOSED,      'Clôturée'),
]


# ============================================================
# LIMITES ET SEUILS
# ============================================================

# Tailles de fichiers
MAX_FILE_SIZE_MB        = 10
MAX_FILE_SIZE_BYTES     = MAX_FILE_SIZE_MB * 1024 * 1024  # 10 MB
MAX_IMAGE_SIZE_MB       = 5
MAX_IMAGE_SIZE_BYTES    = MAX_IMAGE_SIZE_MB * 1024 * 1024  # 5 MB
MAX_DOCUMENT_SIZE_MB    = 50
MAX_DOCUMENT_SIZE_BYTES = MAX_DOCUMENT_SIZE_MB * 1024 * 1024  # 50 MB

# Longueurs de champs
MAX_NAME_LENGTH         = 255
MAX_DESCRIPTION_LENGTH  = 2000
MAX_CODE_LENGTH         = 50
MAX_REFERENCE_LENGTH    = 100
MAX_COMMENT_LENGTH      = 1000

# Pagination
DEFAULT_PAGE_SIZE       = 50
MAX_PAGE_SIZE           = 200

# Sécurité
PASSWORD_MIN_LENGTH     = 12
MAX_LOGIN_ATTEMPTS      = 5
LOCKOUT_DURATION_MINUTES = 30
JWT_ACCESS_TOKEN_LIFETIME_MINUTES = 60
JWT_REFRESH_TOKEN_LIFETIME_DAYS   = 1


# ============================================================
# FORMATS ET TYPES DE FICHIERS
# ============================================================

ALLOWED_IMAGE_TYPES = [
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
]

ALLOWED_DOCUMENT_TYPES = [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
]

ALLOWED_FILE_EXTENSIONS = [
    '.pdf', '.doc', '.docx',
    '.xls', '.xlsx', '.csv',
    '.jpg', '.jpeg', '.png',
    '.svg', '.dwg', '.dxf',
]