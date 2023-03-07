import re
from unittest import mock

from django.conf import settings
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APITestCase

from asu.tests.factories import UserFactory
from asu.verification.models import EmailVerification


class TestEmailVerification(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url_send = reverse("api:email-verification-list")
        cls.url_check = reverse("api:email-verification-check")

    def test_email_verification(self):
        # Test email verification as whole
        email = "patato@example.com"
        user = UserFactory(email="old_patato@example.com")
        test_backend = "django.core.mail.backends.locmem.EmailBackend"

        self.client.force_login(user)

        # Send code to email and parse it
        with self.settings(EMAIL_BACKEND=test_backend):
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                self.client.post(self.url_send, data={"email": email})
            self.assertEqual(1, len(callbacks))
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

        period = settings.EMAIL_VERIFY_PERIOD + 10
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

    def test_check_nullification(self):
        email1 = "patato@example.com"
        email2 = "tomato@example.com"
        email3 = "carrot@example.com"
        user = UserFactory(email="hello@example.com")

        self.client.force_login(user)

        # Send verifications to three different emails.
        self.client.post(self.url_send, data={"email": email1})
        self.client.post(self.url_send, data={"email": email2})
        self.client.post(self.url_send, data={"email": email3})

        verification1 = EmailVerification.objects.get(email=email1)
        verification2 = EmailVerification.objects.get(email=email2)
        verification3 = EmailVerification.objects.get(email=email3)

        # Change email to "email2" first.
        self.client.post(
            self.url_check,
            data={"email": email2, "code": verification2.code},
        )

        # Let's see if the other verifications
        # can be used --they shouldn't--
        response1 = self.client.post(
            self.url_check,
            data={"email": email1, "code": verification1.code},
        )
        response3 = self.client.post(
            self.url_check,
            data={"email": email3, "code": verification3.code},
        )
        self.assertEqual(404, response1.status_code)
        self.assertEqual(404, response3.status_code)

        # Let's also check nulled_by is correct.
        verification3.refresh_from_db()
        verification2.refresh_from_db()
        verification1.refresh_from_db()
        self.assertEqual(verification2, verification1.nulled_by)
        self.assertEqual(verification2, verification3.nulled_by)
        self.assertIsNone(verification2.nulled_by_id)

        # Change email once again, to ensure
        # "verification2" is not nulled
        email4 = "onion@example.com"
        self.client.post(self.url_send, data={"email": email4})
        verification4 = EmailVerification.objects.get(email=email4)
        response4 = self.client.post(
            self.url_check,
            data={"email": email4, "code": verification4.code},
        )
        self.assertEqual(200, response4.status_code)
        self.assertIsNone(verification2.nulled_by_id)
