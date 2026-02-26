"""
Configuration Django — Environnement de développement local.

Usage :
    export DJANGO_SETTINGS_MODULE=config.settings.development
    python manage.py runserver
"""

from .base import *

# ── Dev ───────────────────────────────────────────────────────
DEBUG         = True
ALLOWED_HOSTS = ['*']

# ── Base de données : SQLite (aucune config requise) ──────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'electrosecure_dev'),
        'USER': os.environ.get('DB_USER', 'electrosecure'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'electrosecure123'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}
# ── CORS : tout autoriser en dev ──────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True

# ── Email : affichage en console ──────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ── Sécurité : désactivée en dev ──────────────────────────────
SECURE_SSL_REDIRECT    = False
SESSION_COOKIE_SECURE  = False
CSRF_COOKIE_SECURE     = False

# ── JWT : tokens longs pour le confort du dev ─────────────────
from datetime import timedelta
SIMPLE_JWT = {
    **SIMPLE_JWT,
    'ACCESS_TOKEN_LIFETIME' : timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

# ── Logs : verbeux en dev ─────────────────────────────────────
LOGGING['root']['level'] = 'DEBUG'
LOGGING['loggers']['django']['level'] = 'INFO'
LOGGING['loggers']['electrosecure']['level'] = 'DEBUG'

# ── Django REST Framework : browsable API activée en dev ──────
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',  # Interface web DRF
    ],
}

# ── Celery : exécution synchrone en dev (pas besoin de Redis) ─
# Toutes les tâches Celery s'exécutent directement sans worker
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True