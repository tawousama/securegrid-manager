"""
URLs de l'application Authentication.

Toutes ces URLs sont préfixées par /api/v1/auth/
(défini dans config/urls.py)

Tableau des endpoints :

Méthode  URL                          Vue                   Description
-------  ---------------------------  --------------------  ---------------------
POST     /register/                   RegisterView          Créer un compte
POST     /login/                      LoginView             Se connecter
POST     /logout/                     LogoutView            Se déconnecter
POST     /token/refresh/              TokenRefreshView      Renouveler le token
GET      /me/                         MeView                Mon profil
PUT      /me/                         MeView                Modifier mon profil
POST     /password/change/            PasswordChangeView    Changer mon mdp
POST     /mfa/setup/                  MFASetupView          Activer le MFA (étape 1)
POST     /mfa/confirm/                MFAConfirmView        Activer le MFA (étape 2)
POST     /mfa/verify/                 MFAVerifyView         Vérifier code MFA (login)
POST     /mfa/disable/                MFADisableView        Désactiver le MFA
GET      /sso/microsoft/              MicrosoftSSOView      Lancer le SSO Microsoft
GET      /sso/microsoft/callback/     MicrosoftCallbackView Retour SSO Microsoft
GET      /sso/google/                 GoogleSSOView         Lancer le SSO Google
GET      /sso/google/callback/        GoogleCallbackView    Retour SSO Google
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RegisterView, LoginView, LogoutView,
    MeView, PasswordChangeView,
    MFASetupView, MFAConfirmView, MFAVerifyView, MFADisableView,
    MicrosoftSSOView, MicrosoftCallbackView,
)

app_name = 'authentication'

urlpatterns = [

    # --- Compte ---
    path('register/',        RegisterView.as_view(),       name='register'),
    path('login/',           LoginView.as_view(),           name='login'),
    path('logout/',          LogoutView.as_view(),          name='logout'),
    path('token/refresh/',   TokenRefreshView.as_view(),    name='token-refresh'),

    # --- Profil ---
    path('me/',              MeView.as_view(),              name='me'),
    path('password/change/', PasswordChangeView.as_view(),  name='password-change'),

    # --- MFA ---
    path('mfa/setup/',       MFASetupView.as_view(),        name='mfa-setup'),
    path('mfa/confirm/',     MFAConfirmView.as_view(),      name='mfa-confirm'),
    path('mfa/verify/',      MFAVerifyView.as_view(),       name='mfa-verify'),
    path('mfa/disable/',     MFADisableView.as_view(),      name='mfa-disable'),

    # --- SSO Microsoft ---
    path('sso/microsoft/',            MicrosoftSSOView.as_view(),      name='sso-microsoft'),
    path('sso/microsoft/callback/',   MicrosoftCallbackView.as_view(), name='sso-microsoft-callback'),
]