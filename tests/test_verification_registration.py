import re
from datetime import timedelta
from unittest import mock

from django.conf import settings
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APITestCase

from asu.verification.models import RegistrationVerification
from tests.factories import UserFactory, first_party_token


class TestRegistrationVerification(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url_send = reverse("api:verification:registration-verification-list")
        cls.url_check = reverse("api:verification:registration-verification-check")

    def test_code_gen(self):
        verification = RegistrationVerification.objects.create(
            email="world@exmaple.com"
        )

        self.assertEqual(6, len(verification.code))
        self.assertTrue(verification.code.isdigit())

    def test_send(self):
        self.client.force_authenticate(token=first_party_token)
        email = "patato@example.com"

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            self.client.post(self.url_send, data={"email": email})
        self.assertEqual(1, len(callbacks))
        (code,) = re.findall(r"[\d]{6}", mail.outbox[0].body)

        verification = RegistrationVerification.objects.get(code=code, email=email)

        self.assertFalse(verification.is_eligible)
        self.assertIsNone(verification.user)
        self.assertIsNone(verification.date_completed)

        with self.assertRaises(AssertionError):
            verification.create_consent()

    def test_send_case_exists(self):
        self.client.force_authenticate(token=first_party_token)

        email_taken = "hello@example.com"
        UserFactory(email=email_taken)

        response = self.client.post(self.url_send, data={"email": email_taken})
        self.assertContains(response, "e-mail is already in use", status_code=400)

    def test_send_case_exists_case_insensitive(self):
        self.client.force_authenticate(token=first_party_token)

        UserFactory(email="Hello.World@example.com")

        response = self.client.post(
            self.url_send, data={"email": "hello.world@example.com"}
        )
        self.assertContains(response, "e-mail is already in use", status_code=400)

    def test_check(self):
        self.client.force_authenticate(token=first_party_token)

        email = "worldt@exmaple.com"
        verification = RegistrationVerification.objects.create(email=email)

        # Check non-matching
        invalid = self.client.post(
            self.url_check,
            {"email": email, "code": "000000"},
        )
        self.assertEqual(404, invalid.status_code)

        # Check valid
        payload = {"email": email, "code": verification.code}
        valid = self.client.post(self.url_check, payload)
        verification.refresh_from_db()
        self.assertEqual(200, valid.status_code)
        self.assertContains(valid, "consent")
        self.assertTrue(verification.is_eligible)
        self.assertIsNotNone(verification.date_verified)
        self.assertIsNone(verification.date_completed)

        # Resend to confirm that it is no more valid
        resend = self.client.post(self.url_check, payload)
        self.assertEqual(404, resend.status_code)

    def test_check_case_expired(self):
        self.client.force_authenticate(token=first_party_token)

        period = settings.REGISTRATION_VERIFY_PERIOD + 10
        expired_create = timezone.now() - timedelta(seconds=period)
        email = "worldz@exmaple.com"

        with mock.patch(
            "django.utils.timezone.now",
            return_value=expired_create,
        ):
            verification = RegistrationVerification.objects.create(email=email)

        response = self.client.post(
            self.url_check,
            {"email": email, "code": verification.code},
        )
        self.assertEqual(404, response.status_code)

    def test_check_consent_matching(self):
        email = "janet@example.com"
        verification = RegistrationVerification.objects.create(
            email=email, date_verified=timezone.now()
        )
        actual = RegistrationVerification.objects.get_with_consent(
            email, verification.create_consent()
        )
        self.assertEqual(verification, actual)

    def test_check_case_bad_code(self):
        self.client.force_authenticate(token=first_party_token)

        response = self.client.post(
            self.url_check,
            {"email": "test@example.com", "code": "AB132"},
        )
        self.assertContains(response, text="at least 6 digits", status_code=400)
        self.assertContains(response, text="only digits", status_code=400)

    def test_get_with_consent(self):
        period = settings.REGISTRATION_REGISTER_PERIOD + 10
        email = "janet2@example.com"

        # Create a verified registration
        verification = RegistrationVerification.objects.create(
            email=email, date_verified=timezone.now()
        )
        consent = verification.create_consent()

        # Expire the verification date
        verification.date_verified = timezone.now() - timedelta(seconds=period)
        verification.save(update_fields=["date_verified"])

        # Should return nothing
        actual = RegistrationVerification.objects.get_with_consent(email, consent)
        self.assertIsNone(actual)
