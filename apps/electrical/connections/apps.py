from django.apps import AppConfig


class ConnectionsConfig(AppConfig):
    name         = 'apps.electrical.connections'
    verbose_name = '🔌 Raccordements Électriques'
    default_auto_field = 'django.db.models.BigAutoField'