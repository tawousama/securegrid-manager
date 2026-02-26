#!/usr/bin/env python
"""
Point d'entrée Django — gestion du projet.

Commandes utiles :
    python manage.py runserver              → Démarrer le serveur de dev
    python manage.py makemigrations        → Créer les migrations
    python manage.py migrate               → Appliquer les migrations
    python manage.py createsuperuser       → Créer un admin
    python manage.py test                  → Lancer les tests
    python manage.py shell                 → Shell interactif Django
    python manage.py collectstatic         → Collecter les fichiers statiques
"""

import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django introuvable. Vérifiez que votre environnement virtuel "
            "est activé : source venv/bin/activate"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()