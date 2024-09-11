import datetime
import io
import zoneinfo
from datetime import timedelta
from unittest import mock

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.db import IntegrityError, connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APITestCase

from PIL import Image

from asu.auth.models import (
    AccessToken,
    Application,
    RefreshToken,
    Session,
    TOTPDevice,
    User,
    UserBlock,
    UserDeactivation,
    UserFollowRequest,
)
from asu.auth.sessions.cached_db import KEY_PREFIX
from asu.auth.tasks import delete_users_permanently
from asu.verification.models import RegistrationVerification
from tests.factories import UserFactory, first_party_token


class TestAuth(APITestCase):
    fixtures = ("oauth", "vars")

    @classmethod
    def setUpTestData(cls):
        cls.url_create = reverse("api:auth:user-list")
        cls.create_payload = {
            "display_name": "Janet",
            "username": "janet_48",
            "password": "very_secret",
            "gender": "female",
            "birth_data": "1999-02-02",
        }
        cls.user1 = UserFactory()
        cls.user2 = UserFactory()
        cls.user3 = UserFactory()
        cls.user4 = UserFactory()
        cls.private_user = UserFactory(is_private=True)
        cls.inactive_user = UserFactory(is_active=False)
        cls.frozen_user = UserFactory(is_frozen=True)

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
        response = self.client.get(reverse("api:auth:user-me"))
        self.assertEqual(200, response.status_code)
        detail = response.json()

        self._compare_instance_to_dict(
            self.user1,
            detail,
            exclude=["profile_picture", "url", "date_joined"],
        )

    def test_me_update(self):
        self.client.force_login(self.user2)
        response = self.client.patch(
            reverse("api:auth:user-me"),
            data={
                "display_name": "__Potato__",
                "description": "Lorem ipsum",
            },
        )
        detail = response.json()
        self.assertEqual("__Potato__", detail["display_name"])
        self.assertEqual("Lorem ipsum", detail["description"])

        self.user2.refresh_from_db()
        self._compare_instance_to_dict(
            self.user2,
            detail,
            exclude=["profile_picture", "url", "date_joined", "birth_date"],
        )

    def test_me_update_username_taken(self):
        UserFactory(username="suzie")

        self.client.force_login(self.user2)
        response = self.client.patch(
            reverse("api:auth:user-me"),
            data={"username": "Suzie"},
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(
            {"username": ["The username you specified is already in use."]},
            response.json()["errors"],
        )

    def test_me_update_disallow_email(self):
        email = "hello@example.com"
        self.client.force_login(self.user1)
        self.client.patch(reverse("api:auth:user-me"), data={"email": email})
        self.user1.refresh_from_db()
        self.assertNotEqual(email, self.user1)

    def test_detail(self):
        self.client.force_authenticate(token=first_party_token)

        response = self.client.get(
            reverse(
                "api:auth:user-detail",
                kwargs={"pk": self.user1.pk},
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
                "profile_picture",
            ],
        )

    def test_detail_self(self):
        self.client.force_login(self.user1)

        with CaptureQueriesContext(connection) as context:
            response = self.client.get(
                reverse(
                    "api:auth:user-detail",
                    kwargs={"pk": self.user1.pk},
                )
            )

        user_queries = [
            query
            for query in context.captured_queries
            if '"account_user"."username"' in query["sql"]
        ]

        self.assertEqual(1, len(user_queries))
        self.assertEqual(200, response.status_code)

    def test_detail_follow_counts(self):
        self.client.force_login(self.user1)

        self.user1.following.add(self.user2)
        self.user1.following.add(self.user3)

        self.user1.followed_by.add(self.user4)

        response = self.client.get(
            reverse(
                "api:auth:user-detail",
                kwargs={"pk": self.user1.pk},
            )
        )
        self.assertEqual(200, response.status_code)

        detail = response.data
        self.assertEqual(1, detail["follower_count"])
        self.assertEqual(2, detail["following_count"])

    def test_detail_returns_200_when_blocked(self):
        self.user1.blocked.add(self.user2)
        self.client.force_login(self.user1)

        response = self.client.get(
            reverse(
                "api:auth:user-detail",
                kwargs={"pk": self.user2.pk},
            )
        )
        self.assertEqual(200, response.status_code)

    def test_detail_returns_200_when_blocked_by(self):
        self.user1.blocked.add(self.user2)
        self.client.force_login(self.user2)

        response = self.client.get(
            reverse(
                "api:auth:user-detail",
                kwargs={"pk": self.user1.pk},
            )
        )
        self.assertEqual(200, response.status_code)

    def test_detail_excludes_frozen_or_inactive(self):
        self.client.force_authenticate(token=first_party_token)

        frozen = self.client.get(
            reverse(
                "api:auth:user-detail",
                kwargs={"pk": self.frozen_user.pk},
            )
        )
        inactive = self.client.get(
            reverse(
                "api:auth:user-detail",
                kwargs={"pk": self.inactive_user.pk},
            )
        )
        self.assertEqual(404, frozen.status_code)
        self.assertEqual(404, inactive.status_code)

    def test_by(self):
        # Since the `test_detail_*` cases uses the common code,
        # only testing the sanity of this endpoint here.
        self.client.force_authenticate(token=first_party_token)

        response = self.client.get(
            reverse("api:auth:user-lookup"),
            {"username": self.user2.username},
        )

        self.assertEqual(200, response.status_code)
        self.assertContains(response, "follower_count")
        self.assertContains(response, "following_count")
        self._compare_instance_to_dict(
            self.user2,
            response.json(),
            exclude=[
                "follower_count",
                "following_count",
                "url",
                "date_joined",
                "profile_picture",
            ],
        )

    def test_by_query_param_required(self):
        self.client.force_authenticate(token=first_party_token)
        response = self.client.get(reverse("api:auth:user-lookup"))

        self.assertEqual(400, response.status_code)
        self.assertEqual(
            {"username": ["This field is required."]},
            response.json()["errors"],
        )

    def test_by_case_not_found(self):
        self.client.force_authenticate(token=first_party_token)
        response = self.client.get(
            reverse("api:auth:user-lookup"),
            {"username": self.inactive_user.username},
        )
        self.assertEqual(404, response.status_code)

    def test_user_create_invalid_consent_case_1(self):
        self.client.force_authenticate(token=first_party_token)

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
        self.client.force_authenticate(token=first_party_token)

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
                "api:auth:user-follow",
                kwargs={"pk": self.user2.pk},
            )
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual("following", response.data["status"])
        self.assertTrue(self.user1.following.filter(pk=self.user2.pk).exists())

        # Unfollow
        response2 = self.client.post(
            reverse(
                "api:auth:user-unfollow",
                kwargs={"pk": self.user2.pk},
            )
        )
        self.assertEqual(204, response2.status_code)
        self.assertFalse(self.user1.following.filter(pk=self.user2.pk).exists())

    def test_follow_private(self):
        self.client.force_login(self.user1)

        response = self.client.post(
            reverse(
                "api:auth:user-follow",
                kwargs={"pk": self.private_user.pk},
            )
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual("follow_request_sent", response.data["status"])
        self.assertFalse(self.user1.following.filter(pk=self.private_user.pk).exists())
        self.assertEqual(
            1,
            UserFollowRequest.objects.filter(
                from_user=self.user1, to_user=self.private_user
            ).count(),
        )

    def _test_follow_subsequent_ok(self, user1, user2):
        self.client.force_login(user2)

        response1 = self.client.post(
            reverse(
                "api:auth:user-follow",
                kwargs={"pk": user1.pk},
            )
        )
        response2 = self.client.post(
            reverse(
                "api:auth:user-follow",
                kwargs={"pk": user1.pk},
            )
        )
        self.assertEqual(200, response1.status_code)
        self.assertEqual(200, response2.status_code)

    def test_follow_subsequent_ok(self):
        self._test_follow_subsequent_ok(self.user1, self.user2)
        self.assertEqual(1, self.user2.following.filter(pk=self.user1.pk).count())

    def test_follow_subsequent_ok_private(self):
        self._test_follow_subsequent_ok(self.private_user, self.user2)
        self.assertEqual(
            1,
            UserFollowRequest.objects.filter(
                from_user=self.user2, to_user=self.private_user
            ).count(),
        )

    def test_follow_subsequent_ok_private_case_already_following(self):
        self.user2.add_following(to_user=self.private_user)
        self._test_follow_subsequent_ok(self.private_user, self.user2)
        self.assertEqual(
            0,
            UserFollowRequest.objects.filter(
                from_user=self.user2, to_user=self.private_user
            ).count(),
        )

    def test_follow_request_accept_whole(self):
        # Send follow request
        self.client.force_login(self.user1)
        self.client.post(
            reverse(
                "api:auth:user-follow",
                kwargs={"pk": self.private_user.pk},
            )
        )
        self.assertFalse(self.user1.following.filter(pk=self.private_user.pk))

        # Switch to recipient, check follow request list
        self.client.force_login(self.private_user)
        response = self.client.get(reverse("api:auth:follow-request-list"))
        data = response.json()
        results = data["results"]
        self.assertEqual(1, len(results))

        # Approve request
        detail = results[0]["url"]
        approved_response = self.client.patch(detail, data={"status": "approved"})
        self.assertEqual(200, approved_response.status_code)

        # Make sure the follow request is gone
        subsequent_response = self.client.patch(detail, data={"status": "approved"})
        self.assertEqual(404, subsequent_response.status_code)

        # Verify that sender follows the user now.
        self.assertTrue(self.user1.following.filter(pk=self.private_user.pk).exists())
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
                "api:auth:user-follow",
                kwargs={"pk": self.private_user.pk},
            )
        )

        self.client.force_login(self.private_user)
        response = self.client.get(reverse("api:auth:follow-request-list"))
        detail = response.json()["results"][0]["url"]

        rejected_response = self.client.patch(detail, data={"status": "rejected"})
        self.assertEqual(200, rejected_response.status_code)
        self.assertFalse(self.user1.following.filter(pk=self.private_user.pk).exists())
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
                "api:auth:user-follow",
                kwargs={"pk": self.user2.pk},
            )
        )
        self.assertFalse(self.user1.following.filter(pk=self.user2.pk).exists())
        return response

    def test_follow_fails_if_blocked(self):
        response = self._test_follows_fails_if(self.user1, self.user2)
        self.assertEqual(403, response.status_code)

    def test_follow_fails_if_blocked_by(self):
        response = self._test_follows_fails_if(self.user2, self.user1)
        self.assertEqual(403, response.status_code)

    def test_self_follow_not_allowed(self):
        self.client.force_login(self.user1)
        response = self.client.post(
            reverse("api:auth:user-follow", kwargs={"pk": self.user1.pk})
        )
        self.assertEqual(403, response.status_code)

    def test_block_basic(self):
        self.client.force_login(self.user1)

        # Block
        response = self.client.post(
            reverse(
                "api:auth:user-block",
                kwargs={"pk": self.user2.pk},
            )
        )
        self.assertEqual(204, response.status_code)
        self.assertTrue(self.user1.blocked.filter(pk=self.user2.pk).exists())

        # Unblock
        response = self.client.post(
            reverse(
                "api:auth:user-unblock",
                kwargs={"pk": self.user2.pk},
            )
        )
        self.assertEqual(204, response.status_code)
        self.assertFalse(self.user1.blocked.filter(pk=self.user2.pk).exists())

    def test_block_subsequent_ok(self):
        self.client.force_login(self.user2)

        response1 = self.client.post(
            reverse(
                "api:auth:user-block",
                kwargs={"pk": self.user1.pk},
            )
        )
        response2 = self.client.post(
            reverse(
                "api:auth:user-block",
                kwargs={"pk": self.user1.pk},
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
                "api:auth:user-block",
                kwargs={"pk": self.user2.pk},
            )
        )
        self.assertEqual(204, response.status_code)
        self.assertFalse(a.following.filter(pk=b.pk).exists())

    def test_block_removes_following(self):
        self._test_block_removes_follows(self.user1, self.user2)

    def test_block_removes_followed_by(self):
        self._test_block_removes_follows(self.user2, self.user1)

    def _test_block_rejects_follow_request(self, a, b):
        self.client.force_login(self.user1)

        request = UserFollowRequest.objects.create(
            from_user=a, to_user=b, status=UserFollowRequest.Status.PENDING
        )
        response = self.client.post(
            reverse(
                "api:auth:user-block",
                kwargs={"pk": self.user2.pk},
            )
        )

        self.assertEqual(204, response.status_code)

        request.refresh_from_db()
        self.assertEqual(UserFollowRequest.Status.REJECTED, request.status)

    def test_block_rejects_received_follow_request(self):
        self._test_block_rejects_follow_request(self.user1, self.user2)

    def test_block_rejects_sent_follow_request(self):
        self._test_block_rejects_follow_request(self.user2, self.user1)

    def test_block_rejects_only_pending_follow_request(self):
        request = UserFollowRequest.objects.create(
            from_user=self.user2,
            to_user=self.user1,
            status=UserFollowRequest.Status.APPROVED,
        )
        self._test_block_rejects_follow_request(self.user2, self.user1)
        request.refresh_from_db()
        self.assertEqual(UserFollowRequest.Status.APPROVED, request.status)

    def test_self_block_not_allowed(self):
        self.client.force_login(self.user1)
        response = self.client.post(
            reverse(
                "api:auth:user-block",
                kwargs={"pk": self.user1.pk},
            )
        )
        self.assertEqual(403, response.status_code)

    def test_block_allowed_while_being_blocked(self):
        self.client.force_login(self.user1)
        self.client.post(
            reverse(
                "api:auth:user-block",
                kwargs={"pk": self.user2.pk},
            )
        )

        self.client.force_login(self.user2)
        response = self.client.post(
            reverse(
                "api:auth:user-block",
                kwargs={"pk": self.user1.pk},
            )
        )

        self.assertEqual(204, response.status_code)
        self.assertEqual(2, UserBlock.objects.count())

        response = self.client.post(
            reverse(
                "api:auth:user-unblock",
                kwargs={"pk": self.user1.pk},
            )
        )
        self.assertEqual(204, response.status_code)
        self.assertEqual(1, UserBlock.objects.count())

    def _test_action_yields_404(self, url_name):
        self.client.force_login(self.user1)
        response1 = self.client.post(
            reverse(
                url_name,
                kwargs={"pk": "54893573489573498751"},
            )
        )
        response2 = self.client.post(
            reverse(
                url_name,
                kwargs={"pk": self.inactive_user.pk},
            )
        )
        response3 = self.client.post(
            reverse(
                url_name,
                kwargs={"pk": self.frozen_user.pk},
            )
        )
        self.assertEqual(404, response1.status_code)
        self.assertEqual(404, response2.status_code)
        self.assertEqual(404, response3.status_code)

    def test_follow_yields_404(self):
        self._test_action_yields_404("api:auth:user-follow")

    def test_unfollow_yields_404(self):
        self._test_action_yields_404("api:auth:user-unfollow")

    def test_block_yields_404(self):
        self._test_action_yields_404("api:auth:user-block")

    def test_unblock_yields_404(self):
        self._test_action_yields_404("api:auth:user-unblock")

    def _test_get_yields_404(self, url_name):
        self.client.force_authenticate(token=first_party_token)

        response1 = self.client.get(
            reverse(
                url_name,
                kwargs={"pk": "54893573489573498751"},
            )
        )
        response2 = self.client.get(
            reverse(
                url_name,
                kwargs={"pk": self.inactive_user.pk},
            )
        )
        response3 = self.client.get(
            reverse(
                url_name,
                kwargs={"pk": self.frozen_user.pk},
            )
        )
        self.assertEqual(404, response1.status_code)
        self.assertEqual(404, response2.status_code)
        self.assertEqual(404, response3.status_code)

    def test_followers_yields_404(self):
        self._test_get_yields_404("api:auth:user-followers")

    def test_following_yields_404(self):
        self._test_get_yields_404("api:auth:user-following")

    def _assert_valid_user_connections_response(self, response):
        # Should not contain inactive or frozen users. Order is
        # important; latest follows/blocks should appear fist.
        self.assertEqual(
            [self.private_user.id, self.user3.id, self.user2.id],
            [result["id"] for result in response.data["results"]],
        )

    def test_followers(self):
        self.client.force_authenticate(token=first_party_token)

        self.user2.following.add(self.user1)
        self.user3.following.add(self.user1)
        self.private_user.following.add(self.user1)
        self.inactive_user.following.add(self.user1)
        self.frozen_user.following.add(self.user1)

        response = self.client.get(
            reverse(
                "api:auth:user-followers",
                kwargs={"pk": self.user1.pk},
            )
        )
        self._assert_valid_user_connections_response(response)

    def test_following(self):
        self.client.force_authenticate(token=first_party_token)

        self.user1.following.add(self.user2)
        self.user1.following.add(self.user3)
        self.user1.following.add(self.private_user)
        self.user1.following.add(self.inactive_user)
        self.user1.following.add(self.frozen_user)

        response = self.client.get(
            reverse(
                "api:auth:user-following",
                kwargs={"pk": self.user1.pk},
            )
        )
        self._assert_valid_user_connections_response(response)

    def test_followers_respect_privacy(self):
        self.client.force_login(self.user1)
        url = reverse(
            "api:auth:user-followers",
            kwargs={"pk": self.private_user.pk},
        )

        response = self.client.get(url)
        self.assertEqual(403, response.status_code)

        self.user1.add_following(to_user=self.private_user)
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

    def test_following_respect_privacy(self):
        self.client.force_login(self.user1)
        url = reverse(
            "api:auth:user-following",
            kwargs={"pk": self.private_user.pk},
        )

        response = self.client.get(url)
        self.assertEqual(403, response.status_code)

        self.user1.add_following(to_user=self.private_user)
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

    def test_follow_stats_respect_privacy_case_no_user(self):
        self.client.force_authenticate(token=first_party_token)
        followers = self.client.get(
            reverse(
                "api:auth:user-followers",
                kwargs={"pk": self.private_user.pk},
            )
        )
        following = self.client.get(
            reverse(
                "api:auth:user-followers",
                kwargs={"pk": self.private_user.pk},
            )
        )
        self.assertEqual(403, followers.status_code)
        self.assertEqual(403, following.status_code)

    def test_blocked(self):
        self.client.force_login(self.user1)

        self.user1.blocked.add(self.user2)
        self.user1.blocked.add(self.user3)
        self.user1.blocked.add(self.private_user)
        self.user1.blocked.add(self.inactive_user)
        self.user1.blocked.add(self.frozen_user)

        response = self.client.get(reverse("api:auth:user-blocked"))
        self._assert_valid_user_connections_response(response)

    def test_upload_delete_profile_picture(self):
        file_path = settings.BASE_DIR.parent / "tests/files/asli.jpeg"

        self.assertFalse(self.user1.profile_picture.name)
        self.client.force_login(self.user1)

        with open(file_path, "rb") as image:
            response = self.client.put(
                reverse("api:auth:user-profile-picture"),
                data={"profile_picture": image},
            )
        self.assertEqual(200, response.status_code)

        self.user1.refresh_from_db()
        self.assertTrue(self.user1.profile_picture.name)
        self.assertTrue(self.user1.profile_picture.name.endswith(".jpeg"))

        r2 = self.client.delete(reverse("api:auth:user-profile-picture"))
        self.assertEqual(204, r2.status_code)

        self.user1.refresh_from_db()
        self.assertFalse(self.user1.profile_picture.name)

    def test_change_profile_picture(self):
        self.client.force_login(self.user1)

        file_path = settings.BASE_DIR.parent / "tests/files/asli.jpeg"

        with open(file_path, "rb") as file:
            r1 = self.client.put(
                reverse("api:auth:user-profile-picture"),
                data={"profile_picture": file},
            )
            self.assertEqual(200, r1.status_code)

            file.seek(0)
            buf = io.BytesIO()
            image = Image.open(file)
            image = image.convert("RGBA")
            image.save(buf, "PNG")
            picture = ContentFile(buf.getvalue(), name="hello.png")

            r2 = self.client.put(
                reverse("api:auth:user-profile-picture"),
                data={"profile_picture": picture},
            )
            self.assertEqual(200, r2.status_code)

        profile = self.client.get(
            reverse(
                "api:auth:user-detail",
                kwargs={"pk": self.user1.pk},
            )
        )
        profile_picture_url = profile.json()["profile_picture"]
        self.assertIsNotNone(profile_picture_url)
        self.assertTrue(profile_picture_url.endswith("jpg"))

    def test_delete_profile_picture_idempotent(self):
        self.client.force_login(self.user1)

        r = self.client.delete(reverse("api:auth:user-profile-picture"))
        r1 = self.client.delete(reverse("api:auth:user-profile-picture"))

        self.assertEqual(204, r.status_code)
        self.assertEqual(204, r1.status_code)

    def test_revoke_other_tokens(self):
        r1 = self.user1.issue_token()
        r2 = self.user1.issue_token()
        r3 = self.user1.issue_token()

        current = AccessToken.objects.get(token=r3["access_token"])
        self.user1.revoke_other_tokens(current)

        revoke1 = RefreshToken.objects.get(token=r1["refresh_token"])
        revoke2 = RefreshToken.objects.get(token=r2["refresh_token"])
        not_revoked = RefreshToken.objects.get(token=r3["refresh_token"])

        self.assertIsNotNone(revoke1.revoked)
        self.assertIsNotNone(revoke2.revoked)
        self.assertIsNone(not_revoked.revoked)

    def test_revoke_all_sessions(self):
        self.client.force_login(self.user1)
        session_key = self.client.session.session_key

        self.assertTrue(Session.objects.filter(session_key=session_key).exists())

        self.user1.revoke_all_sessions()
        self.assertFalse(Session.objects.filter(session_key=session_key).exists())

    @override_settings(SESSION_ENGINE="asu.auth.sessions.cached_db")
    def test_revoke_all_sessions_case_cached_db(self):
        self.client.force_login(self.user1)
        session_key = self.client.session.session_key

        cached = cache.get(KEY_PREFIX + session_key)
        self.assertIsNotNone(cached)
        self.assertTrue(Session.objects.filter(session_key=session_key).exists())

        self.user1.revoke_all_sessions()
        cached = cache.get(KEY_PREFIX + session_key)
        self.assertFalse(Session.objects.filter(session_key=session_key).exists())
        self.assertIsNone(cached)

    def test_deactivation_unique_constraint(self):
        UserDeactivation.objects.create(user=self.user1, date_revoked=timezone.now())
        UserDeactivation.objects.create(user=self.user1)

        with self.assertRaises(IntegrityError):
            UserDeactivation.objects.create(user=self.user1)

    def test_user_deactivate(self):
        self.user1.set_password("hello")
        self.user1.save(update_fields=["password"])
        token = self.user1.issue_token()
        authorization = f"{token['token_type']} {token['access_token']}"

        url = reverse("api:auth:user-deactivate")

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            response = self.client.post(
                url,
                data={"password": "hello"},
                headers={"Authorization": authorization},
            )

        self.assertEqual(204, response.status_code)
        self.assertIsNone(response.data)
        self.assertEqual(1, len(mail.outbox))
        self.assertEqual(1, len(callbacks))
        self.assertIn("account has been deactivated", mail.outbox[0].body)

        self.user1.refresh_from_db()
        deactivation = UserDeactivation.objects.get(user=self.user1)

        self.assertTrue(self.user1.is_frozen)
        self.assertIsNone(deactivation.date_revoked)
        self.assertFalse(Session.objects.filter(user=self.user1.pk).exists())
        self.assertFalse(AccessToken.objects.exists())
        self.assertFalse(
            RefreshToken.objects.filter(
                user=self.user1,
                revoked__isnull=True,
            ).exists()
        )

    def test_user_deactivate_invalid_password(self):
        self.client.force_login(self.user1)

        url = reverse("api:auth:user-deactivate")
        response = self.client.post(url, data={"password": "hello"})
        self.assertContains(
            response,
            "password was not correct",
            status_code=400,
        )

    def test_user_reactivate(self):
        self.user1.deactivate()
        self.user1.reactivate()
        self.user1.refresh_from_db()

        deactivation = UserDeactivation.objects.get(user=self.user1)

        self.assertIsNotNone(deactivation.date_revoked)
        self.assertFalse(self.user1.is_frozen)

    def test_user_reactivate_by_activity(self):
        # If user is caught logged-in, their account should
        # be activated.
        self.user1.deactivate()
        self.client.force_login(self.user1)

        self.client.get(reverse("api:api-root"))

        self.user1.refresh_from_db()
        self.assertFalse(self.user1.is_frozen)
        self.assertFalse(
            UserDeactivation.objects.filter(
                date_revoked__isnull=True,
            ).exists()
        )

    def test_task_delete_users_permanently(self):
        delete_immediately, to_be_deleted_later, deletion_cancelled = (
            UserFactory(),
            UserFactory(),
            UserFactory(),
        )
        UserFactory()  # unrelated user obj, should not be affected.

        now = datetime.datetime(2022, 1, 1, tzinfo=zoneinfo.ZoneInfo("UTC"))

        # This deactivation will be triggered immediately.
        with mock.patch("django.utils.timezone.now", return_value=now):
            UserDeactivation.objects.create(user=delete_immediately)
            UserDeactivation.objects.create(user=deletion_cancelled, date_revoked=now)

        # This one should not trigger.
        UserDeactivation.objects.create(user=to_be_deleted_later)

        future = now + datetime.timedelta(days=30)
        with mock.patch("django.utils.timezone.now", return_value=future):
            num, objs = delete_users_permanently()

        self.assertEqual(1, objs["account.User"])
        self.assertEqual(2, num)  # `d1` & `delete_immediately`

        with self.assertRaises(User.DoesNotExist):
            delete_immediately.refresh_from_db()

    def test_user_two_factor_enabled_attribute(self):
        self.assertFalse(self.user1.two_factor_enabled)
        del self.user1.two_factor_enabled

        TOTPDevice.objects.create(user=self.user1, confirmed=True)
        self.assertTrue(self.user1.two_factor_enabled)


