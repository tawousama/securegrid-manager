"""
Fonctions utilitaires du projet ElectroSecure Platform.

Ce fichier contient des fonctions "helper" sans état (stateless) :
- Pas de modèles
- Pas d'effets de bord
- Entrée → Traitement → Sortie

Principe : Si vous vous surprenez à copier-coller une fonction
dans plusieurs fichiers, elle doit être ici.
"""

import math
import uuid
import random
import string
import hashlib
from datetime import datetime, timedelta
from typing import Optional


# ============================================================
# GÉNÉRATION D'IDENTIFIANTS
# ============================================================

def generate_unique_code(prefix: str = '', length: int = 8) -> str:
    """
    Génère un code unique alphanumérique.

    Args:
        prefix : Préfixe du code (ex: 'CAB-', 'DEV-')
        length : Longueur de la partie aléatoire

    Returns:
        str : Code unique (ex: 'CAB-A7K2M9X1')

    Usage :
        code = generate_unique_code(prefix='CAB-', length=6)
        # → 'CAB-A7K2M9'
    """
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(random.choices(chars, k=length))
    return f"{prefix}{random_part}"


def generate_reference(category: str, sequence: int) -> str:
    """
    Génère une référence formatée pour les équipements électriques.

    Args:
        category : Catégorie (ex: 'CAB', 'CON', 'SCH')
        sequence : Numéro séquentiel

    Returns:
        str : Référence formatée (ex: 'CAB-00042')

    Usage :
        ref = generate_reference('CAB', 42)
        # → 'CAB-00042'
    """
    return f"{category.upper()}-{sequence:05d}"


# ============================================================
# CALCULS ÉLECTRIQUES
# ============================================================

def calculate_cable_length(point_a: dict, point_b: dict) -> float:
    """
    Calcule la distance euclidienne entre deux points 3D.
    Utile pour estimer la longueur d'un câble entre deux équipements.

    Args:
        point_a : Dictionnaire avec 'x', 'y', 'z' (en mètres)
        point_b : Dictionnaire avec 'x', 'y', 'z' (en mètres)

    Returns:
        float : Longueur en mètres (arrondie à 2 décimales)

    Usage :
        length = calculate_cable_length(
            {'x': 0, 'y': 0, 'z': 0},
            {'x': 10, 'y': 5, 'z': 3}
        )
        # → 11.58 mètres
    """
    dx = point_b['x'] - point_a['x']
    dy = point_b['y'] - point_a['y']
    dz = point_b.get('z', 0) - point_a.get('z', 0)
    return round(math.sqrt(dx**2 + dy**2 + dz**2), 2)


def calculate_voltage_drop(
    current_amps: float,
    length_meters: float,
    section_mm2: float,
    conductor: str = 'copper'
) -> float:
    """
    Calcule la chute de tension dans un câble.
    Formule : ΔU = (2 × ρ × L × I) / S

    Args:
        current_amps   : Courant en ampères
        length_meters  : Longueur du câble en mètres
        section_mm2    : Section du câble en mm²
        conductor      : 'copper' (cuivre) ou 'aluminum' (aluminium)

    Returns:
        float : Chute de tension en Volts

    Usage :
        drop = calculate_voltage_drop(
            current_amps=16,
            length_meters=50,
            section_mm2=2.5
        )
        # → 5.5 V (chute de tension sur 50m)
    """
    # Résistivité (en Ω·mm²/m)
    resistivity = {
        'copper': 0.01786,     # Cuivre
        'aluminum': 0.02941,   # Aluminium
    }
    rho = resistivity.get(conductor, 0.01786)

    voltage_drop = (2 * rho * length_meters * current_amps) / section_mm2
    return round(voltage_drop, 3)


def calculate_current_capacity(section_mm2: float, installation_method: str = 'B1') -> float:
    """
    Estime la capacité de courant d'un câble cuivre selon la section
    et la méthode d'installation (norme IEC 60364).

    Args:
        section_mm2       : Section du câble en mm²
        installation_method : 'A1', 'A2', 'B1', 'B2', 'C', 'E', 'F'

    Returns:
        float : Courant maximal en Ampères

    Usage :
        capacity = calculate_current_capacity(2.5, 'B1')
        # → 18.0 A
    """
    # Capacités indicatives pour câble cuivre (méthode B1, 3 conducteurs)
    capacity_table = {
        1.5:  13.5,
        2.5:  18.0,
        4.0:  24.0,
        6.0:  31.0,
        10.0: 42.0,
        16.0: 56.0,
        25.0: 73.0,
        35.0: 89.0,
        50.0: 108.0,
        70.0: 136.0,
        95.0: 164.0,
        120.0: 188.0,
        150.0: 216.0,
        185.0: 245.0,
        240.0: 286.0,
    }
    return capacity_table.get(section_mm2, 0.0)


def calculate_power(voltage: float, current: float, power_factor: float = 1.0) -> float:
    """
    Calcule la puissance électrique active.
    Formule monophasé : P = U × I × cos(φ)

    Args:
        voltage      : Tension en Volts
        current      : Courant en Ampères
        power_factor : Facteur de puissance (0 à 1, défaut = 1)

    Returns:
        float : Puissance en Watts

    Usage :
        power = calculate_power(230, 16, 0.85)
        # → 3128.0 W = 3.1 kW
    """
    return round(voltage * current * power_factor, 2)


# ============================================================
# FORMATAGE ET AFFICHAGE
# ============================================================

def format_file_size(size_bytes: int) -> str:
    """
    Convertit une taille en octets en format lisible.

    Args:
        size_bytes : Taille en octets

    Returns:
        str : Taille formatée

    Usage :
        format_file_size(1048576)   # → '1.0 MB'
        format_file_size(2500)      # → '2.4 KB'
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def format_duration(seconds: int) -> str:
    """
    Convertit une durée en secondes en format lisible.

    Args:
        seconds : Durée en secondes

    Returns:
        str : Durée formatée

    Usage :
        format_duration(3661)   # → '1h 01m 01s'
        format_duration(90)     # → '1m 30s'
    """
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    elif minutes:
        return f"{minutes}m {secs:02d}s"
    else:
        return f"{secs}s"


def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """
    Tronque un texte à une longueur maximale.

    Args:
        text       : Texte à tronquer
        max_length : Longueur maximale
        suffix     : Suffixe ajouté si tronqué

    Returns:
        str : Texte tronqué

    Usage :
        truncate_text("Un texte très long...", max_length=15)
        # → 'Un texte très l...'
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


# ============================================================
# SÉCURITÉ
# ============================================================

def mask_sensitive_data(value: str, visible_chars: int = 4) -> str:
    """
    Masque les données sensibles (mots de passe, tokens, etc.)

    Args:
        value         : Valeur à masquer
        visible_chars : Nombre de caractères visibles à la fin

    Returns:
        str : Valeur masquée

    Usage :
        mask_sensitive_data("password123")   # → '***********123'
        mask_sensitive_data("192.168.1.1")   # → '**********1.1'
    """
    if len(value) <= visible_chars:
        return '*' * len(value)
    masked = '*' * (len(value) - visible_chars)
    return masked + value[-visible_chars:]


def generate_secure_token(length: int = 32) -> str:
    """
    Génère un token sécurisé pour les liens de réinitialisation, etc.

    Args:
        length : Longueur du token en octets

    Returns:
        str : Token hexadécimal sécurisé

    Usage :
        token = generate_secure_token()
        # → 'a3f8c2e1d4b7...' (64 caractères hex)
    """
    import secrets
    return secrets.token_hex(length)