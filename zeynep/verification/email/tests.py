import re
from unittest import mock

from django.apps import apps
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APITestCase

from zeynep.tests.factories import UserFactory
from zeynep.verification.models import EmailVerification


class TestRegistrationVerification(APITestCase):
    def setUp(self):
        self.url_send = reverse("email-verification-list")
        self.url_check = reverse("email-verification-check")

    def test_email_verification(self):
        # Test email verification as whole
        email = "patato@example.com"
        user = UserFactory(email="old_patato@example.com")
        test_backend = "django.core.mail.backends.locmem.EmailBackend"

        self.client.force_login(user)

        # Send code to email and parse it
        with self.settings(EMAIL_BACKEND=test_backend):
            self.client.post(self.url_send, data={"email": email})
            (code,) = re.findall(r"[\d]{6}", mail.outbox[0].body)

        # Check EmailVerification has related user assigned
        verification = EmailVerification.objects.get()
        self.assertEqual(user, verification.user)

        # Use code to change email
        response = self.client.post(
            self.url_check, data={"email": email, "code": code}
        )
        self.assertContains(response, email, status_code=200)

        # Check if email changed
        user.refresh_from_db()
        self.assertEqual(email, user.email)

    def test_send_case_exists(self):
        taken = "janet2@example.com"
        UserFactory(email=taken)
        user = UserFactory(email="janet@example.com")

        self.client.force_login(user)
        response = self.client.post(self.url_send, data={"email": taken})
        self.assertContains(
            response,
            "e-mail is already in use",
            status_code=400,
        )

    def test_check_case_expired(self):
        self.client.force_login(UserFactory(email="old@exmaple.com"))

        config = apps.get_app_config("verification")
        period = config.EMAIL_VERIFY_PERIOD + 10
        expired_create = timezone.now() - timezone.timedelta(seconds=period)
        email = "new@exmaple.com"

        with mock.patch(
            "django.utils.timezone.now",
            return_value=expired_create,
        ):
            verification = EmailVerification.objects.create(email=email)

        response = self.client.post(
            self.url_check,
            {"email": email, "code": verification.code},
        )
        self.assertEqual(404, response.status_code)
