"""
Validateurs personnalisés du projet ElectroSecure Platform.

Un validateur est une fonction qui :
1. Reçoit une valeur en entrée
2. Vérifie qu'elle respecte certaines règles
3. Lève une ValidationError si la règle est violée
4. Ne retourne rien si la valeur est valide

Utilisation dans un modèle :
    class Device(BaseModel):
        ip_address = models.CharField(validators=[validate_ip_address])

Utilisation dans un serializer :
    class CableSerializer(serializers.ModelSerializer):
        section = serializers.FloatField(validators=[validate_cable_section])
"""

import re
import ipaddress
from django.core.exceptions import ValidationError


# ============================================================
# VALIDATEURS GÉNÉRIQUES
# ============================================================

def validate_no_special_chars(value):
    """
    Vérifie qu'une chaîne ne contient pas de caractères spéciaux dangereux.
    Utile pour les noms et références.

    ✅ "Cable-EPR-001"
    ❌ "Cable<script>alert(1)</script>"
    """
    pattern = r'^[a-zA-Z0-9\s\-_\./éèêàùûîôç]+$'
    if not re.match(pattern, value):
        raise ValidationError(
            "Ce champ ne peut contenir que des lettres, chiffres, "
            "espaces et les caractères : - _ . /"
        )


def validate_positive_number(value):
    """
    Vérifie qu'un nombre est strictement positif.

    ✅ 10, 1.5, 0.01
    ❌ 0, -5, -0.01
    """
    if value <= 0:
        raise ValidationError(
            f"La valeur doit être strictement positive. Valeur reçue : {value}"
        )


def validate_percentage(value):
    """
    Vérifie qu'une valeur est un pourcentage valide (entre 0 et 100).

    ✅ 0, 50, 100, 99.9
    ❌ -1, 101, 150
    """
    if not (0 <= value <= 100):
        raise ValidationError(
            f"Le pourcentage doit être compris entre 0 et 100. Valeur reçue : {value}"
        )


# ============================================================
# VALIDATEURS RÉSEAU ET SÉCURITÉ
# ============================================================

def validate_ip_address(value):
    """
    Vérifie qu'une adresse IP est valide (IPv4 ou IPv6).

    ✅ "192.168.1.1", "10.0.0.1", "::1"
    ❌ "999.999.999.999", "not-an-ip"
    """
    try:
        ipaddress.ip_address(value)
    except ValueError:
        raise ValidationError(
            f"L'adresse IP '{value}' est invalide."
        )


def validate_ip_network(value):
    """
    Vérifie qu'une plage réseau CIDR est valide.

    ✅ "192.168.1.0/24", "10.0.0.0/8"
    ❌ "192.168.1.0/33", "not-a-network"
    """
    try:
        ipaddress.ip_network(value, strict=False)
    except ValueError:
        raise ValidationError(
            f"La plage réseau '{value}' est invalide. Format attendu : 192.168.1.0/24"
        )


def validate_mac_address(value):
    """
    Vérifie qu'une adresse MAC est valide.

    ✅ "00:1A:2B:3C:4D:5E", "00-1A-2B-3C-4D-5E"
    ❌ "00:1A:2B:3C:4D", "not-a-mac"
    """
    pattern = r'^([0-9A-Fa-f]{2}[:\-]){5}([0-9A-Fa-f]{2})$'
    if not re.match(pattern, value):
        raise ValidationError(
            f"L'adresse MAC '{value}' est invalide. "
            "Format attendu : 00:1A:2B:3C:4D:5E"
        )


def validate_port_number(value):
    """
    Vérifie qu'un numéro de port réseau est valide (1-65535).

    ✅ 80, 443, 8000, 65535
    ❌ 0, 65536, -1
    """
    if not (1 <= value <= 65535):
        raise ValidationError(
            f"Le numéro de port doit être compris entre 1 et 65535. "
            f"Valeur reçue : {value}"
        )


# ============================================================
# VALIDATEURS MÉTIER ÉLECTRICITÉ
# ============================================================

def validate_cable_section(value):
    """
    Vérifie que la section d'un câble est une valeur standard (en mm²).

    Sections standard selon la norme IEC :
    1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240 mm²

    ✅ 1.5, 2.5, 16.0
    ❌ 3.0, 7.5, 13.0
    """
    standard_sections = [
        1.5, 2.5, 4.0, 6.0, 10.0, 16.0, 25.0, 35.0,
        50.0, 70.0, 95.0, 120.0, 150.0, 185.0, 240.0
    ]
    if value not in standard_sections:
        sections_str = ', '.join([str(s) for s in standard_sections])
        raise ValidationError(
            f"La section {value} mm² n'est pas une valeur standard. "
            f"Valeurs acceptées : {sections_str}"
        )


