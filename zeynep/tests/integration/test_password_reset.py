import re

from django.core import mail
from django.urls import reverse

from rest_framework.test import APITestCase

from zeynep.tests.factories import UserFactory
from zeynep.verification.models import PasswordResetVerification


class PasswordResetTest(APITestCase):
    """
    Test the entire password reset process.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(email="best@example.com")

    def _send_new_password(self, email, consent, password):
        return self.client.patch(
            reverse("user-reset-password"),
            data={
                "email": email,
                "consent": consent,
                "password": password,
            },
        )

    def test_password_reset(self):
        test_backend = "django.core.mail.backends.locmem.EmailBackend"
        url_check = reverse("password-reset-check")
        url_send = reverse("password-reset-list")
        email = self.user.email

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

        kwargs = {"email": email, "consent": consent}

        # Let's try to send some bad requests first.
        bad_1 = self._send_new_password(**kwargs, password="Janet")
        bad_2 = self._send_new_password(**kwargs, password="1234")
        bad_3 = self._send_new_password(**kwargs, password="best")
        self.assertContains(bad_1, "too short", status_code=400)
        self.assertContains(bad_2, "numeric", status_code=400)
        self.assertContains(bad_2, "too common", status_code=400)
        self.assertContains(bad_3, "similar", status_code=400)

        # Make a valid request to change the password.
        password = "12345678*"
        response = self._send_new_password(**kwargs, password=password)
        self.assertEqual(200, response.status_code)

        # Let's make sure everything is in the database.
        verification = PasswordResetVerification.objects.get(user=self.user)
        self.assertFalse(verification.is_eligible)
        self.assertIsNotNone(verification.date_completed)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(password))
