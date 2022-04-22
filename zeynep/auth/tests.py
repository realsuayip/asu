from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APITestCase

from zeynep.auth.models import UserFollowRequest
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
        self.private_user = UserFactory(is_private=True)
        self.inactive_user = UserFactory(is_active=False)
        self.frozen_user = UserFactory(is_frozen=True)

    def _compare_instance_to_dict(self, instance, dictionary, *, exclude):
        for item in exclude:
            dictionary.pop(item)

        for key, value in dictionary.items():
            self.assertEqual(
                getattr(instance, key),
                value,
                msg="mismatch on '%s'" % key,
            )

    def test_me(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse("user-me"))
        self.assertEqual(200, response.status_code)
        detail = response.json()

        self._compare_instance_to_dict(
            self.user1,
            detail,
            exclude=["url", "date_joined"],
        )

    def test_me_update(self):
        self.client.force_login(self.user2)
        response = self.client.patch(
            reverse("user-me"),
            data={
                "display_name": "__Potato__",
                "description": "Lorem ipsum",
            },
        )
        detail = response.json()

        self.user2.refresh_from_db()
        self._compare_instance_to_dict(
            self.user2,
            detail,
            exclude=["url", "date_joined", "birth_date"],
        )

    def test_me_update_disallow_email(self):
        email = "hello@example.com"
        self.client.force_login(self.user1)
        self.client.patch(reverse("user-me"), data={"email": email})
        self.user1.refresh_from_db()
        self.assertNotEqual(email, self.user1)

    def test_detail(self):
        response = self.client.get(
            reverse(
                "user-detail",
                kwargs={"username": self.user1.username},
            )
        )
        detail = response.json()

        self.assertIn("follower_count", detail)
        self.assertIn("following_count", detail)

        self._compare_instance_to_dict(
            self.user1,
            detail,
            exclude=[
                "follower_count",
                "following_count",
                "url",
                "date_joined",
            ],
        )

    def test_detail_returns_200_when_blocked(self):
        self.user1.blocked.add(self.user2)
        self.client.force_login(self.user1)

        response = self.client.get(
            reverse(
                "user-detail",
                kwargs={"username": self.user2.username},
            )
        )
        self.assertEqual(200, response.status_code)

    def test_detail_returns_404_when_blocked_by(self):
        self.user1.blocked.add(self.user2)
        self.client.force_login(self.user2)

        response = self.client.get(
            reverse(
                "user-detail",
                kwargs={"username": self.user1.username},
            )
        )
        self.assertEqual(404, response.status_code)

    def test_detail_excludes_frozen_or_inactive(self):
        frozen = self.client.get(
            reverse(
                "user-detail",
                kwargs={"username": self.frozen_user.username},
            )
        )
        inactive = self.client.get(
            reverse(
                "user-detail",
                kwargs={"username": self.inactive_user.username},
            )
        )
        self.assertEqual(404, frozen.status_code)
        self.assertEqual(404, inactive.status_code)

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

    def _test_follow_subsequent_ok(self, user1, user2):
        self.client.force_login(user2)

        response1 = self.client.post(
            reverse(
                "user-follow",
                kwargs={"username": user1.username},
            )
        )
        response2 = self.client.post(
            reverse(
                "user-follow",
                kwargs={"username": user1.username},
            )
        )
        self.assertEqual(204, response1.status_code)
        self.assertEqual(204, response2.status_code)

    def test_follow_subsequent_ok(self):
        self._test_follow_subsequent_ok(self.user1, self.user2)
        self.assertEqual(
            1, self.user2.following.filter(pk=self.user1.pk).count()
        )

    def test_follow_subsequent_ok_private(self):
        self._test_follow_subsequent_ok(self.private_user, self.user2)
        self.assertEqual(
            1,
            UserFollowRequest.objects.filter(
                from_user=self.user2, to_user=self.private_user
            ).count(),
        )

    def test_follow_request_accept_whole(self):
        # Send follow request
        self.client.force_login(self.user1)
        self.client.post(
            reverse(
                "user-follow",
                kwargs={"username": self.private_user.username},
            )
        )
        self.assertFalse(self.user1.following.filter(pk=self.private_user.pk))

        # Switch to recipient, check follow request list
        self.client.force_login(self.private_user)
        response = self.client.get(reverse("follow-request-list"))
        data = response.json()
        results = data["results"]
        self.assertEqual(1, len(results))

        # Approve request
        detail = results[0]["url"]
        approved_response = self.client.patch(
            detail, data={"status": "approved"}
        )
        self.assertEqual(200, approved_response.status_code)

        # Make sure the follow request is gone
        subsequent_response = self.client.patch(
            detail, data={"status": "approved"}
        )
        self.assertEqual(404, subsequent_response.status_code)

        # Verify that sender follows the user now.
        self.assertTrue(
            self.user1.following.filter(pk=self.private_user.pk).exists()
        )
        self.assertEqual(
            1,
            UserFollowRequest.objects.filter(
                status="approved",
                from_user=self.user1,
                to_user=self.private_user,
            ).count(),
        )

    def test_follow_request_reject(self):
        self.client.force_login(self.user1)
        self.client.post(
            reverse(
                "user-follow",
                kwargs={"username": self.private_user.username},
            )
        )

        self.client.force_login(self.private_user)
        response = self.client.get(reverse("follow-request-list"))
        detail = response.json()["results"][0]["url"]

        rejected_response = self.client.patch(
            detail, data={"status": "rejected"}
        )
        self.assertEqual(200, rejected_response.status_code)
        self.assertFalse(
            self.user1.following.filter(pk=self.private_user.pk).exists()
        )
        self.assertEqual(
            1,
            UserFollowRequest.objects.filter(
                status="rejected",
                from_user=self.user1,
                to_user=self.private_user,
            ).count(),
        )

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
