from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APITestCase

from zeynep.tests.factories import UserFactory
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
        self.user1 = UserFactory()
        self.user2 = UserFactory()

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

    def test_follow_basic(self):
        self.client.force_login(self.user1)

        # Follow
        response = self.client.post(
            reverse(
                "user-follow",
                kwargs={"username": self.user2.username},
            )
        )
        self.assertEqual(204, response.status_code)
        self.assertTrue(self.user1.following.filter(pk=self.user2.pk).exists())

        # Unfollow
        response2 = self.client.post(
            reverse(
                "user-unfollow",
                kwargs={"username": self.user2.username},
            )
        )
        self.assertEqual(204, response2.status_code)
        self.assertFalse(
            self.user1.following.filter(pk=self.user2.pk).exists()
        )

    def test_follow_subsequent_ok(self):
        self.client.force_login(self.user2)

        response1 = self.client.post(
            reverse(
                "user-follow",
                kwargs={"username": self.user1.username},
            )
        )
        response2 = self.client.post(
            reverse(
                "user-follow",
                kwargs={"username": self.user1.username},
            )
        )
        self.assertEqual(204, response1.status_code)
        self.assertEqual(204, response2.status_code)
        self.assertTrue(self.user2.following.filter(pk=self.user1.pk).exists())

    def _test_follows_fails_if(self, a, b):
        # user1 sends the follow request, blockage direction
        # is swapped via a, b (user1, user2) (user2, user1)
        self.client.force_login(self.user1)

        a.blocked.add(b)
        response = self.client.post(
            reverse(
                "user-follow",
                kwargs={"username": self.user2.username},
            )
        )
        self.assertEqual(403, response.status_code)
        self.assertFalse(
            self.user1.following.filter(pk=self.user2.pk).exists()
        )

    def test_follow_fails_if_blocked(self):
        self._test_follows_fails_if(self.user1, self.user2)

    def test_follow_fails_if_blocked_by(self):
        self._test_follows_fails_if(self.user2, self.user1)

    def test_self_follow_not_allowed(self):
        self.client.force_login(self.user1)
        response = self.client.post(
            reverse(
                "user-follow",
                kwargs={"username": self.user1.username},
            )
        )
        self.assertEqual(403, response.status_code)

    def test_block_basic(self):
        self.client.force_login(self.user1)

        # Block
        response = self.client.post(
            reverse(
                "user-block",
                kwargs={"username": self.user2.username},
            )
        )
        self.assertEqual(204, response.status_code)
        self.assertTrue(self.user1.blocked.filter(pk=self.user2.pk).exists())

        # Unblock
        response = self.client.post(
            reverse(
                "user-unblock",
                kwargs={"username": self.user2.username},
            )
        )
        self.assertEqual(204, response.status_code)
        self.assertFalse(self.user1.blocked.filter(pk=self.user2.pk).exists())

    def test_block_subsequent_ok(self):
        self.client.force_login(self.user2)

        response1 = self.client.post(
            reverse(
                "user-block",
                kwargs={"username": self.user1.username},
            )
        )
        response2 = self.client.post(
            reverse(
                "user-block",
                kwargs={"username": self.user1.username},
            )
        )
        self.assertEqual(204, response1.status_code)
        self.assertEqual(204, response2.status_code)
        self.assertTrue(self.user2.blocked.filter(pk=self.user1.pk).exists())

    def _test_block_removes_follows(self, a, b):
        self.client.force_login(self.user1)

        a.following.add(b)
        response = self.client.post(
            reverse(
                "user-block",
                kwargs={"username": self.user2.username},
            )
        )
        self.assertEqual(204, response.status_code)
        self.assertFalse(a.following.filter(pk=b.pk).exists())

    def test_block_removes_following(self):
        self._test_block_removes_follows(self.user1, self.user2)

    def test_block_removes_followed_by(self):
        self._test_block_removes_follows(self.user2, self.user1)

    def test_self_block_not_allowed(self):
        self.client.force_login(self.user1)
        response = self.client.post(
            reverse(
                "user-block",
                kwargs={"username": self.user1.username},
            )
        )
        self.assertEqual(403, response.status_code)
