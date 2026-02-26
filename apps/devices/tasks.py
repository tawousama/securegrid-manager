"""
Tâches Celery périodiques pour l'app devices.

Ces tâches sont planifiées via config/celery.py :
- check_offline_devices_task  → toutes les 5 minutes
- check_unscanned_devices_task → toutes les 10 minutes
- run_nightly_security_scan   → toutes les nuits à 2h
"""

import logging
from celery import shared_task

logger = logging.getLogger('electrosecure')


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def check_offline_devices_task(self, timeout_minutes: int = 10):
    """
    Vérifie les équipements qui n'ont pas répondu depuis X minutes.
    Déclenche des alertes pour les équipements critiques hors ligne.

    Planification : toutes les 5 minutes (voir config/celery.py)
    """
    from apps.devices.services.alert_service import AlertService
    try:
        offline = AlertService.check_offline_devices(timeout_minutes=timeout_minutes)
        logger.info(
            "[TASK] check_offline_devices : %d équipement(s) marqué(s) offline",
            len(offline)
        )
        return {'offline_count': len(offline)}
    except Exception as exc:
        logger.error("[TASK] check_offline_devices ERREUR : %s", exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2)
def check_unscanned_devices_task(self, days: int = 7):
    """
    Identifie les équipements non scannés depuis X jours.
    Lance automatiquement un scan ping sur chacun.

    Planification : toutes les 10 minutes (voir config/celery.py)
    """
    from apps.devices.services.alert_service import AlertService
    from apps.devices.services.scan_service import ScanService

    try:
        stale = AlertService.check_unscanned_devices(days=days)
        scan_service = ScanService()

        for device in stale[:10]:  # Max 10 scans par exécution
            scan_service.run_ping_scan(device)

        logger.info(
            "[TASK] check_unscanned_devices : %d équipement(s) traité(s)",
            min(len(stale), 10)
        )
        return {'scanned_count': min(len(stale), 10)}
    except Exception as exc:
        logger.error("[TASK] check_unscanned_devices ERREUR : %s", exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=1)
def run_nightly_security_scan(self):
    """
    Scan de sécurité complet sur tous les équipements supervisés.
    Ports + vulnérabilités CVE.

    Planification : toutes les nuits à 2h00 (voir config/celery.py)
    """
    from apps.devices.models import Device
    from apps.devices.services.scan_service import ScanService

    try:
        devices = Device.objects.filter(
            is_monitored=True,
            is_active=True,
            is_deleted=False,
        )
        scan_service = ScanService()
        scanned = 0

        for device in devices:
            try:
                scan_service.run_full_scan(device)
                scanned += 1
            except Exception as e:
                logger.warning(
                    "[TASK] Scan échoué pour %s : %s",
                    device.reference, e
                )

        logger.info(
            "[TASK] run_nightly_security_scan : %d/%d équipements scannés",
            scanned, devices.count()
        )
        return {'total': devices.count(), 'scanned': scanned}

    except Exception as exc:
        logger.error("[TASK] run_nightly_security_scan ERREUR : %s", exc)
        raise self.retry(exc=exc)