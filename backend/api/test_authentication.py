from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase


class AuthenticationTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='operator', password='correct-horse-battery-staple',
            email='operator@example.com', first_name='Monicah',
        )

    def test_login_returns_token_and_user(self):
        response = self.client.post(reverse('auth-login'), {
            'username': 'operator', 'password': 'correct-horse-battery-staple',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['token'])
        self.assertEqual(response.data['user']['display_name'], 'Monicah')

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {response.data['token']}")
        self.assertEqual(self.client.get(reverse('auth-me')).status_code, 200)
        self.assertEqual(self.client.post(reverse('auth-logout')).status_code, 204)
        self.assertEqual(self.client.get(reverse('auth-me')).status_code, 401)

    def test_invalid_login_and_anonymous_api_access_are_rejected(self):
        response = self.client.post(reverse('auth-login'), {
            'username': 'operator', 'password': 'wrong-password',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get(reverse('vendor-leads')).status_code, 401)
