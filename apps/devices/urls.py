"""
URLs de l'application Devices.
Préfixées par /api/v1/devices/

  GET/POST    /                               → liste + enregistrer
  GET/PUT/DEL /{id}/                          → détail
  POST        /{id}/scan/                     → lancer un scan
  POST        /{id}/status/                   → mettre à jour le statut
  GET         /{id}/ports/                    → ports réseau
  GET         /{id}/vulnerabilities/          → vulnérabilités CVE
  POST        /{id}/vulnerabilities/{cve}/patch/ → corriger une CVE
  GET         /{id}/scans/                    → historique des scans
  GET         /network-map/                   → cartographie réseau
  GET         /stats/                         → statistiques globales
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DeviceViewSet, NetworkMapView, DeviceStatsView

router = DefaultRouter()
router.register(r'', DeviceViewSet, basename='device')

urlpatterns = [
    path('network-map/', NetworkMapView.as_view(), name='network-map'),
    path('stats/',       DeviceStatsView.as_view(), name='device-stats'),
    path('',             include(router.urls)),
]