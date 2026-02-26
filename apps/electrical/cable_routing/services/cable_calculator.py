"""
Calculateur électrique pour les câbles — Conformité normes IEC.

Ce service effectue tous les calculs électriques liés aux câbles :
- Chute de tension (voltage drop) → Norme IEC 60364-5-52
- Vérification de la section (courant admissible)
- Résistance et pertes en ligne
- Courant de court-circuit admissible

Formules utilisées :

    Chute de tension (monophasé) :
        ΔU = (2 × ρ × L × I) / S
        Où :
            ρ = résistivité du conducteur (Ω·mm²/m)
            L = longueur du câble (m)
            I = courant (A)
            S = section (mm²)

    Chute de tension en % :
        ΔU% = (ΔU / U) × 100

    Résistance du câble :
        R = (2 × ρ × L) / S    (aller-retour)

    Pertes en puissance :
        P_pertes = R × I²

Seuils normatifs IEC 60364 :
    - Chute de tension max circuits terminaux : 3%
    - Chute de tension max totale installation : 5%
"""


class CableCalculator:
    """
    Effectue les calculs électriques sur un câble.

    Usage :
        calc   = CableCalculator()
        result = calc.check_cable_sizing(
            current_a=32,
            length_m=150,
            section_mm2=6.0,
            voltage_v=230,
            conductor='copper'
        )
    """

    # Résistivités à 20°C (en Ω·mm²/m)
    RESISTIVITY = {
        'copper'   : 0.01786,   # Cuivre (le plus utilisé)
        'aluminum' : 0.02941,   # Aluminium (lignes haute tension)
    }

    # Courant admissible par section — méthode B1, 3 conducteurs, cuivre (IEC 60364)
    # {section_mm2: current_A}
    CURRENT_CAPACITY_COPPER_B1 = {
        1.5  : 13.5,
        2.5  : 18.0,
        4.0  : 24.0,
        6.0  : 31.0,
        10.0 : 42.0,
        16.0 : 56.0,
        25.0 : 73.0,
        35.0 : 89.0,
        50.0 : 108.0,
        70.0 : 136.0,
        95.0 : 164.0,
        120.0: 188.0,
        150.0: 216.0,
        185.0: 245.0,
        240.0: 286.0,
    }

    # Seuils normatifs IEC (en %)
    MAX_VOLTAGE_DROP_TERMINAL  = 3.0  # Circuits terminaux
    MAX_VOLTAGE_DROP_TOTAL     = 5.0  # Installation complète

    # --------------------------------------------------------
    # MÉTHODE PRINCIPALE : VÉRIFICATION COMPLÈTE
    # --------------------------------------------------------

    def check_cable_sizing(
        self,
        current_a   : float,
        length_m    : float,
        section_mm2 : float,
        voltage_v   : float,
        conductor   : str = 'copper',
        circuit_type: str = 'terminal'
    ) -> dict:
        """
        Vérification complète du dimensionnement d'un câble.
        Retourne tous les calculs et la conformité IEC.

        Args:
            current_a    : Courant de service en Ampères
            length_m     : Longueur du câble en mètres
            section_mm2  : Section du câble en mm²
            voltage_v    : Tension de service en Volts
            conductor    : 'copper' ou 'aluminum'
            circuit_type : 'terminal' (3%) ou 'distribution' (5%)

        Returns:
            dict : {
                'voltage_drop_v'        : float,   # Chute de tension en Volts
                'voltage_drop_percent'  : float,   # Chute de tension en %
                'max_allowed_percent'   : float,   # Seuil IEC
                'is_voltage_drop_ok'    : bool,    # Conformité chute de tension
                'current_capacity_a'    : float,   # Courant admissible de la section
                'is_current_capacity_ok': bool,    # Conformité courant
                'resistance_ohm'        : float,   # Résistance aller-retour
                'power_loss_w'          : float,   # Pertes en Watts
                'is_compliant'          : bool,    # Conformité globale IEC
                'recommendations'       : list,    # Suggestions si non conforme
            }
        """
        # 1. Calcul de la chute de tension
        v_drop_v       = self.calculate_voltage_drop(current_a, length_m, section_mm2, conductor)
        v_drop_percent = (v_drop_v / voltage_v) * 100 if voltage_v > 0 else 0

        # 2. Seuil applicable
        max_percent = (
            self.MAX_VOLTAGE_DROP_TERMINAL
            if circuit_type == 'terminal'
            else self.MAX_VOLTAGE_DROP_TOTAL
        )

        # 3. Vérification courant admissible
        current_capacity   = self.get_current_capacity(section_mm2, conductor)
        is_current_ok      = current_a <= current_capacity

        # 4. Résistance et pertes
        resistance = self.calculate_resistance(length_m, section_mm2, conductor)
        power_loss = resistance * (current_a ** 2)

        # 5. Conformité globale
        is_voltage_ok = v_drop_percent <= max_percent
        is_compliant  = is_voltage_ok and is_current_ok

        # 6. Recommandations si non conforme
        recommendations = []
        if not is_current_ok:
            recommended = self._recommend_section_for_current(current_a)
            recommendations.append(
                f"Section insuffisante pour {current_a}A. "
                f"Section minimale recommandée : {recommended} mm²"
            )
        if not is_voltage_ok:
            recommended = self._recommend_section_for_voltage_drop(
                current_a, length_m, voltage_v, max_percent, conductor
            )
            recommendations.append(
                f"Chute de tension de {v_drop_percent:.1f}% dépasse le seuil IEC de {max_percent}%. "
                f"Section recommandée : {recommended} mm²"
            )

        return {
            'voltage_drop_v'        : round(v_drop_v, 3),
            'voltage_drop_percent'  : round(v_drop_percent, 2),
            'max_allowed_percent'   : max_percent,
            'is_voltage_drop_ok'    : is_voltage_ok,
            'current_capacity_a'    : current_capacity,
            'is_current_capacity_ok': is_current_ok,
            'resistance_ohm'        : round(resistance, 4),
            'power_loss_w'          : round(power_loss, 2),
            'is_compliant'          : is_compliant,
            'recommendations'       : recommendations,
        }

    # --------------------------------------------------------
    # CALCULS INDIVIDUELS
    # --------------------------------------------------------

    def calculate_voltage_drop(
        self,
        current_a   : float,
        length_m    : float,
        section_mm2 : float,
        conductor   : str = 'copper'
    ) -> float:
        """
        Calcule la chute de tension (aller-retour) en Volts.

        Formule : ΔU = (2 × ρ × L × I) / S

        Returns:
            float : Chute de tension en Volts
        """
        rho = self.RESISTIVITY.get(conductor, self.RESISTIVITY['copper'])
        return (2 * rho * length_m * current_a) / section_mm2

    def calculate_resistance(
        self,
        length_m    : float,
        section_mm2 : float,
        conductor   : str = 'copper'
    ) -> float:
        """
        Calcule la résistance aller-retour du câble en Ohms.

        Formule : R = (2 × ρ × L) / S

        Returns:
            float : Résistance en Ohms
        """
        rho = self.RESISTIVITY.get(conductor, self.RESISTIVITY['copper'])
        return (2 * rho * length_m) / section_mm2

    def get_current_capacity(
        self,
        section_mm2 : float,
        conductor   : str = 'copper'
    ) -> float:
        """
        Retourne le courant admissible pour une section donnée.
        Méthode B1, 3 conducteurs, selon IEC 60364-5-52.

        Returns:
            float : Courant admissible en Ampères. 0 si section inconnue.
        """
        if conductor == 'copper':
            return self.CURRENT_CAPACITY_COPPER_B1.get(section_mm2, 0.0)
        # Aluminium : environ 78% de la capacité cuivre
        copper_capacity = self.CURRENT_CAPACITY_COPPER_B1.get(section_mm2, 0.0)
        return round(copper_capacity * 0.78, 1)

    # --------------------------------------------------------
    # RECOMMANDATIONS
    # --------------------------------------------------------

    def _recommend_section_for_current(self, current_a: float) -> float:
        """
        Trouve la section minimale pour supporter un courant donné.

        Returns:
            float : Section recommandée en mm²
        """
        for section, capacity in sorted(self.CURRENT_CAPACITY_COPPER_B1.items()):
            if capacity >= current_a:
                return section
        return 240.0  # Maximum disponible

    def _recommend_section_for_voltage_drop(
        self,
        current_a   : float,
        length_m    : float,
        voltage_v   : float,
        max_percent : float,
        conductor   : str
    ) -> float:
        """
        Trouve la section minimale pour respecter la chute de tension.

        On cherche S tel que : ΔU% = (2×ρ×L×I) / (S×U) × 100 ≤ max_percent

        Formule inversée : S ≥ (2×ρ×L×I×100) / (U×max_percent)

        Returns:
            float : Section recommandée en mm²
        """
        rho = self.RESISTIVITY.get(conductor, self.RESISTIVITY['copper'])
        min_section = (2 * rho * length_m * current_a * 100) / (voltage_v * max_percent)

        # Trouver la section standard supérieure
        for section in sorted(self.CURRENT_CAPACITY_COPPER_B1.keys()):
            if section >= min_section:
                return section
        return 240.0