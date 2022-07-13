from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APITestCase

from zeynep.auth.models import UserFollow
from zeynep.messaging.models import Conversation, ConversationRequest, Message
from zeynep.tests.factories import UserFactory


class TestMessaging(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = UserFactory()
        cls.user2 = UserFactory()
        cls.user3 = UserFactory()
        cls.user4 = UserFactory(allows_receipts=False)
        cls.user5 = UserFactory(allows_receipts=False)
        cls.frozen_user = UserFactory(is_frozen=True)
        cls.inactive_user = UserFactory(is_active=False)
        cls.user_disabled_msg_requests = UserFactory(allows_all_messages=False)

    def _accept_conversation(self, sender, recipient):  # noqa
        ConversationRequest.objects.filter(
            sender=sender, conversation__holder=recipient
        ).update(date_accepted=timezone.now())

    def _send_message(self, sender, recipient, message):
        self.client.force_login(sender)
        return self.client.post(
            reverse("user-message", kwargs={"username": recipient.username}),
            data={"body": message},
        )

    def test_message_basic(self):
        self.client.force_login(self.user1)
        response = self.client.post(
            reverse("user-message", kwargs={"username": self.user2.username}),
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
        response = self._send_message(
            self.user1, self.user_disabled_msg_requests, "Hi"
        )
        self.assertEqual(response.status_code, 403)

    def test_message_reply_fails_if_not_accepted(self):
        response = self._send_message(self.user1, self.user2, "Hi")
        self.assertEqual(201, response.status_code)
        response = self._send_message(self.user2, self.user1, "Yo")
        self.assertEqual(403, response.status_code)

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
        self.client.post(
            reverse(
                "conversation-accept",
                kwargs={"pk": target_conversation.pk},
            )
        )

        response = self._send_message(
            self.user2, self.user_disabled_msg_requests, "Yo"
        )
        self.assertEqual(201, response.status_code)

    def test_message_ok_if_previous_request_case_2(self):
        # Case 1 but message preference changed after the request
        # has been accepted.
        self._send_message(self.user1, self.user2, "Hi")

        target_conversation = Conversation.objects.get(holder=self.user2)
        self.client.force_login(self.user2)

        self.client.post(
            reverse(
                "conversation-accept",
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

        UserFollow.objects.filter(
            from_user=self.user1, to_user=self.user2
        ).delete()

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
        self.assertEqual(recipient_conversation, request.conversation)
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

        url = reverse("conversation-accept", kwargs={"pk": conversation.pk})

        self.client.force_login(self.user2)

        r1 = self.client.post(url)
        r2 = self.client.post(url)
        r3 = self.client.post(url)

        self.assertEqual(204, r1.status_code)
        request = conversation.requests.get()
        date_accepted = request.date_accepted

        self.assertEqual(204, r2.status_code)
        self.assertEqual(204, r3.status_code)

        request.refresh_from_db()
        self.assertEqual(date_accepted, request.date_accepted)

    def test_conversation_list(self):
        url = reverse("conversation-list")
        requests_url = reverse("conversation-list") + "?type=requests"

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
        self.assertEqual(
            0, len(user1_conversation_requests_response.data["results"])
        )

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
        self.assertContains(
            user2_conversation_requests_response, self.user1.username
        )

        # 3. Accept the conversation; we should observe the change
        # in lists.
        accept_response = self.client.post(results[0]["url"] + "accept/")
        self.assertEqual(204, accept_response.status_code)

        user2_conversations_response = self.client.get(url)
        self.assertEqual(1, len(user2_conversations_response.data["results"]))

        user2_conversation_requests_response = self.client.get(requests_url)
        self.assertEqual(
            0, len(user2_conversation_requests_response.data["results"])
        )
