"""
Tâches Celery périodiques pour l'app authentication.

- cleanup_expired_tokens_task → toutes les heures
"""

import logging
from celery import shared_task

logger = logging.getLogger('electrosecure')


@shared_task(bind=True)
def cleanup_expired_tokens_task(self):
    """
    Purge les tokens JWT expirés de la blacklist.

    Sans cette tâche, la table OutstandingToken grossit indéfiniment.
    Simple_JWT fournit cette commande : flushexpiredtokens

    Planification : toutes les heures (voir config/celery.py)
    """
    try:
        from rest_framework_simplejwt.token_blacklist.models import (
            OutstandingToken, BlacklistedToken
        )
        from django.utils import timezone

        # Supprimer les tokens expirés de la blacklist
        deleted_bl, _ = BlacklistedToken.objects.filter(
            token__expires_at__lt=timezone.now()
        ).delete()

        # Supprimer les tokens expirés non blacklistés
        deleted_ot, _ = OutstandingToken.objects.filter(
            expires_at__lt=timezone.now()
        ).exclude(
            blacklistedtoken__isnull=False
        ).delete()

        logger.info(
            "[TASK] cleanup_expired_tokens : %d blacklisted + %d outstanding supprimés",
            deleted_bl, deleted_ot
        )
        return {'blacklisted_deleted': deleted_bl, 'outstanding_deleted': deleted_ot}

    except Exception as exc:
        logger.error("[TASK] cleanup_expired_tokens ERREUR : %s", exc)
        return {'error': str(exc)}