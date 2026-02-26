"""
Service SSO — Single Sign-On via OAuth2.

SSO permet à un utilisateur de se connecter avec son compte
d'entreprise (Microsoft Azure AD, Google, Okta...) sans créer
de compte séparé.

Flux OAuth2 (Authorization Code) :
1. Utilisateur clique "Se connecter avec Microsoft"
2. Notre app redirige vers le provider (Microsoft)
3. L'utilisateur s'authentifie chez Microsoft
4. Microsoft redirige vers notre callback avec un "code"
5. Notre app échange ce code contre un access_token
6. Notre app récupère les infos de l'utilisateur avec ce token
7. On connecte ou crée l'utilisateur dans notre base

Providers supportés :
- Microsoft Azure AD (entreprises, EPR)
- Google Workspace
- Générique OAuth2

Note : Pour une vraie implémentation, utiliser
'social-auth-app-django' ou 'django-allauth'.
"""

import requests
from django.conf import settings

from ..models import User
from .auth_service import AuthService


class SSOService:

    # --------------------------------------------------------
    # MICROSOFT AZURE AD
    # --------------------------------------------------------

    @staticmethod
    def get_microsoft_auth_url(state: str = '') -> str:
        """
        Génère l'URL de redirection vers Microsoft Azure AD.

        L'utilisateur sera redirigé ici pour s'authentifier.

        Args:
            state : Paramètre anti-CSRF (token aléatoire)

        Returns:
            str : URL Microsoft vers laquelle rediriger l'utilisateur
        """
        params = {
            'client_id':     settings.MICROSOFT_CLIENT_ID,
            'response_type': 'code',
            'redirect_uri':  settings.MICROSOFT_REDIRECT_URI,
            'scope':         'openid email profile',
            'state':         state,
            'response_mode': 'query',
        }
        tenant = settings.MICROSOFT_TENANT_ID
        base_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"

        param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{param_string}"

    @staticmethod
    def handle_microsoft_callback(code: str, request) -> dict:
        """
        Traite le retour de Microsoft après authentification.

        Étapes :
        1. Échanger le code contre un token
        2. Récupérer les infos de l'utilisateur
        3. Créer ou connecter l'utilisateur dans notre base

        Args:
            code    : Code d'autorisation reçu de Microsoft
            request : Requête HTTP Django

        Returns:
            dict : {'user': User, 'tokens': {...}, 'created': bool}
        """
        # 1. Échanger le code contre un access token
        token_data = SSOService._exchange_microsoft_code(code)
        access_token = token_data.get('access_token')

        if not access_token:
            raise ValueError("Impossible d'obtenir le token Microsoft.")

        # 2. Récupérer les infos de l'utilisateur
        user_info = SSOService._get_microsoft_user_info(access_token)

        # 3. Créer ou retrouver l'utilisateur
        user, created = SSOService._get_or_create_user(user_info, provider='microsoft')

        # 4. Générer les tokens JWT
        tokens = AuthService._generate_tokens(user)
        AuthService._record_session(user, request)

        return {
            'user':    user,
            'tokens':  tokens,
            'created': created,  # True si nouveau compte créé
        }

    # --------------------------------------------------------
    # GOOGLE WORKSPACE
    # --------------------------------------------------------

    @staticmethod
    def get_google_auth_url(state: str = '') -> str:
        """
        Génère l'URL de redirection vers Google.
        """
        params = {
            'client_id':     settings.GOOGLE_CLIENT_ID,
            'response_type': 'code',
            'redirect_uri':  settings.GOOGLE_REDIRECT_URI,
            'scope':         'openid email profile',
            'state':         state,
            'access_type':   'offline',
        }
        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{param_string}"

    @staticmethod
    def handle_google_callback(code: str, request) -> dict:
        """
        Traite le retour de Google après authentification.
        """
        token_data = SSOService._exchange_google_code(code)
        access_token = token_data.get('access_token')

        if not access_token:
            raise ValueError("Impossible d'obtenir le token Google.")

        user_info = SSOService._get_google_user_info(access_token)
        user, created = SSOService._get_or_create_user(user_info, provider='google')

        tokens = AuthService._generate_tokens(user)
        AuthService._record_session(user, request)

        return {'user': user, 'tokens': tokens, 'created': created}

    # --------------------------------------------------------
    # MÉTHODES PRIVÉES
    # --------------------------------------------------------

    @staticmethod
    def _exchange_microsoft_code(code: str) -> dict:
        """Échange le code d'autorisation contre un token Microsoft."""
        tenant = settings.MICROSOFT_TENANT_ID
        url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"

        response = requests.post(url, data={
            'client_id':     settings.MICROSOFT_CLIENT_ID,
            'client_secret': settings.MICROSOFT_CLIENT_SECRET,
            'code':          code,
            'redirect_uri':  settings.MICROSOFT_REDIRECT_URI,
            'grant_type':    'authorization_code',
        })
        return response.json()

    @staticmethod
    def _get_microsoft_user_info(access_token: str) -> dict:
        """Récupère les infos utilisateur depuis l'API Microsoft Graph."""
        response = requests.get(
            'https://graph.microsoft.com/v1.0/me',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        data = response.json()
        return {
            'email':      data.get('mail') or data.get('userPrincipalName'),
            'first_name': data.get('givenName', ''),
            'last_name':  data.get('surname', ''),
            'provider_id': data.get('id'),
        }

    @staticmethod
    def _exchange_google_code(code: str) -> dict:
        """Échange le code d'autorisation contre un token Google."""
        response = requests.post('https://oauth2.googleapis.com/token', data={
            'client_id':     settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'code':          code,
            'redirect_uri':  settings.GOOGLE_REDIRECT_URI,
            'grant_type':    'authorization_code',
        })
        return response.json()

    @staticmethod
    def _get_google_user_info(access_token: str) -> dict:
        """Récupère les infos utilisateur depuis l'API Google."""
        response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        data = response.json()
        return {
            'email':       data.get('email'),
            'first_name':  data.get('given_name', ''),
            'last_name':   data.get('family_name', ''),
            'provider_id': data.get('id'),
        }

    @staticmethod
    def _get_or_create_user(user_info: dict, provider: str) -> tuple:
        """
        Crée l'utilisateur s'il n'existe pas, ou le retourne.

        Returns:
            tuple : (User, created: bool)
        """
        email = user_info.get('email', '').lower()

        if not email:
            raise ValueError("Impossible de récupérer l'email depuis le provider SSO.")

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name':    user_info.get('first_name', ''),
                'last_name':     user_info.get('last_name', ''),
                'email_verified': True,  # Email vérifié par le provider
                'is_active':     True,
            }
        )

        # Mettre à jour last_login
        from django.utils import timezone
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        return user, created