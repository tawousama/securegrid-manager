"""
Configuration Django — Environnement de test.

Usage :
    python manage.py test --settings=config.settings.test
    pytest --ds=config.settings.test
"""

from .base import *

DEBUG = False

# Base de données en mémoire → ultra-rapide pour les tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME'  : ':memory:',  # En RAM, pas sur disque
    }
}

# Pas d'email en test
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Pas de CORS en test
CORS_ALLOW_ALL_ORIGINS = True

# Celery synchrone en test
CELERY_TASK_ALWAYS_EAGER     = True
CELERY_TASK_EAGER_PROPAGATES = True

# Logs silencieux pendant les tests
LOGGING['root']['level'] = 'CRITICAL'

# Hashage de mot de passe rapide (tests plus rapides)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]