"""
Configuration de l'application Authentication.

AppConfig est exécuté au démarrage de Django.
Le nom affiché dans l'admin et dans les logs vient d'ici.
"""

from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    name           = 'apps.authentication'
    verbose_name   = '🔐 Authentification'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        """
        Exécuté une seule fois au démarrage de Django.
        On importe les signaux ici pour qu'ils soient connectés.

        Un signal = "quand cet événement se produit, exécute cette fonction"
        Exemple : quand un User est créé → envoyer un email de bienvenue
        """
        import apps.authentication.signals  # noqa: F401