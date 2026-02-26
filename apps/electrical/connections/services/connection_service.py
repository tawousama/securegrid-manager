"""
Service de gestion des raccordements électriques.

Orchestre la création, modification et validation des raccordements.
Fait appel au ValidationService pour les vérifications de conformité.
"""

from django.utils import timezone
from django.db import transaction

from core.exceptions import BusinessLogicError, ElectricalComplianceError

from ..models import Connection, ConnectionPoint, Terminal
from .validation_service import ConnectionValidationService


class ConnectionService:
    """
    Service métier pour les raccordements.

    Usage :
        service = ConnectionService()
        conn    = service.create_connection(data, user=request.user)
        service.mark_completed(conn, user=request.user)
        service.verify_connection(conn, user=request.user)
    """

    def __init__(self):
        self.validator = ConnectionValidationService()

    # --------------------------------------------------------
    # CRÉATION
    # --------------------------------------------------------

    @transaction.atomic
    def create_connection(self, validated_data: dict, user) -> Connection:
        """
        Crée un raccordement après validation des compatibilités.

        @transaction.atomic garantit que si une erreur survient,
        RIEN n'est enregistré en base de données (tout ou rien).

        Args:
            validated_data : Données validées par ConnectionCreateSerializer
            user           : Utilisateur qui crée le raccordement

        Returns:
            Connection : Le raccordement créé
        """
        # Créer le raccordement
        connection = Connection.objects.create(
            **validated_data,
            created_by=user,
        )

        # Vérifications de compatibilité (section, tension, unicité)
        errors = self.validator.validate_section_compatibility(connection)
        errors += self.validator.validate_voltage_compatibility(connection)

        if errors:
            # Rollback automatique grâce à @transaction.atomic
            raise ElectricalComplianceError(
                f"Raccordement non conforme : {'; '.join(errors)}"
            )

        return connection

    # --------------------------------------------------------
    # AJOUT DE POINTS DE RACCORDEMENT
    # --------------------------------------------------------

    def add_connection_point(
        self,
        connection: Connection,
        conductor: str,
        terminal: Terminal,
        wire_color: str,
        tightening_torque_nm: float = None,
        has_ferrule: bool = True,
    ) -> ConnectionPoint:
        """
        Ajoute un point de raccordement (un conducteur sur une borne).

        Vérifie la convention de couleur IEC 60446 et marque la borne
        comme occupée.

        Args:
            connection           : Le raccordement parent
            conductor            : Code du conducteur (L1, L2, N, PE...)
            terminal             : La borne physique
            wire_color           : Couleur du fil
            tightening_torque_nm : Couple de serrage en N·m
            has_ferrule          : Embout de câblage posé ou non

        Returns:
            ConnectionPoint : Le point créé
        """
        # Vérifier unicité (un conducteur par raccordement)
        if connection.connection_points.filter(conductor=conductor).exists():
            raise BusinessLogicError(
                f"Le conducteur {conductor} est déjà raccordé sur cette connexion."
            )

        # Vérifier que la borne appartient au raccordement
        valid_terminals = [connection.terminal_origin, connection.terminal_dest]
        if terminal not in valid_terminals:
            raise BusinessLogicError(
                f"La borne {terminal} n'appartient pas à ce raccordement."
            )

        # Créer le point
        point = ConnectionPoint.objects.create(
            connection           = connection,
            terminal             = terminal,
            conductor            = conductor,
            wire_color           = wire_color,
            tightening_torque_nm = tightening_torque_nm,
            has_ferrule          = has_ferrule,
        )

        # Marquer la borne comme occupée
        terminal.is_occupied = True
        terminal.save(update_fields=['is_occupied'])

        return point

    # --------------------------------------------------------
    # CYCLE DE VIE
    # --------------------------------------------------------

    def mark_completed(self, connection: Connection, user) -> Connection:
        """
        Marque un raccordement comme réalisé.
        Vérifie que tous les conducteurs sont raccordés.
        """
        if connection.status != Connection.STATUS_IN_PROGRESS:
            if connection.status == Connection.STATUS_PLANNED:
                # Passage automatique de PLANNED à IN_PROGRESS à COMPLETED
                connection.status = Connection.STATUS_IN_PROGRESS
            else:
                raise BusinessLogicError(
                    f"Impossible de compléter un raccordement avec le statut '{connection.status}'."
                )

        # Vérifier qu'il y a au moins un point de raccordement
        if not connection.connection_points.exists():
            raise BusinessLogicError(
                "Impossible de marquer comme réalisé : aucun point de raccordement renseigné."
            )

        connection.status       = Connection.STATUS_COMPLETED
        connection.completed_at = timezone.now()
        connection.updated_by   = user
        connection.save(update_fields=['status', 'completed_at', 'updated_by'])

        return connection

    def verify_connection(self, connection: Connection, user) -> Connection:
        """
        Vérifie et valide un raccordement terminé.

        Lance toutes les validations de conformité électrique.
        Nécessite le rôle Ingénieur (vérifié dans la vue).

        Returns:
            Connection : Raccordement vérifié et conforme
        """
        if connection.status != Connection.STATUS_COMPLETED:
            raise BusinessLogicError(
                "Seul un raccordement réalisé peut être vérifié."
            )

        # Lancer toutes les validations
        errors = self.validator.validate_full(connection)

        if errors:
            # Marquer comme défectueux
            connection.status = Connection.STATUS_FAULTY
            connection.fault_description = '\n'.join(errors)
            connection.save(update_fields=['status', 'fault_description'])

            raise ElectricalComplianceError(
                f"Raccordement non conforme : {'; '.join(errors)}"
            )

        # Marquer comme vérifié
        connection.status      = Connection.STATUS_VERIFIED
        connection.verified_at = timezone.now()
        connection.verified_by = user
        connection.save(update_fields=['status', 'verified_at', 'verified_by'])

        # Marquer tous les points comme vérifiés
        connection.connection_points.all().update(is_verified=True)

        return connection

    def mark_faulty(self, connection: Connection, description: str, user) -> Connection:
        """Signale un raccordement comme défectueux."""
        connection.status           = Connection.STATUS_FAULTY
        connection.fault_description = description
        connection.updated_by       = user
        connection.save(update_fields=['status', 'fault_description', 'updated_by'])
        return connection

    # --------------------------------------------------------
    # DIAGRAMME
    # --------------------------------------------------------

    def get_connection_diagram_data(self, connection: Connection) -> dict:
        """
        Génère les données structurées pour afficher le schéma
        de raccordement côté frontend.

        Returns:
            dict : Données du schéma avec conducteurs et bornes
        """
        points = connection.connection_points.select_related('terminal').all()

        return {
            'connection_ref'   : connection.reference,
            'cable_ref'        : connection.cable.reference,
            'cable_section'    : connection.cable.cable_type.section_mm2,
            'origin_terminal'  : str(connection.terminal_origin),
            'dest_terminal'    : str(connection.terminal_dest),
            'conductors'       : [
                {
                    'conductor'           : pt.conductor,
                    'color'               : pt.wire_color,
                    'terminal'            : str(pt.terminal),
                    'torque'              : pt.tightening_torque_nm,
                    'has_ferrule'         : pt.has_ferrule,
                    'color_ok'            : pt.follows_color_convention,
                    'verified'            : pt.is_verified,
                }
                for pt in points
            ],
            'status'           : connection.status,
            'is_compliant'     : connection.status == Connection.STATUS_VERIFIED,
        }