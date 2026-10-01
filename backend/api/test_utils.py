from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase


class AuthenticatedAPITestCase(APITestCase):
    def setUp(self):
        self.auth_user = get_user_model().objects.create_user(
            username=f'test-user-{self.__class__.__name__.lower()}',
            password='test-password-12345',
        )
        self.client.force_authenticate(self.auth_user)
