"""
URLs de l'application Cable Routing.

Préfixées par /api/v1/electrical/cables/ (défini dans config/urls.py)

Endpoints disponibles :

  Types de câbles :
    GET/POST   /types/           → liste + créer
    GET/PUT/DELETE /types/{id}/  → détail

  Chemins de câbles :
    GET/POST   /pathways/           → liste + créer
    GET/PUT/DELETE /pathways/{id}/  → détail

  Câbles :
    GET/POST   /                    → liste + créer
    GET/PUT/DELETE /{id}/           → détail
    POST       /{id}/route/         → calculer tracé automatique
    GET        /{id}/calculate/     → calculs électriques IEC
    GET        /{id}/routes/        → historique des tracés
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CableViewSet, CableTypeViewSet, CablePathwayViewSet

router = DefaultRouter()
router.register(r'types',    CableTypeViewSet,    basename='cable-type')
router.register(r'pathways', CablePathwayViewSet, basename='cable-pathway')
router.register(r'',         CableViewSet,        basename='cable')

urlpatterns = [
    path('', include(router.urls)),
]