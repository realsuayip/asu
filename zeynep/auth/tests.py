from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APITestCase

from zeynep.verification.models import RegistrationVerification


class TestAuth(APITestCase):
    def setUp(self):
        self.url_create = reverse("user-list")
        self.create_payload = {
            "display_name": "Janet",
            "username": "janet_48",
            "password": "very_secret",
            "gender": "female",
            "birth_data": "1999-02-02",
        }

    def test_user_create_invalid_consent_case_1(self):
        email = "janet@example.com"
        verification = RegistrationVerification.objects.create(
            email=email, date_verified=timezone.now()
        )

        payload = {
            **self.create_payload,
            "email": email,
            "consent": verification.create_consent() + "z",
        }
        response = self.client.post(self.url_create, data=payload)

        self.assertContains(
            response,
            "e-mail could not be verified",
            status_code=400,
        )

    def test_user_create_invalid_consent_case_2(self):
        response = self.client.post(
            self.url_create,
            data={
                **self.create_payload,
                "email": "janet@example.com",
                "consent": "random_stuff",
            },
        )
        self.assertContains(
            response,
            "e-mail could not be verified",
            status_code=400,
        )
