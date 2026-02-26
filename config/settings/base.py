"""
Configuration Django de base — commune à tous les environnements.

Ne jamais utiliser ce fichier directement.
Utiliser development.py ou production.py qui l'importent.

Variables d'environnement requises :
    SECRET_KEY              → Clé secrète Django (obligatoire en prod)
    DATABASE_URL            → URL PostgreSQL (prod)
    REDIS_URL               → URL Redis pour Celery/cache
    MICROSOFT_CLIENT_ID     → OAuth2 Azure AD
    MICROSOFT_CLIENT_SECRET
    MICROSOFT_TENANT_ID
    GOOGLE_CLIENT_ID        → OAuth2 Google
    GOOGLE_CLIENT_SECRET
    DEFAULT_FROM_EMAIL      → Email d'expédition
"""

import os
from pathlib import Path
from datetime import timedelta

# ── Chemins ──────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ── Sécurité ─────────────────────────────────────────────────
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-insecure-key-changeme-in-production')
DEBUG      = False  # Surchargé dans development.py

ALLOWED_HOSTS = []  # Surchargé dans chaque environnement

# ── Applications ─────────────────────────────────────────────
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
]

LOCAL_APPS = [
    'core',
    'apps.authentication',
    'apps.electrical.cable_routing',
    'apps.electrical.connections',
    'apps.electrical.schematics',
    'apps.devices',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ── Modèle utilisateur ────────────────────────────────────────
AUTH_USER_MODEL = 'authentication.User'

# ── Middlewares ───────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF    = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ── Templates ─────────────────────────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS'   : [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ── Base de données (SQLite par défaut, override en prod) ─────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME'  : BASE_DIR / 'db.sqlite3',
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Validation des mots de passe ──────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 10}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internationalisation ──────────────────────────────────────
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE     = 'Europe/Paris'
USE_I18N      = True
USE_TZ        = True

# ── Fichiers statiques et médias ──────────────────────────────
STATIC_URL       = '/static/'
STATIC_ROOT      = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL        = '/media/'
MEDIA_ROOT       = BASE_DIR / 'media'

# ── Django REST Framework ─────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
}

# ── JWT ───────────────────────────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME'  : timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME' : timedelta(days=1),
    'ROTATE_REFRESH_TOKENS'  : True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM'              : 'HS256',
    'AUTH_HEADER_TYPES'      : ('Bearer',),
    'USER_ID_FIELD'          : 'id',
    'USER_ID_CLAIM'          : 'user_id',
}

# ── CORS ──────────────────────────────────────────────────────
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS   = []  # Surchargé dans chaque environnement
CORS_ALLOW_METHODS = ['DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT']
CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization',
    'content-type', 'dnt', 'origin',
    'user-agent', 'x-csrftoken', 'x-requested-with',
]

# ── Email ─────────────────────────────────────────────────────
DEFAULT_FROM_EMAIL   = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@electrosecure.com')
EMAIL_SUBJECT_PREFIX = '[ElectroSecure] '

# ── OAuth2 SSO ────────────────────────────────────────────────
MICROSOFT_CLIENT_ID     = os.environ.get('MICROSOFT_CLIENT_ID', '')
MICROSOFT_CLIENT_SECRET = os.environ.get('MICROSOFT_CLIENT_SECRET', '')
MICROSOFT_TENANT_ID     = os.environ.get('MICROSOFT_TENANT_ID', 'common')
MICROSOFT_REDIRECT_URI  = os.environ.get(
    'MICROSOFT_REDIRECT_URI',
    'http://localhost:8000/api/v1/auth/sso/microsoft/callback/'
)

GOOGLE_CLIENT_ID     = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI  = os.environ.get(
    'GOOGLE_REDIRECT_URI',
    'http://localhost:8000/api/v1/auth/sso/google/callback/'
)

# ── Celery ────────────────────────────────────────────────────
CELERY_BROKER_URL        = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND    = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT    = ['json']
CELERY_TASK_SERIALIZER   = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE          = TIME_ZONE

# ── Sécurité des sessions ─────────────────────────────────────
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY    = True

# ── Logging ───────────────────────────────────────────────────
LOGGING = {
    'version'                 : 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} — {message}',
            'style' : '{',
        },
        'simple': {
            'format': '[{levelname}] {asctime} {message}',
            'style' : '{',
        },
    },
    'handlers': {
        'console': {
            'class'    : 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level'   : 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers' : ['console'],
            'level'    : 'WARNING',
            'propagate': False,
        },
        'electrosecure': {
            'handlers' : ['console'],
            'level'    : 'INFO',
            'propagate': False,
        },
        'electrosecure.alerts': {
            'handlers' : ['console'],
            'level'    : 'WARNING',
            'propagate': False,
        },
    },
}