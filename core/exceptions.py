"""
Exceptions personnalisées du projet ElectroSecure Platform.

Pourquoi des exceptions personnalisées ?
- Erreurs spécifiques au domaine métier
- Messages d'erreur cohérents dans toute l'API
- Codes HTTP automatiquement associés
- Facilite le débogage et le monitoring

Hiérarchie :
    BaseAPIException
    ├── ValidationError       (400)
    ├── AuthenticationError   (401)
    ├── PermissionDeniedError (403)
    ├── NotFoundError         (404)
    ├── ConflictError         (409)
    ├── BusinessLogicError    (422)
    └── ServiceUnavailableError (503)
"""

from rest_framework.exceptions import APIException
from rest_framework import status


# ============================================================
# EXCEPTION DE BASE
# ============================================================

class BaseAPIException(APIException):
    """
    Exception de base dont toutes les autres héritent.

    Exemple d'usage :
        raise BaseAPIException("Une erreur est survenue")
    """
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Une erreur inattendue est survenue."
    default_code = "error"


# ============================================================
# ERREURS D'AUTHENTIFICATION ET PERMISSIONS
# ============================================================

class AuthenticationError(BaseAPIException):
    """
    Levée quand l'utilisateur n'est pas authentifié.

    Exemple :
        if not request.user.is_authenticated:
            raise AuthenticationError()
    """
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentification requise."
    default_code = "authentication_required"


class PermissionDeniedError(BaseAPIException):
    """
    Levée quand l'utilisateur n'a pas les droits nécessaires.

    Exemple :
        if not user.has_role('engineer'):
            raise PermissionDeniedError("Seuls les ingénieurs peuvent modifier ce câble.")
    """
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Vous n'avez pas la permission d'effectuer cette action."
    default_code = "permission_denied"


class MFARequiredError(BaseAPIException):
    """
    Levée quand la double authentification est requise.

    Exemple :
        if not user.mfa_verified:
            raise MFARequiredError()
    """
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "La double authentification (MFA) est requise pour cette action."
    default_code = "mfa_required"


class TokenExpiredError(BaseAPIException):
    """
    Levée quand le token JWT est expiré.
    """
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Votre session a expiré. Veuillez vous reconnecter."
    default_code = "token_expired"


# ============================================================
# ERREURS DE RESSOURCES
# ============================================================

class NotFoundError(BaseAPIException):
    """
    Levée quand une ressource n'existe pas.

    Exemple :
        cable = Cable.objects.filter(id=pk).first()
        if not cable:
            raise NotFoundError(f"Câble avec l'ID {pk} introuvable.")
    """
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "La ressource demandée est introuvable."
    default_code = "not_found"


class ConflictError(BaseAPIException):
    """
    Levée quand il y a un conflit (ex: doublon).

    Exemple :
        if Cable.objects.filter(reference=ref).exists():
            raise ConflictError(f"Un câble avec la référence '{ref}' existe déjà.")
    """
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Un conflit a été détecté avec une ressource existante."
    default_code = "conflict"


# ============================================================
# ERREURS DE VALIDATION
# ============================================================

class ValidationError(BaseAPIException):
    """
    Levée quand des données sont invalides.

    Exemple :
        if cable.section not in VALID_SECTIONS:
            raise ValidationError("Section de câble non standard.")
    """
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Les données fournies sont invalides."
    default_code = "validation_error"


class BusinessLogicError(BaseAPIException):
    """
    Levée quand une règle métier est violée.

    Exemple :
        if cable.voltage > circuit.max_voltage:
            raise BusinessLogicError(
                "La tension du câble dépasse la tension maximale du circuit."
            )
    """
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "L'opération viole une règle métier."
    default_code = "business_logic_error"


# ============================================================
# ERREURS MÉTIER ÉLECTRICITÉ
# ============================================================

class CableRoutingError(BusinessLogicError):
    """
    Levée quand un routage de câble est impossible.

    Exemple :
        if not path_exists(start, end):
            raise CableRoutingError("Aucun chemin disponible entre ces deux points.")
    """
    default_detail = "Impossible de router le câble selon les contraintes définies."
    default_code = "cable_routing_error"


class ElectricalComplianceError(BusinessLogicError):
    """
    Levée quand une installation ne respecte pas les normes électriques.

    Exemple :
        if not check_iec_compliance(installation):
            raise ElectricalComplianceError("Non conforme à la norme IEC 60364.")
    """
    default_detail = "L'installation ne respecte pas les normes électriques en vigueur."
    default_code = "electrical_compliance_error"


class ConnectionIncompatibleError(BusinessLogicError):
    """
    Levée quand deux éléments ne peuvent pas être raccordés.

    Exemple :
        if terminal_a.voltage != terminal_b.voltage:
            raise ConnectionIncompatibleError(
                "Impossibe de raccorder deux terminaux de tensions différentes."
            )
    """
    default_detail = "Les éléments ne sont pas compatibles pour ce raccordement."
    default_code = "connection_incompatible"


# ============================================================
# ERREURS DE SERVICES EXTERNES
# ============================================================

class ServiceUnavailableError(BaseAPIException):
    """
    Levée quand un service externe est indisponible.

    Exemple :
        if not sso_provider.is_available():
            raise ServiceUnavailableError("Le service SSO est momentanément indisponible.")
    """
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Le service est momentanément indisponible. Réessayez plus tard."
    default_code = "service_unavailable"


class ExternalAPIError(ServiceUnavailableError):
    """
    Levée quand un appel à une API externe échoue.
    """
    default_detail = "Une erreur est survenue lors de la communication avec un service externe."
    default_code = "external_api_error"


# ============================================================
# HANDLER GLOBAL POUR DRF
# ============================================================

def custom_exception_handler(exc, context):
    """
    Handler global qui intercepte toutes les exceptions et
    retourne une réponse JSON formatée de manière cohérente.

    Format de réponse :
    {
        "error": true,
        "code": "not_found",
        "message": "La ressource est introuvable.",
        "details": {...}  // optionnel
    }

    À déclarer dans settings.py :
        REST_FRAMEWORK = {
            'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler'
        }
    """
    from rest_framework.views import exception_handler
    from rest_framework.response import Response

    # Appeler d'abord le handler par défaut de DRF
    response = exception_handler(exc, context)

    if response is not None:
        error_code = getattr(exc, 'default_code', 'error')
        message = str(exc.detail) if hasattr(exc, 'detail') else str(exc)

        response.data = {
            'error': True,
            'code': error_code,
            'message': message,
        }

    return response