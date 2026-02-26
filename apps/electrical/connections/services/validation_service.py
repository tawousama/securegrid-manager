"""
Service de validation des raccordements électriques.

Ce service est le garde-fou de sécurité.
Il vérifie qu'un raccordement respecte les normes électriques
AVANT qu'il soit créé ou validé.

Normes appliquées :
- IEC 60446 : Identification des conducteurs par couleurs
- IEC 60947 : Appareillage de connexion
- NF C 15-100 : Installations électriques basse tension (France)
"""

from core.exceptions import ElectricalComplianceError, ConnectionIncompatibleError


class ConnectionValidationService:
    """
    Valide la conformité électrique d'un raccordement.

    Usage :
        validator = ConnectionValidationService()
        errors    = validator.validate_full(connection)
        if errors:
            raise ConnectionIncompatibleError(errors[0])
    """

    # --------------------------------------------------------
    # VALIDATION COMPLÈTE
    # --------------------------------------------------------

    def validate_full(self, connection) -> list:
        """
        Lance toutes les validations sur un raccordement.

        Returns:
            list[str] : Liste des erreurs trouvées (vide = conforme)
        """
        errors = []

        errors += self.validate_section_compatibility(connection)
        errors += self.validate_voltage_compatibility(connection)
        errors += self.validate_no_duplicate_connection(connection)
        errors += self.validate_connection_points(connection)

        return errors

    # --------------------------------------------------------
    # VALIDATION SECTION
    # --------------------------------------------------------

    def validate_section_compatibility(self, connection) -> list:
        """
        Vérifie que la section du câble est compatible avec les bornes.

        Règle : section_câble ≤ section_max_borne

        ✅ Câble 2.5mm² → Borne max 6mm²    → OK
        ❌ Câble 10mm²  → Borne max 6mm²    → ERREUR
        """
        errors = []
        cable_section = connection.cable.cable_type.section_mm2

        if cable_section > connection.terminal_origin.max_section_mm2:
            errors.append(
                f"Section du câble ({cable_section}mm²) incompatible avec "
                f"la borne origine {connection.terminal_origin} "
                f"(max {connection.terminal_origin.max_section_mm2}mm²)."
            )

        if cable_section > connection.terminal_dest.max_section_mm2:
            errors.append(
                f"Section du câble ({cable_section}mm²) incompatible avec "
                f"la borne destination {connection.terminal_dest} "
                f"(max {connection.terminal_dest.max_section_mm2}mm²)."
            )

        return errors

    # --------------------------------------------------------
    # VALIDATION TENSION
    # --------------------------------------------------------

    def validate_voltage_compatibility(self, connection) -> list:
        """
        Vérifie que la tension du câble est compatible avec les bornes.

        Règle : tension_câble ≤ tension_nominale_borne

        ✅ Câble 230V → Borne 400V    → OK (marge de sécurité)
        ❌ Câble 1000V → Borne 400V   → DANGER — ERREUR
        """
        errors = []

        cable_voltage = getattr(connection.cable, 'operating_voltage', None)
        if cable_voltage is None:
            return errors  # Pas de tension renseignée → skip

        if cable_voltage > connection.terminal_origin.voltage_rating:
            errors.append(
                f"Tension du câble ({cable_voltage}V) dépasse le rating de "
                f"la borne origine {connection.terminal_origin} "
                f"({connection.terminal_origin.voltage_rating}V). "
                "RISQUE ÉLECTRIQUE."
            )

        if cable_voltage > connection.terminal_dest.voltage_rating:
            errors.append(
                f"Tension du câble ({cable_voltage}V) dépasse le rating de "
                f"la borne destination {connection.terminal_dest} "
                f"({connection.terminal_dest.voltage_rating}V). "
                "RISQUE ÉLECTRIQUE."
            )

        return errors

    # --------------------------------------------------------
    # VALIDATION UNICITÉ
    # --------------------------------------------------------

    def validate_no_duplicate_connection(self, connection) -> list:
        """
        Vérifie qu'une borne n'est pas déjà raccordée.

        Un terminal ne peut accueillir qu'un seul conducteur à la fois
        (sauf borniers doubles ou spéciaux).
        """
        from ..models import Connection

        errors = []

        existing_origin = Connection.objects.filter(
            terminal_origin=connection.terminal_origin,
            is_active=True
        ).exclude(id=connection.id).first()

        if existing_origin:
            errors.append(
                f"La borne d'origine {connection.terminal_origin} est déjà "
                f"utilisée par le raccordement {existing_origin.reference}."
            )

        existing_dest = Connection.objects.filter(
            terminal_dest=connection.terminal_dest,
            is_active=True
        ).exclude(id=connection.id).first()

        if existing_dest:
            errors.append(
                f"La borne de destination {connection.terminal_dest} est déjà "
                f"utilisée par le raccordement {existing_dest.reference}."
            )

        return errors

    # --------------------------------------------------------
    # VALIDATION DES POINTS DE RACCORDEMENT
    # --------------------------------------------------------

    def validate_connection_points(self, connection) -> list:
        """
        Vérifie que tous les conducteurs respectent les conventions
        de couleur IEC 60446.

        L1 → Marron, L2 → Noir, L3 → Gris, N → Bleu, PE → Vert/Jaune
        """
        errors = []

        for point in connection.connection_points.all():
            if not point.follows_color_convention:
                expected_color = point.STANDARD_COLORS.get(point.conductor)
                errors.append(
                    f"Conducteur {point.conductor} : couleur '{point.wire_color}' "
                    f"non conforme IEC 60446 (attendu : '{expected_color}'). "
                    "Risque d'erreur de câblage."
                )

        return errors

    # --------------------------------------------------------
    # VALIDATION COUPLE DE SERRAGE
    # --------------------------------------------------------

    def validate_tightening_torques(self, connection) -> list:
        """
        Vérifie que le couple de serrage renseigné est dans les limites
        recommandées par le fabricant de la borne.
        """
        errors = []

        for point in connection.connection_points.all():
            if point.tightening_torque_nm is None:
                continue

            terminal      = point.terminal
            max_torque    = terminal.recommended_torque_nm
            if max_torque is None:
                continue

            tolerance     = 0.2  # ±20% de tolérance
            min_acceptable = max_torque * (1 - tolerance)
            max_acceptable = max_torque * (1 + tolerance)

            if not (min_acceptable <= point.tightening_torque_nm <= max_acceptable):
                errors.append(
                    f"Couple de serrage {point.tightening_torque_nm}N·m hors plage "
                    f"pour {point.conductor} sur {terminal} "
                    f"(recommandé : {max_torque}N·m ±20%)."
                )

        return errors