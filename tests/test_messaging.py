import datetime

import django.core.signing
from django.db.models import F
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property

from rest_framework.test import APITestCase

from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator

from asu.auth.models import UserFollow
from asu.messaging.models import Conversation, ConversationRequest, Message
from asu.messaging.websocket import ConversationConsumer
from tests.factories import UserFactory


class TestMessaging(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user0 = UserFactory()
        cls.user1 = UserFactory()
        cls.user2 = UserFactory()
        cls.user3 = UserFactory()
        cls.user4 = UserFactory(allows_receipts=False)
        cls.user5 = UserFactory(allows_receipts=False)
        cls.frozen_user = UserFactory(is_frozen=True)
        cls.inactive_user = UserFactory(is_active=False)
        cls.user_disabled_msg_requests = UserFactory(allows_all_messages=False)

    def _accept_conversation(self, sender, recipient):
        ConversationRequest.objects.filter(sender=sender, recipient=recipient).update(
            date_accepted=timezone.now()
        )

    def _send_message(self, sender, recipient, message):
        self.client.force_login(sender)
        return self.client.post(
            reverse("api:auth:user-message", kwargs={"pk": recipient.pk}),
            data={"body": message},
        )

    def test_message_basic(self):
        self.client.force_login(self.user1)
        response = self.client.post(
            reverse("api:auth:user-message", kwargs={"pk": self.user2.pk}),
            data={"body": "Hello world!"},
        )
        self.assertEqual(201, response.status_code)

    def test_message_fails_if_blocked(self):
        self.user1.blocked.add(self.user2)
        response = self._send_message(self.user1, self.user2, "Hi")
        self.assertEqual(403, response.status_code)

    def test_message_fails_if_blocked_by(self):
        self.user2.blocked.add(self.user1)
        response = self._send_message(self.user1, self.user2, "Hi")
        self.assertEqual(404, response.status_code)

    def test_self_message_fails(self):
        response = self._send_message(self.user1, self.user1, "Hi myself")
        self.assertEqual(403, response.status_code)

    def test_message_fails_if_user_not_accessible(self):
        # This check is already applied in UserViewSet, so testing this
        # part of the method manually (instead of sending an api request).
        self.assertFalse(self.frozen_user.can_send_message(self.user1))
        self.assertFalse(self.inactive_user.can_send_message(self.user1))
        self.assertFalse(self.user1.can_send_message(self.frozen_user))
        self.assertFalse(self.user1.can_send_message(self.inactive_user))

    def test_message_fails_if_requests_disabled(self):
        response = self._send_message(self.user1, self.user_disabled_msg_requests, "Hi")
        self.assertEqual(response.status_code, 403)

    def test_message_reply_fails_if_not_accepted(self):
        response = self._send_message(self.user1, self.user2, "Hi")
        self.assertEqual(201, response.status_code)
        response = self._send_message(self.user2, self.user1, "Yo")
        self.assertEqual(403, response.status_code)

        conversation = Conversation.objects.get(holder=self.user2)
        conversation = self.client.get(
            reverse(
                "api:messaging:conversation-detail",
                kwargs={"pk": conversation.pk},
            )
        )
        accept_required = conversation.data["accept_required"]
        self.assertTrue(accept_required)

    def test_message_fails_on_preference_interruption(self):
        # In this case, the request was created but not accepted.
        # The user then decided to not receive any messages from
        # strangers. So no new messages could be added to the
        # conversation.
        self._send_message(self.user1, self.user2, "Hi")
        self.client.force_login(self.user2)

        self.user2.allows_all_messages = False
        self.user2.save(update_fields=["allows_all_messages"])

        response = self._send_message(self.user1, self.user2, "Hi again")
        self.assertEqual(403, response.status_code)

    def test_message_fails_on_blocking_interruption(self):
        self._send_message(self.user1, self.user2, "Hi")
        self.client.force_login(self.user2)

        self.user2.blocked.add(self.user1)

        response = self._send_message(self.user1, self.user2, "Hi again")
        self.assertEqual(404, response.status_code)

    def test_message_ok_on_deletion_interruption(self):
        self._send_message(self.user1, self.user2, "Hi")
        original_request = ConversationRequest.objects.get()
        original_conversation = Conversation.objects.get(holder=self.user2)

        self._accept_conversation(self.user1, self.user2)

        r1 = self._send_message(self.user2, self.user1, "What?")
        self.assertEqual(201, r1.status_code)

        original_conversation.delete()

        r2 = self._send_message(self.user2, self.user1, "May I?")
        self.assertEqual(201, r2.status_code)

        current_request = ConversationRequest.objects.get()
        self.assertEqual(current_request, original_request)

        current_conversation = Conversation.objects.get(holder=self.user2)
        self.assertNotEqual(current_conversation, original_conversation)

    def test_message_request_changed_on_follow_interruption(self):
        self._send_message(self.user1, self.user2, "Hi")

        request = ConversationRequest.objects.get()
        self.assertIsNone(request.date_accepted)

        self.user1.add_following(to_user=self.user2)

        r1 = self._send_message(self.user1, self.user2, "Hi again")
        request.refresh_from_db()
        self.assertIsNone(request.date_accepted)
        self.assertEqual(201, r1.status_code)

        r2 = self._send_message(self.user2, self.user1, "Hey")
        request.refresh_from_db()
        self.assertIsNotNone(request.date_accepted)
        self.assertEqual(201, r2.status_code)

    def test_message_ok_if_previous_request_case_1(self):
        # User does not accept external messages, but sent a message
        # to a stranger. The stranger should be able to reply.
        self._send_message(self.user_disabled_msg_requests, self.user2, "Hi")

        target_conversation = Conversation.objects.get(holder=self.user2)
        self.client.force_login(self.user2)
        self.client.patch(
            reverse(
                "api:messaging:conversation-accept",
                kwargs={"pk": target_conversation.pk},
            )
        )

        response = self._send_message(self.user2, self.user_disabled_msg_requests, "Yo")
        self.assertEqual(201, response.status_code)

    def test_message_ok_if_previous_request_case_2(self):
        # Case 1 but message preference changed after the request
        # has been accepted.
        self._send_message(self.user1, self.user2, "Hi")

        target_conversation = Conversation.objects.get(holder=self.user2)
        self.client.force_login(self.user2)

        self.client.patch(
            reverse(
                "api:messaging:conversation-accept",
                kwargs={"pk": target_conversation.pk},
            )
        )
        self.user2.allows_all_messages = False
        self.user2.save(update_fields=["allows_all_messages"])

        response = self._send_message(self.user1, self.user2, "Hi again")
        self.assertEqual(201, response.status_code)

    def test_message_ok_if_previous_request_case_3(self):
        # In this case, request was previously accepted due
        # to follow relations. Reversed version of:
        # test_message_request_changed_on_follow_interruption
        self.user1.add_following(to_user=self.user2)
        self._send_message(self.user2, self.user1, "Hi")

        UserFollow.objects.filter(from_user=self.user1, to_user=self.user2).delete()

        r1 = self._send_message(self.user2, self.user1, "Hi again")
        r2 = self._send_message(self.user1, self.user2, "What?")

        self.assertEqual(201, r1.status_code)
        self.assertEqual(201, r2.status_code)

    def test_messaging_creates_relations(self):
        self.client.force_login(self.user1)
        response = self._send_message(self.user1, self.user2, "Hello world!")
        self.assertEqual(201, response.status_code)

        message = Message.objects.get()
        request = ConversationRequest.objects.get()
        sender_conversation = Conversation.objects.get(holder=self.user1)
        recipient_conversation = Conversation.objects.get(holder=self.user2)

        self.assertEqual(2, Conversation.objects.all().count())
        self.assertEqual(self.user1, request.sender)
        self.assertEqual(self.user2, request.recipient)
        self.assertIsNone(request.date_accepted)
        self.assertEqual(message, recipient_conversation.messages.get())
        self.assertEqual(message, sender_conversation.messages.get())
        self.assertEqual(self.user1, message.sender)
        self.assertEqual(self.user2, message.recipient)
        self.assertEqual(self.user1, sender_conversation.holder)
        self.assertEqual(self.user2, sender_conversation.target)
        self.assertEqual(self.user2, recipient_conversation.holder)
        self.assertEqual(self.user1, recipient_conversation.target)

        # Creating subsequent messages here, to make sure no duplicate
        # stuff is created.
        self._accept_conversation(self.user1, self.user2)
        self._send_message(self.user1, self.user2, "Hello again")
        self._send_message(self.user2, self.user1, "Thank you")
        self.assertEqual(2, Conversation.objects.all().count())
        self.assertEqual(3, Message.objects.all().count())
        self.assertEqual(3, sender_conversation.messages.all().count())
        self.assertEqual(3, recipient_conversation.messages.all().count())
        self.assertEqual(1, ConversationRequest.objects.all().count())

    def test_follow_rel_auto_accepts(self):
        self.user1.add_following(to_user=self.user2)
        response = self._send_message(self.user2, self.user1, "Hi")

        self.assertEqual(201, response.status_code)

        request = ConversationRequest.objects.get()
        self.assertIsNotNone(request.date_accepted)

        self.client.force_login(self.user1)
        conversation = Conversation.objects.get(holder=self.user1)

        conversation = self.client.get(
            reverse(
                "api:messaging:conversation-detail",
                kwargs={"pk": conversation.pk},
            )
        )
        accept_required = conversation.data["accept_required"]
        self.assertFalse(accept_required)

    def test_follow_rel_other_direction(self):
        # Sending a message to some person I'm following, but not
        # followed by, it should create a pending request.
        self.user1.add_following(to_user=self.user2)
        self._send_message(self.user1, self.user2, "Hi")

        request = ConversationRequest.objects.get()
        self.assertIsNone(request.date_accepted)

    def test_follow_rel_both_directions(self):
        self.user1.add_following(to_user=self.user2)
        self.user2.add_following(to_user=self.user1)
        self._send_message(self.user1, self.user2, "Hi")

        request = ConversationRequest.objects.get()
        self.assertIsNotNone(request.date_accepted)

    def test_message_updates_conversation_date_modified(self):
        self._send_message(self.user1, self.user2, "Hi")
        self._accept_conversation(self.user1, self.user2)

        c1 = Conversation.objects.get(holder=self.user1)
        c2 = Conversation.objects.get(holder=self.user2)

        md1 = c1.date_modified
        md2 = c2.date_modified

        self.assertIsNotNone(md1)
        self.assertIsNotNone(md2)

        self._send_message(self.user2, self.user1, "Go away")

        c1.refresh_from_db()
        c2.refresh_from_db()

        self.assertNotEqual(md1, c1.date_modified)
        self.assertNotEqual(md2, c2.date_modified)

    def test_receipt_registry(self):
        yes_no = self._send_message(self.user1, self.user4, "Hi")
        no_yes = self._send_message(self.user4, self.user3, "Hi")
        no_no = self._send_message(self.user4, self.user5, "Hi")
        yes_yes = self._send_message(self.user1, self.user2, "Hi")

        yes_no = Message.objects.get(pk=yes_no.data["id"])
        no_yes = Message.objects.get(pk=no_yes.data["id"])
        no_no = Message.objects.get(pk=no_no.data["id"])
        yes_yes = Message.objects.get(pk=yes_yes.data["id"])

        self.assertFalse(yes_no.has_receipt)
        self.assertFalse(no_yes.has_receipt)
        self.assertFalse(no_no.has_receipt)
        self.assertTrue(yes_yes.has_receipt)

    def test_message_modification_does_not_affect_conversation(self):
        self._send_message(self.user1, self.user2, "Hi")
        message = Message.objects.get()
        conversation = Conversation.objects.get(holder=self.user1)
        date_modified = conversation.date_modified

        message.save(update_fields=["date_modified"])
        conversation.refresh_from_db()
        self.assertEqual(date_modified, conversation.date_modified)

    def test_conversation_accept_idempotency(self):
        self._send_message(self.user1, self.user2, "Hi")
        conversation = Conversation.objects.get(holder=self.user2)

        url = reverse(
            "api:messaging:conversation-accept", kwargs={"pk": conversation.pk}
        )

        self.client.force_login(self.user2)

        r1 = self.client.patch(url)
        r2 = self.client.patch(url)
        r3 = self.client.patch(url)

        self.assertEqual(204, r1.status_code)
        request = ConversationRequest.objects.get()
        date_accepted = request.date_accepted

        self.assertEqual(204, r2.status_code)
        self.assertEqual(204, r3.status_code)

        request.refresh_from_db()
        self.assertEqual(date_accepted, request.date_accepted)

    def test_conversation_list(self):
        url = reverse("api:messaging:conversation-list")
        requests_url = reverse("api:messaging:conversation-list") + "?type=requests"

        self._send_message(self.user1, self.user2, "Hi")
        self._send_message(self.user1, self.user3, "Hi")

        # 1. Check conversation list
        user1_conversations_response = self.client.get(url)
        self.assertEqual(200, user1_conversations_response.status_code)
        self.assertEqual(2, len(user1_conversations_response.data["results"]))
        self.assertContains(user1_conversations_response, self.user2.username)
        self.assertContains(user1_conversations_response, self.user3.username)

        # 2. Check conversation requests
        user1_conversation_requests_response = self.client.get(requests_url)
        self.assertEqual(200, user1_conversation_requests_response.status_code)
        self.assertEqual(0, len(user1_conversation_requests_response.data["results"]))

        # (Target perspective)

        # 1a.
        self.client.force_login(self.user2)
        user2_conversations_response = self.client.get(url)
        self.assertEqual(200, user2_conversations_response.status_code)
        self.assertEqual(0, len(user2_conversations_response.data["results"]))

        # 2a.
        user2_conversation_requests_response = self.client.get(requests_url)
        self.assertEqual(200, user2_conversation_requests_response.status_code)
        results = user2_conversation_requests_response.data["results"]
        self.assertEqual(1, len(results))
        self.assertContains(user2_conversation_requests_response, self.user1.username)

        # 3. Accept the conversation; we should observe the change
        # in lists.
        accept_response = self.client.patch(results[0]["url"] + "accept/")
        self.assertEqual(204, accept_response.status_code)

        user2_conversations_response = self.client.get(url)
        self.assertEqual(1, len(user2_conversations_response.data["results"]))

        user2_conversation_requests_response = self.client.get(requests_url)
        self.assertEqual(0, len(user2_conversation_requests_response.data["results"]))

    def test_conversation_list_case_1(self):
        self._send_message(self.user0, self.user1, "Yo")
        self._send_message(self.user1, self.user2, "Hi")
        self._send_message(self.user1, self.user3, "Hello")

        r1 = self.client.get(reverse("api:messaging:conversation-list"))
        r2 = self.client.get(
            reverse("api:messaging:conversation-list") + "?type=requests"
        )
        self.assertEqual(2, len(r1.data["results"]))
        self.assertEqual(1, len(r2.data["results"]))

    def test_conversation_list_case_2(self):
        self._send_message(self.user0, self.user1, "Hi")
        self._send_message(self.user1, self.user2, "Hello")

        self.client.force_login(self.user2)
        r1 = self.client.get(reverse("api:messaging:conversation-list"))
        self.assertEqual(0, len(r1.data["results"]))

    def test_conversation_list_case_3(self):
        self._send_message(self.user0, self.user1, "Hi")
        self._accept_conversation(self.user0, self.user1)

        self._send_message(self.user2, self.user1, "Hello")
        self._send_message(self.user3, self.user1, "Hello")

        self.client.force_login(self.user1)
        r2 = self.client.get(reverse("api:messaging:conversation-list"))
        self.assertEqual(1, len(r2.data["results"]))

        r3 = self.client.get(
            reverse("api:messaging:conversation-list") + "?type=requests"
        )
        url = r3.data["results"][0]["url"]
        accept = self.client.patch(url + "accept/")
        self.assertEqual(204, accept.status_code)

    def test_conversation_last_message(self):
        r1 = self._send_message(self.user1, self.user2, "Gary says hello")
        conversation_1 = r1.data["conversation"]
        r2 = self.client.get(conversation_1)
        self.assertEqual("Gary says hello", r2.data["last_message"]["body"])

        self._accept_conversation(self.user1, self.user2)
        r3 = self._send_message(self.user2, self.user1, "Gary who?")

        conversation_2 = r3.data["conversation"]
        r4 = self.client.get(conversation_2)
        self.assertEqual("Gary who?", r4.data["last_message"]["body"])

        self.client.force_login(self.user1)
        r5 = self.client.get(conversation_1)
        self.assertEqual("Gary who?", r5.data["last_message"]["body"])

    def test_conversation_messages_url(self):
        r1 = self._send_message(self.user1, self.user2, "Hello")
        conversation = r1.data["conversation"]
        r2 = self.client.get(conversation)

        pk = r2.data["id"]
        self.assertTrue(
            r2.data["messages"].endswith(
                reverse("api:messaging:message-list", kwargs={"conversation_pk": pk})
            )
        )

    def test_conversation_last_message_case_deletion(self):
        r1 = self._send_message(self.user1, self.user2, "Gary says hello")
        conversation = r1.data["conversation"]

        message = conversation + "messages/%s/" % r1.data["id"]
        self.client.delete(message)

        r2 = self.client.get(conversation)
        self.assertIsNone(r2.data["last_message"])

        # Target should still have the deleted message.
        self.client.force_login(self.user2)
        conversation_2 = Conversation.objects.filter(holder=self.user2).only("pk").get()
        r3 = self.client.get(
            reverse(
                "api:messaging:conversation-detail",
                kwargs={"pk": conversation_2.pk},
            )
        )
        self.assertEqual("Gary says hello", r3.data["last_message"]["body"])

    def test_conversation_read(self):
        self._send_message(self.user1, self.user2, "Howdy")
        self._send_message(self.user1, self.user2, "Are you there?")
        self._send_message(self.user1, self.user2, "Whatever.")
        self._accept_conversation(self.user1, self.user2)
        r1 = self._send_message(self.user2, self.user1, "Whats up?")

        conversation = r1.data["conversation"]
        response = self.client.post(
            conversation + "read/",
            data={"until": timezone.now()},
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(3, response.data["affected"])
        self.assertEqual(
            3,
            Message.objects.filter(
                date_read__isnull=False,
                sender=self.user1,
            ).count(),
        )
        self.assertEqual(
            1,
            Message.objects.filter(
                date_read__isnull=True,
                sender=self.user2,
            ).count(),
        )

    def test_conversation_read_case_partial_update(self):
        self._send_message(self.user1, self.user2, "Howdy")
        second = self._send_message(self.user1, self.user2, "Are you there?")
        third = self._send_message(self.user1, self.user2, "Whatever.")

        # Change the send date of the last message. Only the first two
        # messages are going to be set as 'read'.
        msg_id = third.data["id"]
        Message.objects.filter(pk=msg_id).update(
            date_created=F("date_created") + datetime.timedelta(hours=4)
        )

        # Read the conversation from target user.
        self.client.force_login(self.user2)
        conversation = Conversation.objects.get(holder=self.user2)
        response = self.client.post(
            reverse(
                "api:messaging:conversation-read",
                kwargs={"pk": conversation.pk},
            ),
            data={"until": second.data["date_created"]},
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(2, response.data["affected"])
        self.assertEqual(
            2,
            Message.objects.filter(
                date_read__isnull=False,
                sender=self.user1,
            ).count(),
        )
        self.assertEqual(
            1,
            Message.objects.filter(
                date_read__isnull=True,
                sender=self.user1,
                body="Whatever.",
            ).count(),
        )

    def test_message_list(self):
        self._send_message(self.user1, self.user2, "Howdy")
        r1 = self._send_message(self.user1, self.user2, "World is great!")
        conversation = r1.data["conversation"]
        r2 = self.client.get(conversation + "messages/")
        results = r2.data["results"]

        self.assertEqual(200, r2.status_code)
        self.assertEqual(2, len(results))

        self.assertContains(r2, "Howdy")
        self.assertContains(r2, "World")

        for result in results:
            self.assertEqual("sent", result["source"])

        # Target perspective
        self.client.force_login(self.user2)
        conversation = Conversation.objects.get(holder=self.user2)
        target_messages = self.client.get(
            reverse(
                "api:messaging:conversation-detail",
                kwargs={"pk": conversation.pk},
            )
            + "messages/"
        )
        results = target_messages.data["results"]
        self.assertEqual(2, len(results))

        for result in results:
            self.assertEqual("received", result["source"])

    def test_message_detail(self):
        r1 = self._send_message(self.user1, self.user2, "Howdy")
        message_id = r1.data["id"]
        conversation = r1.data["conversation"]

        r2 = self.client.get(conversation + f"messages/{message_id}/")

        self.assertEqual(200, r2.status_code)
        self.assertContains(r2, "Howdy")

    def _test_receipt_fragment(self, u1, u2):
        r1 = self._send_message(u1, u2, "Howdy")
        message_id = r1.data["id"]
        conversation = r1.data["conversation"]

        msg = Message.objects.get(pk=message_id)
        msg.date_read = timezone.now()
        msg.save(update_fields=["date_read"])

        r2 = self.client.get(conversation + f"messages/{message_id}/")
        return r2.data["date_read"]

    def test_message_receipt_hidden(self):
        date_read = self._test_receipt_fragment(self.user4, self.user1)
        self.assertIsNone(date_read)

    def test_message_receipt_shown(self):
        date_read = self._test_receipt_fragment(self.user1, self.user2)
        self.assertIsNotNone(date_read)

    def test_message_delete(self):
        self._send_message(self.user1, self.user2, "Hi")
        r1 = self._send_message(self.user1, self.user2, "Hi again")
        message_id = r1.data["id"]
        message_url = r1.data["url"]

        detail = self.client.get(message_url)
        self.assertEqual(200, detail.status_code)

        removed = self.client.delete(message_url)
        self.assertEqual(204, removed.status_code)

        detail = self.client.get(message_url)
        self.assertEqual(404, detail.status_code)

        self.assertTrue(Message.objects.filter(pk=message_id).exists())

        conversation = Conversation.objects.get(holder=self.user1)
        other_conversation = Conversation.objects.get(holder=self.user2)
        self.assertFalse(conversation.messages.filter(pk=message_id).exists())
        self.assertTrue(other_conversation.messages.filter(pk=message_id).exists())

    def test_message_delete_both_cascades(self):
        r1 = self._send_message(self.user1, self.user2, "Hi")
        message_id = r1.data["id"]
        c1 = Conversation.objects.get(holder=self.user1)
        c2 = Conversation.objects.get(holder=self.user2)

        message_url_1 = reverse(
            "api:messaging:message-detail",
            kwargs={"conversation_pk": c1.pk, "pk": message_id},
        )
        message_url_2 = reverse(
            "api:messaging:message-detail",
            kwargs={"conversation_pk": c2.pk, "pk": message_id},
        )
        self.client.delete(message_url_1)
        self.client.force_login(self.user2)
        self.client.delete(message_url_2)

        self.assertFalse(Message.objects.filter(pk=message_id).exists())

    def test_delete_conversation(self):
        r1 = self._send_message(self.user1, self.user2, "Hi")
        conversation_url = r1.data["conversation"]

        detail = self.client.get(conversation_url)
        self.assertEqual(200, detail.status_code)

        removed = self.client.delete(conversation_url)
        self.assertEqual(204, removed.status_code)

        detail = self.client.get(conversation_url)
        self.assertEqual(404, detail.status_code)

        self.assertFalse(Conversation.objects.filter(holder=self.user1).exists())
        self.assertTrue(Conversation.objects.filter(holder=self.user2).exists())
        self.assertEqual(1, ConversationRequest.objects.all().count())

    def test_conversation_delete_both_cascades_message(self):
        self._send_message(self.user1, self.user2, "Hi")
        self._send_message(self.user1, self.user2, "Hello")
        c1 = Conversation.objects.get(holder=self.user1)
        c2 = Conversation.objects.get(holder=self.user2)

        conversation_url_1 = reverse(
            "api:messaging:conversation-detail", kwargs={"pk": c1.pk}
        )
        conversation_url_2 = reverse(
            "api:messaging:conversation-detail", kwargs={"pk": c2.pk}
        )

        self.client.delete(conversation_url_1)
        self.client.force_login(self.user2)
        self.client.delete(conversation_url_2)

        self.assertFalse(Message.objects.all().exists())
        self.assertEqual(1, ConversationRequest.objects.all().count())

    def test_can_only_see_own_messages(self):
        # Send independent messages to two conversations and make sure
        # only the participants can access those messages.
        msg_1 = self._send_message(
            self.user1, self.user2, "user1 and user2 message"
        ).json()
        msg_1_url = msg_1["url"]

        msg_2 = self._send_message(
            self.user3, self.user4, "user3 and user4 message"
        ).json()
        msg_2_url = msg_2["url"]

        # at this point, authenticated user is 'user3'. Both user3 and
        # user4 should not be able to see messages of user1 and user2
        r1 = self.client.get(msg_1_url)
        r2 = self.client.get(msg_2_url)
        self.assertEqual(404, r1.status_code)
        self.assertEqual(200, r2.status_code)

        # try for user4
        self.client.force_login(self.user4)
        r1_alt = self.client.get(msg_1_url)
        r2_alt = self.client.get(msg_2_url)
        self.assertEqual(404, r1_alt.status_code)
        self.assertEqual(200, r2_alt.status_code)

    # Websocket related

    @cached_property
    def communicator(self):
        return WebsocketCommunicator(
            ConversationConsumer.as_asgi(),
            "/ws/conversations/",
        )

    async def test_ws_connects(self):
        connected, _ = await self.communicator.connect()
        self.assertTrue(connected)
        await self.communicator.receive_nothing()
        await self.communicator.disconnect()

    async def test_ws_bad_ticket(self):
        await self.communicator.connect()
        await self.communicator.send_json_to({"ticket": "ticket"})

        with self.assertRaises(django.core.signing.BadSignature):
            await self.communicator.receive_from(timeout=0.001)

    def _capture_message(self, sender, recipient, message):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            response = self._send_message(sender, recipient, message)
            return response, callbacks

    async def test_ws_sends_message(self):
        await self.communicator.connect()

        # Verify ticket
        await sync_to_async(self.client.force_login)(self.user1)
        response = await sync_to_async(self.client.post)(
            reverse("api:auth:user-ticket"),
            data={"scope": "websocket"},
        )
        ticket = response.data["ticket"]
        await self.communicator.send_json_to({"ticket": ticket})

        # Send message while connected to conversation ws
        api_result, callbacks = await sync_to_async(self._capture_message)(
            self.user2, self.user1, "Hi"
        )
        ws_result = await self.communicator.receive_json_from(timeout=0.01)

        message_id = api_result.data["id"]
        timestamp = api_result.data["date_created"]
        target_conversation = await sync_to_async(Conversation.objects.get)(
            holder=self.user1
        )

        self.assertEqual(1, len(callbacks))
        self.assertEqual(ws_result["type"], "conversation.message")
        self.assertEqual(ws_result["conversation_id"], target_conversation.id)
        self.assertEqual(ws_result["message_id"], message_id)
        self.assertEqual(ws_result["timestamp"], timestamp)
        await self.communicator.disconnect()
