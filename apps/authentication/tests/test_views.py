"""
Tests des vues de l'application Authentication.

On utilise APIClient de DRF pour simuler des requêtes HTTP.
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.authentication.models import User


class RegisterViewTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url    = reverse('authentication:register')
        self.valid_data = {
            'email':      'test@example.com',
            'password':   'SecurePass123!',
            'password2':  'SecurePass123!',
            'first_name': 'John',
            'last_name':  'Doe',
        }

    def test_register_success(self):
        """Inscription valide crée un utilisateur et retourne les tokens."""
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('tokens', response.data)
        self.assertIn('user', response.data)

    def test_register_duplicate_email(self):
        """Deux inscriptions avec le même email retourne une erreur."""
        self.client.post(self.url, self.valid_data, format='json')
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_passwords_dont_match(self):
        """Mots de passe différents retourne une erreur."""
        data = {**self.valid_data, 'password2': 'AutreMotDePasse!'}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_email(self):
        """Email manquant retourne une erreur."""
        data = {**self.valid_data}
        del data['email']
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginViewTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url    = reverse('authentication:login')
        self.user   = User.objects.create_user(
            email='test@example.com',
            password='SecurePass123!',
            first_name='John',
            last_name='Doe'
        )

    def test_login_success(self):
        """Connexion valide retourne les tokens JWT."""
        response = self.client.post(self.url, {
            'email':    'test@example.com',
            'password': 'SecurePass123!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])

    def test_login_wrong_password(self):
        """Mauvais mot de passe retourne 401."""
        response = self.client.post(self.url, {
            'email':    'test@example.com',
            'password': 'MauvaisMotDePasse',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_unknown_email(self):
        """Email inconnu retourne 401."""
        response = self.client.post(self.url, {
            'email':    'inconnu@example.com',
            'password': 'SecurePass123!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MeViewTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url    = reverse('authentication:me')
        self.user   = User.objects.create_user(
            email='test@example.com',
            password='SecurePass123!',
            first_name='John',
            last_name='Doe'
        )

    def test_get_profile_authenticated(self):
        """Utilisateur connecté peut voir son profil."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'test@example.com')

    def test_get_profile_unauthenticated(self):
        """Utilisateur non connecté reçoit 401."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)