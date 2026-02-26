"""
Configuration Django — Environnement de production.

Usage :
    export DJANGO_SETTINGS_MODULE=config.settings.production
    export SECRET_KEY=<valeur-secrete>
    export DATABASE_URL=postgresql://user:pass@host/db
    export REDIS_URL=redis://host:6379/0
    gunicorn config.wsgi:application

Variables d'environnement OBLIGATOIRES en prod :
    SECRET_KEY, DATABASE_URL, REDIS_URL,
    ALLOWED_HOSTS_LIST (ex: "api.electrosecure.com,www.electrosecure.com")
"""

import os
from .base import *

# ── Sécurité ─────────────────────────────────────────────────
DEBUG = False

SECRET_KEY = os.environ['SECRET_KEY']  # Plantera si absent → intentionnel

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS_LIST', '').split(',')

# ── Base de données : PostgreSQL ──────────────────────────────
# Format DATABASE_URL : postgresql://user:password@host:5432/dbname

import dj_database_url  # pip install dj-database-url

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    raise ValueError(
        "❌ DATABASE_URL environment variable is required in production!\n"
        "Add PostgreSQL service on Railway:\n"
        "  Railway Dashboard → New → Database → Add PostgreSQL"
    )

DATABASES = {
    'default': dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600,        # Connexions persistantes (10 min)
        conn_health_checks=True, # Vérif de santé avant chaque requête
    )
}
# ── Cache : Redis ─────────────────────────────────────────────
CACHES = {
    'default': {
        'BACKEND' : 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://localhost:6379/1'),
    }
}

# ── Sessions : stockées en cache Redis ───────────────────────
SESSION_ENGINE         = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS    = 'default'
SESSION_COOKIE_AGE     = 3600  # 1 heure

# ── Sécurité HTTPS ────────────────────────────────────────────
SECURE_SSL_REDIRECT             = True
SECURE_HSTS_SECONDS             = 31536000  # 1 an
SECURE_HSTS_INCLUDE_SUBDOMAINS  = True
SECURE_HSTS_PRELOAD             = True
SECURE_CONTENT_TYPE_NOSNIFF     = True
SECURE_BROWSER_XSS_FILTER       = True
SESSION_COOKIE_SECURE           = True
CSRF_COOKIE_SECURE              = True
X_FRAME_OPTIONS                 = 'DENY'

# ── CORS : origines autorisées explicites ─────────────────────
CORS_ALLOWED_ORIGINS = os.environ.get(
    'CORS_ALLOWED_ORIGINS',
    'https://electrosecure.com'
).split(',')

# ── Email : SMTP réel ─────────────────────────────────────────
EMAIL_BACKEND  = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST     = os.environ.get('EMAIL_HOST', 'smtp.sendgrid.net')
EMAIL_PORT     = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS  = True
EMAIL_HOST_USER     = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

# ── Fichiers statiques : WhiteNoise pour servir depuis Gunicorn ─
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ── Logging : fichier + Sentry en prod ───────────────────────
LOGGING['handlers']['file'] = {
    'class'    : 'logging.handlers.RotatingFileHandler',
    'filename' : BASE_DIR / 'logs' / 'electrosecure.log',
    'maxBytes' : 10 * 1024 * 1024,  # 10 MB par fichier
    'backupCount': 5,
    'formatter': 'verbose',
}
LOGGING['root'] = {
    'handlers': ['console', 'file'],
    'level'   : 'WARNING',
}
LOGGING['loggers']['electrosecure']['handlers'] = ['console', 'file']

# Sentry (si DSN fourni)
SENTRY_DSN = os.environ.get('SENTRY_DSN', '')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=0.1,   # 10% des transactions
        send_default_pii=False,   # Pas de données personnelles
    )