class TestOAuthPermissions(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = user = UserFactory()

        # First party application with authorization code flow
        first_party = Application.objects.create(
            client_id="first-party",
            client_secret="secret",
            redirect_uris="http://127.0.0.1/local/",
            client_type=Application.CLIENT_PUBLIC,
            authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
            name="First party app",
            is_first_party=True,
        )

        # THIRD party application with authorization code flow
        third_party = Application.objects.create(
            client_id="third-party",
            client_secret="third-secret",
            redirect_uris="http://127.0.0.1/local/",
            client_type=Application.CLIENT_PUBLIC,
            authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
            name="Third party app",
            is_first_party=False,
        )

        # THIRD party application with client credentials flow
        third_party_client_credentials = Application.objects.create(
            client_id="third-party-cc",
            client_secret="third-secret-cc",
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
            name="Third party app with client credentials",
            is_first_party=False,
        )

        AccessToken.objects.bulk_create(
            [
                # FIRST PARTY TOKENS
                AccessToken(
                    user=user,
                    scope="user.profile:read user.profile:write",
                    expires=timezone.now() + timedelta(days=1),
                    token="first-party-token",  # <----
                    application=first_party,
                ),
                AccessToken(
                    user=user,
                    scope="user.profile:read",
                    expires=timezone.now() + timedelta(days=1),
                    token="first-party-token-without-write",  # <----
                    application=first_party,
                ),
                # THIRD PARTY TOKENS
                AccessToken(
                    user=user,
                    scope="user.profile:read",
                    expires=timezone.now() + timedelta(days=1),
                    token="third-party-token",  # <----
                    application=third_party,
                ),
                AccessToken(
                    user=user,
                    scope="user.profile:read user.profile.email:read",
                    expires=timezone.now() + timedelta(days=1),
                    token="third-party-token-with-email",  # <----
                    application=third_party,
                ),
                AccessToken(
                    user=user,
                    scope="user.profile:read user.profile.email:read"
                    " user.profile.private:read",
                    expires=timezone.now() + timedelta(days=1),
                    token="third-party-token-with-private",  # <----
                    application=third_party,
                ),
                AccessToken(
                    user=user,
                    scope="user.profile:read user.profile.private:read",
                    expires=timezone.now() + timedelta(days=1),
                    token="third-party-token-with-private-no-email",  # <----
                    application=third_party,
                ),
                AccessToken(
                    user=user,
                    scope="user.profile:read user.profile.email:read"
                    " user.profile.private:read user.profile:write",
                    expires=timezone.now() + timedelta(days=1),
                    token="third-party-token-with-write",  # <----
                    application=third_party,
                ),
                # THIRD PARTY CLIENT CREDENTIAL FLOW TOKENS
                AccessToken(
                    expires=timezone.now() + timedelta(days=1),
                    scope="user.profile:read",
                    token="third-party-client-credentials",  # <----
                    application=third_party_client_credentials,
                ),
            ]
        )

    def test_require_first_party(self):
        user2 = UserFactory()
        url = reverse(
            "api:auth:user-message",
            kwargs={"pk": user2.pk},
        )

        params = [
            (201, "first-party-token"),
            (403, "third-party-token"),
        ]
        for status_code, token in params:
            response = self.client.post(
                url,
                data={"body": "hello"},
                headers={"Authorization": "Bearer %s" % token},
            )
            self.assertEqual(
                status_code,
                response.status_code,
                msg="used %s" % token,
            )

    def test_require_token(self):
        url = reverse("api:auth:user-detail", kwargs={"pk": self.user.pk})

        response = self.client.get(url)
        self.assertEqual(401, response.status_code)

        for token in (
            "first-party-token",
            "third-party-token",
            "third-party-client-credentials",
        ):
            r = self.client.get(url, headers={"Authorization": "Bearer %s" % token})
            self.assertEqual(200, r.status_code, msg="used %s" % token)

    def test_require_user(self):
        url = reverse("api:auth:user-me")

        params = [
            (200, "first-party-token"),
            (200, "third-party-token"),
            (403, "third-party-client-credentials"),
        ]
        for status_code, token in params:
            r = self.client.get(url, headers={"Authorization": "Bearer %s" % token})
            self.assertEqual(status_code, r.status_code, msg="used %s" % token)

    def test_require_scope(self):
        url = reverse("api:auth:user-me")

        params = [
            (200, "first-party-token"),
            (403, "first-party-token-without-write"),
            (403, "third-party-token"),
            (403, "third-party-token-with-write"),
        ]
        for status_code, token in params:
            r = self.client.patch(
                url,
                data={"display_name": "hello"},
                headers={"Authorization": "Bearer %s" % token},
            )
            self.assertEqual(status_code, r.status_code, msg="used %s" % token)

    def test_properly_responds_with_405_rather_than_403(self):
        r = self.client.post(
            reverse("api:auth:user-me"),
            headers={"Authorization": "Bearer third-party-token"},
        )
        self.assertEqual(405, r.status_code)

    def test_user_me_limited_scopes_changes_fields(self):
        cases = {
            "third-party-token": [
                "id",
                "display_name",
                "username",
                "description",
                "website",
                "profile_picture",
                "date_joined",
                "is_private",
                "url",
            ],
            "third-party-token-with-email": [
                "id",
                "display_name",
                "username",
                "email",  # <--- here should it be!
                "description",
                "website",
                "profile_picture",
                "date_joined",
                "is_private",
                "url",
            ],
            "third-party-token-with-private": [
                "id",
                "display_name",
                "username",
                "email",  # <---
                "description",
                "website",
                "profile_picture",
                "gender",  # <---
                "language",  # <---
                "birth_date",  # <---
                "date_joined",
                "is_private",
                "allows_receipts",  # <---
                "allows_all_messages",  # <---
                "two_factor_enabled",  # <---
                "url",
            ],
            "third-party-token-with-private-no-email": [
                "id",
                "display_name",
                "username",
                # <missing email here>
                "description",
                "website",
                "profile_picture",
                "gender",
                "language",
                "birth_date",
                "date_joined",
                "is_private",
                "allows_receipts",
                "allows_all_messages",
                "two_factor_enabled",
                "url",
            ],
        }
        for token, fields in cases.items():
            response = self.client.get(
                reverse("api:auth:user-me"),
                headers={"Authorization": "Bearer %s" % token},
            )
            self.assertEqual(200, response.status_code)
            self.assertEqual(fields, list(response.data.keys()))


class TestSession(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user1 = UserFactory()

    def test_session_anonymous(self):
        self.client.get(
            reverse("two_factor:login"),
            headers={"User-Agent": "TestAgent/1.0"},
        )

        session_key = self.client.session.session_key
        session = Session.objects.get(session_key=session_key)

        self.assertIsNone(session.user)
        self.assertEqual("TestAgent/1.0", session.user_agent)
        self.assertEqual("127.0.0.1", session.ip)

    def test_session_authenticated(self):
        self.client.force_login(self.user1)
        self.client.get(
            reverse("two_factor:login"),
            headers={"User-Agent": "TestAgent/2.0"},
        )

        session_key = self.client.session.session_key
        session = Session.objects.get(session_key=session_key)

        self.assertEqual(self.user1.pk, session.user)
        self.assertEqual("TestAgent/2.0", session.user_agent)
        self.assertEqual("127.0.0.1", session.ip)


class TestUserRelationLookup(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user1 = UserFactory()
        cls.user2 = UserFactory()
        cls.user3 = UserFactory()
        cls.user4 = UserFactory()
        cls.url = reverse("api:auth:user-relations")

    def make_username_list(self, *users):
        return ",".join(str(user.username) for user in users)

    def test_unrelated(self):
        self.client.force_login(self.user1)
        response = self.client.get(
            self.url,
            data={
                "usernames": self.make_username_list(
                    self.user2,
                    self.user3,
                    self.user4,
                )
            },
        )

        self.assertEqual(200, response.status_code)
        results = response.data["results"]
        self.assertEqual(3, len(results))

        for user in results:
            self.assertTrue(user["username"])
            self.assertEqual([], user["relations"])

    def test_related_multiple(self):
        self.client.force_login(self.user1)
        self.user1.following.add(self.user4)
        self.user2.send_follow_request(to_user=self.user1)
        self.user3.blocked.add(self.user1)

        response = self.client.get(
            self.url,
            data={
                "usernames": self.make_username_list(
                    self.user2,
                    self.user3,
                    self.user4,
                )
            },
        )

        self.assertEqual(200, response.status_code)
        results = response.data["results"]
        self.assertEqual(3, len(results))

        user2, user3, user4 = sorted(results, key=lambda user: user["id"])

        self.assertEqual(["follow_request_received"], user2["relations"])
        self.assertEqual(["blocked_by"], user3["relations"])
        self.assertEqual(["following"], user4["relations"])

    def test_following(self):
        self.client.force_login(self.user1)
        self.user1.add_following(to_user=self.user2)

        response = self.client.get(self.url, data={"usernames": self.user2.username})

        self.assertEqual(200, response.status_code)
        user = response.data["results"][0]

        self.assertEqual(["following"], user["relations"])

    def test_followed_by(self):
        self.client.force_login(self.user1)
        self.user2.add_following(to_user=self.user1)

        response = self.client.get(self.url, data={"usernames": self.user2.username})

        self.assertEqual(200, response.status_code)
        user = response.data["results"][0]

        self.assertEqual(["followed_by"], user["relations"])

    def test_following_and_followed_by(self):
        self.client.force_login(self.user1)
        self.user1.add_following(to_user=self.user2)
        self.user2.add_following(to_user=self.user1)

        response = self.client.get(self.url, data={"usernames": self.user2.username})

        self.assertEqual(200, response.status_code)
        user = response.data["results"][0]

        self.assertEqual(["following", "followed_by"], user["relations"])

    def test_blocking(self):
        self.client.force_login(self.user1)
        self.user1.blocked.add(self.user2)

        response = self.client.get(self.url, data={"usernames": self.user2.username})

        self.assertEqual(200, response.status_code)
        user = response.data["results"][0]

        self.assertEqual(["blocking"], user["relations"])

    def test_blocked_by(self):
        self.client.force_login(self.user1)
        self.user2.blocked.add(self.user1)

        response = self.client.get(self.url, data={"usernames": self.user2.username})

        self.assertEqual(200, response.status_code)
        user = response.data["results"][0]

        self.assertEqual(["blocked_by"], user["relations"])

    def test_blocking_and_blocked_by(self):
        self.client.force_login(self.user1)
        self.user1.blocked.add(self.user2)
        self.user2.blocked.add(self.user1)

        response = self.client.get(self.url, data={"usernames": self.user2.username})

        self.assertEqual(200, response.status_code)
        user = response.data["results"][0]

        self.assertEqual(["blocking", "blocked_by"], user["relations"])

    def test_follow_request_sent(self):
        self.client.force_login(self.user1)
        self.user1.send_follow_request(to_user=self.user2)

        response = self.client.get(self.url, data={"usernames": self.user2.username})

        self.assertEqual(200, response.status_code)
        user = response.data["results"][0]

        self.assertEqual(["follow_request_sent"], user["relations"])

    def test_follow_request_received(self):
        self.client.force_login(self.user1)
        self.user2.send_follow_request(to_user=self.user1)

        response = self.client.get(self.url, data={"usernames": self.user2.username})

        self.assertEqual(200, response.status_code)
        user = response.data["results"][0]

        self.assertEqual(["follow_request_received"], user["relations"])

    def test_follow_request_sent_and_received(self):
        self.client.force_login(self.user1)
        self.user1.send_follow_request(to_user=self.user2)
        self.user2.send_follow_request(to_user=self.user1)

        response = self.client.get(self.url, data={"usernames": self.user2.username})

        self.assertEqual(200, response.status_code)
        user = response.data["results"][0]

        self.assertEqual(
            ["follow_request_sent", "follow_request_received"], user["relations"]
        )

    def test_mixed_followed_by_follow_request_sent(self):
        self.client.force_login(self.user1)
        self.user1.send_follow_request(to_user=self.user2)
        self.user2.add_following(to_user=self.user1)

        response = self.client.get(self.url, data={"usernames": self.user2.username})

        self.assertEqual(200, response.status_code)
        user = response.data["results"][0]

        self.assertEqual(["followed_by", "follow_request_sent"], user["relations"])
