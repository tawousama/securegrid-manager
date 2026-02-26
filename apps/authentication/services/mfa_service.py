"""
Service MFA — Logique de l'authentification à deux facteurs.

Fonctionnement TOTP (Time-based One-Time Password) :
1. Le serveur génère une clé secrète unique (base32)
2. L'utilisateur scanne le QR Code avec Google Authenticator
3. L'application génère un code à 6 chiffres toutes les 30 secondes
   en utilisant : HMAC-SHA1(secret_key, floor(timestamp / 30))
4. L'utilisateur saisit ce code lors de la connexion
5. Le serveur refait le même calcul et compare

Bibliothèque utilisée : pyotp (Python One-Time Password)
Installation : pip install pyotp qrcode
"""

import pyotp
import qrcode
import base64
from io import BytesIO
from django.utils import timezone

from ..models import User, MFADevice


class MFAService:

    APP_NAME = "ElectroSecure Platform"

    # --------------------------------------------------------
    # ACTIVATION DU MFA
    # --------------------------------------------------------

    @staticmethod
    def initiate_mfa_setup(user: User, device_name: str = "Mon téléphone") -> dict:
        """
        Initie la configuration du MFA pour un utilisateur.

        Génère une clé secrète et crée un dispositif non vérifié.
        L'utilisateur doit scanner le QR Code PUIS valider avec un code
        pour confirmer que la configuration a réussi.

        Returns:
            dict : {
                'qr_code': '<base64 image>',   → À afficher à l'utilisateur
                'manual_key': 'JBSWY3DP...',   → Clé manuelle (si scan impossible)
                'device_id': '<uuid>'           → ID du dispositif créé
            }
        """
        # Supprimer tout dispositif TOTP non vérifié existant
        MFADevice.objects.filter(
            user=user,
            device_type=MFADevice.DEVICE_TYPE_TOTP,
            is_verified=False
        ).delete()

        # Générer une nouvelle clé secrète base32
        secret_key = pyotp.random_base32()

        # Créer le dispositif (non vérifié pour l'instant)
        device = MFADevice.objects.create(
            user        = user,
            device_type = MFADevice.DEVICE_TYPE_TOTP,
            name        = device_name,
            secret_key  = secret_key,
            is_verified = False,
        )

        # Générer l'URL pour Google Authenticator
        totp_uri = pyotp.totp.TOTP(secret_key).provisioning_uri(
            name=user.email,
            issuer_name=MFAService.APP_NAME
        )

        # Générer le QR Code en base64 (pour l'afficher dans le navigateur)
        qr_code_b64 = MFAService._generate_qr_code(totp_uri)

        return {
            'qr_code':   qr_code_b64,
            'manual_key': secret_key,
            'device_id': str(device.id),
        }

    @staticmethod
    def confirm_mfa_setup(user: User, device_id: str, code: str) -> bool:
        """
        Confirme l'activation du MFA en vérifiant le premier code.

        L'utilisateur scanne le QR Code et saisit le premier code généré.
        Si le code est valide, le dispositif est marqué comme vérifié
        et le MFA est activé sur le compte.

        Returns:
            bool : True si activation réussie, False sinon
        """
        try:
            device = MFADevice.objects.get(
                id=device_id,
                user=user,
                is_verified=False
            )
        except MFADevice.DoesNotExist:
            return False

        # Vérifier le code
        if not MFAService._verify_totp(device.secret_key, code):
            return False

        # Marquer le dispositif comme vérifié
        device.is_verified = True
        device.is_primary  = True
        device.last_used   = timezone.now()
        device.save()

        # Activer le MFA sur le compte
        user.mfa_enabled = True
        user.save(update_fields=['mfa_enabled'])

        return True

    # --------------------------------------------------------
    # VÉRIFICATION DU CODE MFA (lors de la connexion)
    # --------------------------------------------------------

    @staticmethod
    def verify_mfa_code(user: User, code: str) -> bool:
        """
        Vérifie un code MFA lors de la connexion.

        Cherche le dispositif principal vérifié de l'utilisateur
        et vérifie le code TOTP.

        Returns:
            bool : True si le code est valide
        """
        try:
            device = MFADevice.objects.get(
                user=user,
                is_verified=True,
                is_primary=True
            )
        except MFADevice.DoesNotExist:
            return False

        is_valid = MFAService._verify_totp(device.secret_key, code)

        if is_valid:
            device.last_used = timezone.now()
            device.save(update_fields=['last_used'])

        return is_valid

    # --------------------------------------------------------
    # DÉSACTIVATION DU MFA
    # --------------------------------------------------------

    @staticmethod
    def disable_mfa(user: User, code: str) -> bool:
        """
        Désactive le MFA après vérification du code actuel.

        Pour désactiver le MFA, l'utilisateur doit d'abord
        prouver qu'il a encore accès à son dispositif.

        Returns:
            bool : True si désactivation réussie
        """
        # Vérifier le code avant de désactiver
        if not MFAService.verify_mfa_code(user, code):
            return False

        # Supprimer tous les dispositifs
        MFADevice.objects.filter(user=user).delete()

        # Désactiver le MFA sur le compte
        user.mfa_enabled = False
        user.save(update_fields=['mfa_enabled'])

        return True

    # --------------------------------------------------------
    # MÉTHODES PRIVÉES
    # --------------------------------------------------------

    @staticmethod
    def _verify_totp(secret_key: str, code: str) -> bool:
        """
        Vérifie un code TOTP.

        valid_window=1 : Accepte le code de la période précédente
        et suivante (tolérance horloge de ±30 secondes).
        """
        totp = pyotp.TOTP(secret_key)
        return totp.verify(code, valid_window=1)

    @staticmethod
    def _generate_qr_code(uri: str) -> str:
        """
        Génère un QR Code à partir de l'URI TOTP.
        Retourne l'image en base64 pour l'affichage web.

        Returns:
            str : 'data:image/png;base64,<données>'
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{img_b64}"