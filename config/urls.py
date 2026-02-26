"""
Configuration des URLs — ElectroSecure Platform.

Toutes les routes de l'API sont préfixées par /api/v1/

Structure :
    /admin/                                → Django Admin
    /api/v1/auth/                          → Authentification (JWT, SSO, MFA)
    /api/v1/electrical/cables/             → Câbles & routage
    /api/v1/electrical/connections/        → Raccordements
    /api/v1/electrical/schematics/         → Schémas électriques
    /api/v1/devices/                       → Équipements & supervision
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# ── Admin ─────────────────────────────────────────────────────
admin.site.site_header  = '⚡ ElectroSecure Platform'
admin.site.site_title   = 'ElectroSecure Admin'
admin.site.index_title  = 'Tableau de bord administration'

# ── URL patterns ─────────────────────────────────────────────
urlpatterns = [

    # Administration Django
    path('admin/', admin.site.urls),

    # ── Authentification ──────────────────────────────────────
    # JWT login/refresh/logout, SSO Microsoft/Google, MFA TOTP
    path('api/v1/auth/', include('apps.authentication.urls')),

    # ── Domaine Électrique ────────────────────────────────────
    path('api/v1/electrical/', include([

        # Câbles, types, chemins de câbles, routage BFS
        # GET/POST /api/v1/electrical/cables/
        # POST     /api/v1/electrical/cables/{id}/route/
        # GET      /api/v1/electrical/cables/{id}/calculate/
        path('cables/', include('apps.electrical.cable_routing.urls')),

        # Raccordements, bornes, borniers
        # GET/POST /api/v1/electrical/connections/
        # POST     /api/v1/electrical/connections/{id}/verify/
        path('connections/', include('apps.electrical.connections.urls')),

        # Schémas électriques
        # GET/POST /api/v1/electrical/schematics/
        # GET      /api/v1/electrical/schematics/{id}/export/svg/
        path('schematics/', include('apps.electrical.schematics.urls')),
    ])),

    # ── Équipements & Supervision ─────────────────────────────
    # Inventaire réseau, scans CVE, alertes, cartographie
    # GET      /api/v1/devices/network-map/
    # GET      /api/v1/devices/stats/
    # POST     /api/v1/devices/{id}/scan/
    path('api/v1/devices/', include('apps.devices.urls')),

]

# ── Fichiers médias (dev uniquement) ─────────────────────────
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,  document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)