def validate_voltage(value):
    """
    Vérifie qu'une tension électrique est une valeur positive et raisonnable.
    Plage acceptée : 1V à 400 000V (400kV).

    ✅ 230, 400, 20000
    ❌ 0, -230, 500000
    """
    if not (1 <= value <= 400_000):
        raise ValidationError(
            f"La tension {value}V est hors limites. "
            "Plage acceptée : 1V à 400 000V."
        )


def validate_power_watts(value):
    """
    Vérifie qu'une puissance électrique est valide (en Watts).
    Plage acceptée : 0W à 10 000 000W (10MW).

    ✅ 1000, 50000
    ❌ -500, 99999999
    """
    if not (0 <= value <= 10_000_000):
        raise ValidationError(
            f"La puissance {value}W est hors limites. "
            "Plage acceptée : 0W à 10 000 000W."
        )


def validate_cable_length(value):
    """
    Vérifie qu'une longueur de câble est valide (en mètres).
    Plage acceptée : 0.1m à 50 000m (50km).

    ✅ 1.5, 100, 1000
    ❌ 0, -10, 100000
    """
    if not (0.1 <= value <= 50_000):
        raise ValidationError(
            f"La longueur {value}m est hors limites. "
            "Plage acceptée : 0.1m à 50 000m."
        )


def validate_electrical_reference(value):
    """
    Vérifie qu'une référence électrique respecte le format standard.
    Format : 2-3 lettres majuscules + tiret + chiffres + optionnel suffixe.

    ✅ "CAB-001", "EPR-12345", "HPC-0042-A"
    ❌ "cab001", "TOOLONG-001", "123-ABC"
    """
    pattern = r'^[A-Z]{2,5}-\d{2,6}(-[A-Z0-9]+)?$'
    if not re.match(pattern, value):
        raise ValidationError(
            f"La référence '{value}' ne respecte pas le format standard. "
            "Format attendu : XX-0000 (ex: CAB-001, EPR-12345)"
        )


# ============================================================
# VALIDATEURS FICHIERS
# ============================================================

def validate_file_size(max_mb=10):
    """
    Fabrique de validateur : retourne un validateur qui limite la taille du fichier.

    Utilisation :
        document = models.FileField(validators=[validate_file_size(max_mb=5)])

    ✅ Fichier de 3 MB avec max_mb=5
    ❌ Fichier de 8 MB avec max_mb=5
    """
    def validator(value):
        max_bytes = max_mb * 1024 * 1024
        if value.size > max_bytes:
            raise ValidationError(
                f"Fichier trop volumineux ({value.size / 1024 / 1024:.1f} MB). "
                f"Taille maximale : {max_mb} MB."
            )
    return validator


def validate_file_extension(allowed_extensions):
    """
    Fabrique de validateur : limite les extensions de fichiers autorisées.

    Utilisation :
        document = models.FileField(
            validators=[validate_file_extension(['.pdf', '.docx'])]
        )

    ✅ "rapport.pdf" avec extensions=['.pdf']
    ❌ "script.exe" avec extensions=['.pdf']
    """
    def validator(value):
        import os
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in allowed_extensions:
            exts_str = ', '.join(allowed_extensions)
            raise ValidationError(
                f"Extension '{ext}' non autorisée. "
                f"Extensions acceptées : {exts_str}"
            )
    return validator


# ============================================================
# VALIDATEURS COORDONNÉES (pour schémas électriques)
# ============================================================

def validate_coordinate_x(value):
    """
    Vérifie qu'une coordonnée X est dans les limites d'un schéma.
    Plage : -100 000 à 100 000
    """
    if not (-100_000 <= value <= 100_000):
        raise ValidationError(
            f"Coordonnée X {value} hors limites (-100000 à 100000)."
        )


def validate_coordinate_y(value):
    """
    Vérifie qu'une coordonnée Y est dans les limites d'un schéma.
    Plage : -100 000 à 100 000
    """
    if not (-100_000 <= value <= 100_000):
        raise ValidationError(
            f"Coordonnée Y {value} hors limites (-100000 à 100000)."
        )