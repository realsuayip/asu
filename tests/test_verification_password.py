from django.urls import reverse

from rest_framework.test import APITestCase

from asu.verification.models import PasswordResetVerification
from tests.factories import UserFactory, first_party_token


class TestPasswordReset(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url_send = reverse("api:password-reset-list")
        cls.url_check = reverse("api:password-reset-check")
        cls.url_change = reverse("api:user-reset-password")

    def test_check_nullification(self):
        self.client.force_authenticate(token=first_party_token)

        email = "null_test@example.com"
        UserFactory(email=email)

        # Create & get verifications
        for _ in range(3):
            self.client.post(self.url_send, data={"email": email})

        v1, v2, v3 = verifications = tuple(
            PasswordResetVerification.objects.filter(email=email).order_by("id")
        )
        consents = []

        # Get consents
        for verification in verifications:
            verify_response = self.client.post(
                self.url_check,
                {"email": verification.email, "code": verification.code},
            )
            consents.append(verify_response.data["consent"])
        c1, c2, c3 = consents

        # Reset the password
        reset_response = self.client.patch(
            self.url_change,
            data={
                "email": email,
                "password": "12345678*",
                "consent": c2,
            },
        )
        self.assertEqual(200, reset_response.status_code)

        # Now, subsequent reset requests should fail
        for consent in (c1, c3):
            response = self.client.patch(
                self.url_change,
                data={
                    "email": email,
                    "password": "12345678*",
                    "consent": consent,
                },
            )
            self.assertContains(
                response,
                "e-mail could not be verified",
                status_code=400,
            )

        # Let's make sure nulled_by is set correct
        v1.refresh_from_db()
        v2.refresh_from_db()
        v3.refresh_from_db()
        self.assertEqual(v2, v1.nulled_by)
        self.assertEqual(v2, v3.nulled_by)
        self.assertIsNone(v2.nulled_by_id)

        # Now let's make another valid password reset, this shouldn't
        # affect verification 2 as it is used already.
        self.client.post(self.url_send, data={"email": email})
        v4 = PasswordResetVerification.objects.latest("id")
        check_4 = self.client.post(self.url_check, {"email": email, "code": v4.code})
        response_4 = self.client.patch(
            self.url_change,
            data={
                "email": email,
                "password": "12345678*",
                "consent": check_4.data["consent"],
            },
        )
        self.assertEqual(200, response_4.status_code)

        v2.refresh_from_db()
        self.assertIsNone(v2.nulled_by_id)

    def test_reset_invalid_email(self):
        self.client.force_authenticate(token="UserNotRequired")

        response = self.client.patch(
            self.url_change,
            data={
                "email": "nonexistent@example.com",
                "consent": "abc",
                "password": "1234567890*",
            },
        )
        self.assertEqual(404, response.status_code)

    def test_create_invalid_email_ok(self):
        self.client.force_authenticate(token=first_party_token)

        response = self.client.post(
            self.url_send, data={"email": "nonexistent123@example.com"}
        )
        self.assertEqual(201, response.status_code)
