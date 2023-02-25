import re

from django.core import mail
from django.urls import reverse

from rest_framework.test import APITestCase

from asu.auth.models import User
from asu.verification.models import RegistrationVerification


class RegistrationTest(APITestCase):
    """
    Test the entire registration process.
    """

    def test_registration(self):
        test_backend = "django.core.mail.backends.locmem.EmailBackend"
        url_check = reverse("api:registration-verification-check")
        url_send = reverse("api:registration-verification-list")
        url_register = reverse("api:user-list")
        email = "test@example.com"

        # Send code to e-mail
        with self.settings(EMAIL_BACKEND=test_backend):
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                send_response = self.client.post(
                    url_send, data={"email": email}
                )
            self.assertEqual(201, send_response.status_code)
            self.assertEqual(1, len(mail.outbox))
            self.assertEqual(1, len(callbacks))
            (code,) = re.findall(r"[\d]{6}", mail.outbox[0].body)

        # Check and verify the combination, get consent
        check_response = self.client.post(
            url_check, data={"email": email, "code": code}
        )
        self.assertEqual(200, check_response.status_code)
        consent = check_response.data["consent"]

        register_data = {
            "email": email,
            "consent": consent,
            "display_name": "Janet",
            "username": "janet_52",
            "gender": "female",
            "birth_date": "2000-01-01",
        }

        # Fail password validation
        fail_response = self.client.post(
            url_register,
            data={**register_data, "password": 123},
        )
        self.assertContains(fail_response, "too common", status_code=400)

        # Create the actual user
        register_response = self.client.post(
            url_register,
            data={
                **register_data,
                "password": "very_secret",
            },
        )
        self.assertEqual(201, register_response.status_code)

        # Let's make sure everything is in the database.
        user = User.objects.get(email=email)
        verification = RegistrationVerification.objects.get(user=user)
        self.assertFalse(verification.is_eligible)
        self.assertIsNotNone(verification.date_completed)
