"""
Signaux Django pour l'application Authentication.

Un signal = "quand cet événement se produit, exécute cette fonction"
Découplage : le modèle ne sait pas que l'email sera envoyé.

Signaux utilisés :
- post_save  : Après la sauvegarde d'un modèle
- pre_delete : Avant la suppression d'un modèle
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings

from .models import User


@receiver(post_save, sender=User)
def send_welcome_email(sender, instance, created, **kwargs):
    """
    Envoie un email de bienvenue quand un utilisateur est créé.

    'created' est True seulement lors de la création,
    pas lors des mises à jour.
    """
    if created:
        send_mail(
            subject='Bienvenue sur ElectroSecure Platform',
            message=f"""
Bonjour {instance.full_name},

Votre compte ElectroSecure Platform a été créé avec succès.

Email : {instance.email}
Rôle  : {instance.get_role_display()}

Connectez-vous sur : http://localhost:8000/api/docs/

Cordialement,
L'équipe ElectroSecure
            """,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.email],
            fail_silently=True,  # Ne pas crasher si l'email échoue
        )