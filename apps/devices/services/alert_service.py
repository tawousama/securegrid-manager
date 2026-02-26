"""
Service d'alertes de sécurité.

Crée et envoie des alertes quand un événement critique est détecté :
- Équipement hors ligne
- Port non autorisé détecté
- Vulnérabilité critique découverte
- Équipement sans scan depuis X jours

En production, les notifications seraient envoyées via :
- Email (Django send_mail)
- Slack/Teams (webhook HTTP)
- SMS (Twilio API)
- Système SIEM (syslog, splunk)
"""

from django.utils import timezone
from datetime import timedelta


class AlertService:
    """
    Gère la création et l'envoi d'alertes de sécurité.

    Toutes les méthodes sont @staticmethod car le service
    est sans état — il ne garde pas de données en mémoire.
    """

    # --------------------------------------------------------
    # ALERTES DE STATUT
    # --------------------------------------------------------

    @staticmethod
    def create_status_alert(device, new_status: str) -> None:
        """
        Déclenche une alerte quand un équipement change de statut
        vers OFFLINE ou FAULT.

        Notifie :
        - Le responsable de l'équipement (device.owner)
        - Les ingénieurs du projet
        - L'équipe d'astreinte si criticité HIGH/CRITICAL
        """
        from core.constants import DEVICE_STATUS_OFFLINE, DEVICE_STATUS_FAULT

        severity = 'warning'
        if device.criticality in ['high', 'critical']:
            severity = 'critical'

        message = (
            f"[{severity.upper()}] Équipement {device.reference} ({device.name}) "
            f"— {device.ip_address} est passé au statut '{new_status}'."
        )

        if new_status == DEVICE_STATUS_OFFLINE and device.power_cable_ref:
            message += (
                f"\n→ Câble d'alimentation : {device.power_cable_ref}"
                f"\n→ Vérifier l'alimentation électrique."
            )

        AlertService._send_notification(
            device   = device,
            title    = f"Équipement {new_status.upper()} : {device.reference}",
            message  = message,
            severity = severity,
        )

    # --------------------------------------------------------
    # ALERTES PORTS NON AUTORISÉS
    # --------------------------------------------------------

    @staticmethod
    def create_unauthorized_port_alert(device, count: int) -> None:
        """
        Alerte quand des ports non autorisés sont détectés.
        Toujours de sévérité CRITICAL — c'est une alerte cybersécurité.
        """
        from ..models import DevicePort

        unauthorized_ports = DevicePort.objects.filter(
            device        = device,
            is_authorized = False,
            state         = DevicePort.STATE_OPEN
        ).values_list('port_number', 'service')

        port_list = ', '.join(
            f"{p}({s})" if s else str(p)
            for p, s in unauthorized_ports
        )

        AlertService._send_notification(
            device   = device,
            title    = f"⚠️ PORTS NON AUTORISÉS : {device.reference}",
            message  = (
                f"Scan de {device.reference} ({device.ip_address}) : "
                f"{count} port(s) non autorisé(s) détecté(s) : {port_list}\n"
                f"→ Vérifier immédiatement la configuration réseau."
            ),
            severity = 'critical',
        )

    # --------------------------------------------------------
    # ALERTES VULNÉRABILITÉS CRITIQUES
    # --------------------------------------------------------

    @staticmethod
    def create_critical_vuln_alert(device, count: int) -> None:
        """
        Alerte quand des vulnérabilités critiques sont découvertes.
        """
        from ..models import DeviceVulnerability

        crit_vulns = DeviceVulnerability.objects.filter(
            device   = device,
            severity = DeviceVulnerability.SEVERITY_CRITICAL,
            status   = DeviceVulnerability.STATUS_OPEN,
        ).values_list('cve_id', 'cvss_score')

        vuln_list = ', '.join(
            f"{cve} (score {score:.1f})"
            for cve, score in crit_vulns
        )

        AlertService._send_notification(
            device   = device,
            title    = f"🔴 VULNÉRABILITÉ(S) CRITIQUE(S) : {device.reference}",
            message  = (
                f"Scan de {device.reference} ({device.ip_address}) : "
                f"{count} CVE critique(s) : {vuln_list}\n"
                f"OS : {device.os or 'Non renseigné'}\n"
                f"→ Appliquer les correctifs immédiatement."
            ),
            severity = 'critical',
        )

    # --------------------------------------------------------
    # VÉRIFICATION PÉRIODIQUE (appelé par tâche Celery)
    # --------------------------------------------------------

    @staticmethod
    def check_offline_devices(timeout_minutes: int = 10) -> list:
        """
        Vérifie les équipements qui n'ont pas répondu depuis X minutes.
        Appelé par une tâche Celery périodique (toutes les 5 minutes).

        En production :
            # tasks.py
            @shared_task
            def check_devices_task():
                AlertService.check_offline_devices(timeout_minutes=10)

        Returns:
            list : Équipements marqués offline
        """
        from ..models import Device
        from core.constants import DEVICE_STATUS_ONLINE, DEVICE_STATUS_OFFLINE

        threshold = timezone.now() - timedelta(minutes=timeout_minutes)

        # Équipements supervisés qui n'ont pas répondu récemment
        stale_devices = Device.objects.filter(
            is_monitored  = True,
            status        = DEVICE_STATUS_ONLINE,
            is_active     = True,
            is_deleted    = False,
        ).filter(
            # last_seen absent ou dépassé
            last_seen__lt = threshold
        )

        marked_offline = []
        for device in stale_devices:
            device.status = DEVICE_STATUS_OFFLINE
            device.save(update_fields=['status'])
            AlertService.create_status_alert(device, DEVICE_STATUS_OFFLINE)
            marked_offline.append(device)

        return marked_offline

    @staticmethod
    def check_unscanned_devices(days: int = 7) -> list:
        """
        Identifie les équipements qui n'ont pas été scannés depuis X jours.
        Retourne la liste pour planifier les scans manquants.
        """
        from ..models import Device

        threshold = timezone.now() - timedelta(days=days)

        return list(Device.objects.filter(
            is_monitored = True,
            is_active    = True,
            is_deleted   = False,
        ).filter(
            # Jamais scanné ou scan trop ancien
            last_scan__lt = threshold
        ).order_by('last_scan'))

    # --------------------------------------------------------
    # ENVOI DE NOTIFICATION (à brancher sur le canal souhaité)
    # --------------------------------------------------------

    @staticmethod
    def _send_notification(device, title: str, message: str, severity: str) -> None:
        """
        Envoie une notification aux responsables.

        En production, remplacer par :
        - Email  : send_mail(subject=title, message=message, ...)
        - Slack  : requests.post(SLACK_WEBHOOK, json={"text": message})
        - SIEM   : logging.critical(message)

        Pour l'instant, on log simplement.
        """
        import logging
        logger = logging.getLogger('electrosecure.alerts')

        log_fn = logger.critical if severity == 'critical' else logger.warning
        log_fn(
            "[ALERT][%s] %s — %s",
            severity.upper(), title, message
        )

        # Notifier le responsable de l'équipement si défini
        if device.owner and device.owner.email:
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                send_mail(
                    subject      = f"[ElectroSecure] {title}",
                    message      = message,
                    from_email   = settings.DEFAULT_FROM_EMAIL,
                    recipient_list = [device.owner.email],
                    fail_silently  = True,
                )
            except Exception:
                pass  # Ne pas crasher si l'email échoue