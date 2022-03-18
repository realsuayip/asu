import re

from django.core import mail
from django.urls import reverse

from rest_framework.test import APITestCase

from zeynep.auth.models import User
from zeynep.verification.models import RegistrationVerification


class RegistrationTest(APITestCase):
    """
    Test the entire registration process.
    """

    def test_registration(self):
        test_backend = "django.core.mail.backends.locmem.EmailBackend"
        url_check = reverse("registration-verification-check")
        url_send = reverse("registration-verification-list")
        url_register = reverse("user-list")
        email = "test@example.com"

        # Send code to e-mail
        with self.settings(EMAIL_BACKEND=test_backend):
            send_response = self.client.post(url_send, data={"email": email})
            self.assertEqual(201, send_response.status_code)
            self.assertEqual(1, len(mail.outbox))
            (code,) = re.findall(r"[\d]{6}", mail.outbox[0].body)

        # Check and verify the combination, get consent
        check_response = self.client.post(
            url_check, data={"email": email, "code": code}
        )
        self.assertEqual(200, check_response.status_code)
        consent = check_response.data["consent"]

        # Create the actual user
        register_response = self.client.post(
            url_register,
            data={
                "email": email,
                "consent": consent,
                "display_name": "Janet",
                "username": "janet_52",
                "password": "very_secret",
                "gender": "female",
                "birth_date": "2000-01-01",
            },
        )
        self.assertEqual(201, register_response.status_code)

        # Let's make sure everything is in the database.
        user = User.objects.get(email=email)
        verification = RegistrationVerification.objects.get(user=user)
        self.assertFalse(verification.is_eligible)
        self.assertIsNotNone(verification.date_completed)
