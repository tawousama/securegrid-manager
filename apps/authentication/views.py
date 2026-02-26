"""
Vues de l'application Authentication.

Chaque vue :
1. Reçoit la requête HTTP
2. Valide les données avec un Serializer
3. Appelle le Service approprié
4. Retourne une réponse JSON

Les vues restent LÉGÈRES — toute la logique est dans les services.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenRefreshView

from .models import User, MFADevice, UserSession
from .serializers import (
    UserSerializer, RegisterSerializer, LoginSerializer,
    PasswordChangeSerializer, MFAEnableSerializer,
    MFAVerifySerializer, UpdateProfileSerializer,
    MFADeviceSerializer,
)
from .services.auth_service import AuthService
from .services.mfa_service import MFAService
from .services.sso_service import SSOService
from core.exceptions import ValidationError, NotFoundError


# ============================================================
# INSCRIPTION / CONNEXION / DÉCONNEXION
# ============================================================

class RegisterView(APIView):
    """
    POST /api/v1/auth/register/

    Corps de la requête :
    {
        "email": "john@example.com",
        "password": "SecurePass123!",
        "password2": "SecurePass123!",
        "first_name": "John",
        "last_name": "Doe"
    }

    Réponse 201 :
    {
        "user": {...},
        "tokens": {"access": "...", "refresh": "..."}
    }
    """
    permission_classes = [AllowAny]  # Pas besoin d'être connecté

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        # Créer l'utilisateur via le serializer
        user   = serializer.save()
        result = AuthService.register(user)

        return Response({
            'user':   UserSerializer(result['user']).data,
            'tokens': result['tokens'],
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    POST /api/v1/auth/login/

    Corps de la requête :
    {
        "email": "john@example.com",
        "password": "SecurePass123!"
    }

    Réponse 200 (sans MFA) :
    {
        "mfa_required": false,
        "user": {...},
        "tokens": {"access": "...", "refresh": "..."}
    }

    Réponse 200 (avec MFA) :
    {
        "mfa_required": true,
        "user_id": "...",
        "message": "Veuillez saisir votre code MFA."
    }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_401_UNAUTHORIZED
            )

        user   = serializer.validated_data['user']
        result = AuthService.login(user, request)

        if result.get('mfa_required'):
            return Response(result, status=status.HTTP_200_OK)

        return Response({
            'mfa_required': False,
            'user':         UserSerializer(result['user']).data,
            'tokens':       result['tokens'],
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/

    Corps de la requête :
    {
        "refresh": "eyJ..."
    }

    Réponse 200 :
    {
        "message": "Déconnexion réussie."
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')

        if not refresh_token:
            return Response(
                {'error': 'Le refresh token est requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        AuthService.logout(request.user, refresh_token)

        return Response(
            {'message': 'Déconnexion réussie.'},
            status=status.HTTP_200_OK
        )


# ============================================================
# PROFIL UTILISATEUR
# ============================================================

class MeView(APIView):
    """
    GET  /api/v1/auth/me/  → Récupérer le profil
    PUT  /api/v1/auth/me/  → Mettre à jour le profil
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Retourne le profil de l'utilisateur connecté."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        """Met à jour les informations du profil."""
        serializer = UpdateProfileSerializer(
            request.user,
            data=request.data,
            partial=True,  # Mise à jour partielle (PATCH-like)
            context={'request': request}
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer.save()
        return Response(UserSerializer(request.user).data)


class PasswordChangeView(APIView):
    """
    POST /api/v1/auth/password/change/

    Corps :
    {
        "old_password": "AncienMotDePasse",
        "new_password": "NouveauMotDePasse123!",
        "new_password2": "NouveauMotDePasse123!"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()

        return Response(
            {'message': 'Mot de passe modifié avec succès.'},
            status=status.HTTP_200_OK
        )


# ============================================================
# MFA (Multi-Factor Authentication)
# ============================================================

class MFASetupView(APIView):
    """
    POST /api/v1/auth/mfa/setup/

    Initie la configuration du MFA.
    Retourne un QR Code à scanner.

    Réponse :
    {
        "qr_code": "data:image/png;base64,...",
        "manual_key": "JBSWY3DPEHPK3PXP",
        "device_id": "..."
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MFAEnableSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        result = MFAService.initiate_mfa_setup(
            user=request.user,
            device_name=serializer.validated_data.get('name', 'Mon téléphone')
        )

        return Response(result, status=status.HTTP_200_OK)


class MFAConfirmView(APIView):
    """
    POST /api/v1/auth/mfa/confirm/

    Confirme l'activation du MFA avec le premier code.

    Corps :
    {
        "device_id": "...",
        "code": "123456"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        device_id = request.data.get('device_id')
        code      = request.data.get('code')

        if not device_id or not code:
            return Response(
                {'error': 'device_id et code sont requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        success = MFAService.confirm_mfa_setup(request.user, device_id, code)

        if not success:
            return Response(
                {'error': 'Code MFA invalide. Vérifiez l\'heure de votre téléphone.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {'message': 'MFA activé avec succès.'},
            status=status.HTTP_200_OK
        )


class MFAVerifyView(APIView):
    """
    POST /api/v1/auth/mfa/verify/

    Vérifie le code MFA lors de la connexion.
    Retourne les tokens JWT si le code est valide.

    Corps :
    {
        "user_id": "...",
        "code": "123456"
    }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        user_id = request.data.get('user_id')
        code    = request.data.get('code')

        try:
            user = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            return Response(
                {'error': 'Utilisateur invalide.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not MFAService.verify_mfa_code(user, code):
            return Response(
                {'error': 'Code MFA invalide ou expiré.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        AuthService._record_session(user, request)
        tokens = AuthService._generate_tokens(user)

        return Response({
            'user':   UserSerializer(user).data,
            'tokens': tokens,
        }, status=status.HTTP_200_OK)


class MFADisableView(APIView):
    """
    POST /api/v1/auth/mfa/disable/

    Désactive le MFA (nécessite le code actuel).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MFAVerifySerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        code = serializer.validated_data['code']
        success = MFAService.disable_mfa(request.user, code)

        if not success:
            return Response(
                {'error': 'Code MFA invalide.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {'message': 'MFA désactivé avec succès.'},
            status=status.HTTP_200_OK
        )


# ============================================================
# SSO (Single Sign-On)
# ============================================================

class MicrosoftSSOView(APIView):
    """
    GET /api/v1/auth/sso/microsoft/

    Redirige l'utilisateur vers Microsoft pour l'authentification.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        import secrets
        state   = secrets.token_urlsafe(32)
        auth_url = SSOService.get_microsoft_auth_url(state)
        return Response({'auth_url': auth_url})


class MicrosoftCallbackView(APIView):
    """
    GET /api/v1/auth/sso/microsoft/callback/?code=...

    Microsoft redirige ici après authentification.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        code = request.query_params.get('code')

        if not code:
            return Response(
                {'error': 'Code d\'autorisation manquant.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = SSOService.handle_microsoft_callback(code, request)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'user':    UserSerializer(result['user']).data,
            'tokens':  result['tokens'],
            'created': result['created'],
        })