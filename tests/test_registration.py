import re

from django.core import mail
from django.urls import reverse

from rest_framework.test import APITestCase

from asu.auth.models import User
from asu.verification.models import RegistrationVerification
from tests.factories import first_party_token


class RegistrationTest(APITestCase):
    """
    Test the entire registration process.
    """

    fixtures = ("oauth", "vars")

    def test_registration(self):
        self.client.force_authenticate(token=first_party_token)

        url_check = reverse("api:verification:registration-verification-check")
        url_send = reverse("api:verification:registration-verification-list")
        url_register = reverse("api:auth:user-list")
        email = "test@example.com"

        # Send code to e-mail
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            send_response = self.client.post(url_send, data={"email": email})

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

        # Make sure given access token can be used to authorize the user
        auth = register_response.json()["auth"]
        access_token = auth["access_token"]
        token_type = auth["token_type"]
        authorization = "%s %s" % (token_type, access_token)

        self.client.logout()
        # ^ Disable force_authenticate done above (i.e., server token).
        response = self.client.get(
            reverse("api:auth:user-me"), HTTP_AUTHORIZATION=authorization
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(register_data["username"], response.data["username"])
