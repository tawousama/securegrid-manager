"""Production settings"""
import os
from .base import *

DEBUG = False

# Secret Key (Railway l'injecte)
SECRET_KEY = os.environ.get('SECRET_KEY', 'changeme')

# Allowed Hosts
ALLOWED_HOSTS_STR = os.environ.get('ALLOWED_HOSTS', '*.railway.app')
ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS_STR.split(',')]

# Database (Railway l'injecte via DATABASE_URL)
import dj_database_url

DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    # Fallback pour éviter l'erreur
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
    print("⚠️  WARNING: DATABASE_URL not set, using SQLite fallback")


