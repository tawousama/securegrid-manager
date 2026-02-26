"""
URLs de l'application Schematics.
Préfixées par /api/v1/electrical/schematics/

  GET/POST    /                      → liste + créer
  GET/PUT/DEL /{id}/                 → détail
  POST        /{id}/generate/        → générer depuis les câbles
  POST        /{id}/submit-review/   → soumettre pour révision
  POST        /{id}/approve/         → approuver (ingénieur)
  GET         /{id}/export/svg/      → télécharger SVG
  GET         /{id}/export/json/     → télécharger JSON
  GET         /{id}/export/csv/      → télécharger CSV
  GET/POST    /{id}/elements/        → éléments du schéma
  GET/POST    /{id}/links/           → liens du schéma
  GET         /{id}/revisions/       → historique des révisions
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SchematicViewSet

router = DefaultRouter()
router.register(r'', SchematicViewSet, basename='schematic')

urlpatterns = [
    path('', include(router.urls)),
]