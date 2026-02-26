"""
Configuration Celery — ElectroSecure Platform.

Celery gère les tâches asynchrones et périodiques :

Tâches périodiques (Celery Beat) :
    ┌─ Toutes les 5 min ──── check_offline_devices()   → ping + alerte
    ├─ Toutes les nuits 2h ─ run_security_scans()      → scan CVE complet
    ├─ Toutes les heures ─── cleanup_expired_tokens()  → purge JWT blacklist
    └─ Toutes les 10 min ─── check_unscanned_devices() → équipements sans scan

Démarrage :
    # Worker (traite les tâches)
    celery -A config worker -l info

    # Beat (planificateur de tâches périodiques)
    celery -A config beat -l info

    # Les deux ensemble (dev seulement)
    celery -A config worker --beat -l info
"""

import os
from celery import Celery
from celery.schedules import crontab

# Django settings par défaut
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('electrosecure')

# Charge la config depuis django.conf.settings (préfixe CELERY_)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Découverte automatique des tâches dans chaque app
app.autodiscover_tasks()


# ── Tâches périodiques ────────────────────────────────────────
app.conf.beat_schedule = {

    # ── Supervision des équipements ───────────────────────────
    # Toutes les 5 minutes : vérifie quels équipements sont hors ligne
    'check-offline-devices': {
        'task'    : 'apps.devices.tasks.check_offline_devices_task',
        'schedule': crontab(minute='*/5'),
        'kwargs'  : {'timeout_minutes': 10},
    },

    # Toutes les 10 minutes : identifie les équipements jamais scannés
    'check-unscanned-devices': {
        'task'    : 'apps.devices.tasks.check_unscanned_devices_task',
        'schedule': crontab(minute='*/10'),
        'kwargs'  : {'days': 7},
    },

    # Toutes les nuits à 2h00 : scan de sécurité complet
    'nightly-security-scan': {
        'task'    : 'apps.devices.tasks.run_nightly_security_scan',
        'schedule': crontab(hour=2, minute=0),
    },

    # ── Maintenance ───────────────────────────────────────────
    # Toutes les heures : purge les tokens JWT expirés (blacklist)
    'cleanup-expired-tokens': {
        'task'    : 'apps.authentication.tasks.cleanup_expired_tokens_task',
        'schedule': crontab(minute=0),  # à chaque heure pile
    },

}


# ── Tâche de test ─────────────────────────────────────────────
@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Tâche de test Celery. Lance avec : celery -A config call config.celery.debug_task"""
    print(f'[DEBUG TASK] Request: {self.request!r}')