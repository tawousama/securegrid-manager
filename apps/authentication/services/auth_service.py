"""
Service d'authentification — Logique métier de connexion/inscription.

Principe de séparation des responsabilités :
- View   : reçoit la requête, appelle le service, retourne la réponse
- Service: contient toute la logique métier
- Model  : gère la persistance des données

Avantage : Le service est testable sans serveur HTTP.
"""

from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import User, UserSession


class AuthService:

    # --------------------------------------------------------
    # INSCRIPTION
    # --------------------------------------------------------

    @staticmethod
    def register(validated_data: dict) -> dict:
        """
        Crée un nouveau compte utilisateur et retourne ses tokens JWT.

        Étapes :
        1. Créer l'utilisateur (le serializer a déjà validé les données)
        2. Générer les tokens JWT
        3. Retourner user + tokens

        Args:
            validated_data : Données validées par RegisterSerializer

        Returns:
            dict : {'user': User, 'tokens': {'access': ..., 'refresh': ...}}
        """
        # Le serializer a déjà créé l'utilisateur via create()
        user   = validated_data
        tokens = AuthService._generate_tokens(user)

        return {'user': user, 'tokens': tokens}

    # --------------------------------------------------------
    # CONNEXION
    # --------------------------------------------------------

    @staticmethod
    def login(user: User, request) -> dict:
        """
        Authentifie un utilisateur et retourne ses tokens JWT.

        Si le MFA est activé, retourne mfa_required=True
        et l'utilisateur doit valider avec son code MFA.

        Args:
            user    : Utilisateur validé par LoginSerializer
            request : Requête HTTP (pour logger l'IP)

        Returns:
            dict : Tokens JWT ou indication que MFA est requis
        """
        # Cas 1 : MFA activé → demander le code
        if user.mfa_enabled:
            return {
                'mfa_required': True,
                'user_id': str(user.id),
                'message': "Veuillez saisir votre code MFA."
            }

        # Cas 2 : Pas de MFA → connexion directe
        AuthService._record_session(user, request)
        tokens = AuthService._generate_tokens(user)

        return {
            'mfa_required': False,
            'user': user,
            'tokens': tokens
        }

    # --------------------------------------------------------
    # DÉCONNEXION
    # --------------------------------------------------------

    @staticmethod
    def logout(user: User, refresh_token: str) -> None:
        """
        Déconnecte l'utilisateur en blacklistant son refresh token.

        Avec JWT, on ne peut pas "supprimer" un token côté serveur.
        On l'ajoute à une liste noire (blacklist) pour le rendre invalide.

        Args:
            user          : Utilisateur à déconnecter
            refresh_token : Token à blacklister
        """
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()  # Rend le token invalide
        except Exception:
            pass  # Token déjà invalide, pas grave

        # Fermer la session active en base
        UserSession.objects.filter(
            user=user,
            is_active=True
        ).update(
            is_active=False,
            logged_out_at=timezone.now()
        )

    # --------------------------------------------------------
    # MÉTHODES PRIVÉES (helpers internes)
    # --------------------------------------------------------

    @staticmethod
    def _generate_tokens(user: User) -> dict:
        """
        Génère une paire de tokens JWT pour l'utilisateur.

        Access Token  : Valide 60 minutes. Envoyé à chaque requête.
        Refresh Token : Valide 1 jour. Permet d'obtenir un nouveau access token.

        Returns:
            dict : {'access': 'eyJ...', 'refresh': 'eyJ...'}
        """
        refresh = RefreshToken.for_user(user)

        # Ajouter des données custom au token (payload)
        refresh['email'] = user.email
        refresh['role']  = user.role

        return {
            'access':  str(refresh.access_token),
            'refresh': str(refresh),
        }

    @staticmethod
    def _record_session(user: User, request) -> None:
        """
        Enregistre une nouvelle session en base de données.
        Utilisé pour l'audit de sécurité.
        """
        ip_address = AuthService._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        UserSession.objects.create(
            user       = user,
            ip_address = ip_address,
            user_agent = user_agent[:500],  # Limiter la taille
        )

        # Mettre à jour last_login
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

    @staticmethod
    def _get_client_ip(request) -> str:
        """
        Récupère l'adresse IP réelle du client.
        Gère le cas d'un proxy (X-Forwarded-For).
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')