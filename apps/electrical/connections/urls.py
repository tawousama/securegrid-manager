"""
URLs de l'application Connections.
Préfixées par /api/v1/electrical/connections/

Endpoints :

  Borniers :
    GET/POST    /terminal-blocks/         → liste + créer
    GET/PUT/DEL /terminal-blocks/{id}/    → détail

  Bornes :
    GET/POST    /terminals/               → liste + créer
    GET/PUT/DEL /terminals/{id}/          → détail

  Raccordements :
    GET/POST    /                         → liste + créer
    GET/PUT/DEL /{id}/                    → détail
    POST        /{id}/points/             → ajouter conducteur
    POST        /{id}/complete/           → marquer réalisé
    POST        /{id}/verify/             → valider (ingénieur)
    POST        /{id}/fault/              → signaler défaut
    GET         /{id}/diagram/            → schéma de câblage
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConnectionViewSet, TerminalBlockViewSet, TerminalViewSet

router = DefaultRouter()
router.register(r'terminal-blocks', TerminalBlockViewSet, basename='terminal-block')
router.register(r'terminals',       TerminalViewSet,      basename='terminal')
router.register(r'',                ConnectionViewSet,    basename='connection')

urlpatterns = [
    path('', include(router.urls)),
]