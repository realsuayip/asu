from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APITestCase

from zeynep.messaging.models import Conversation, ConversationRequest, Message
from zeynep.tests.factories import UserFactory


class TestMessaging(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = UserFactory()
        cls.user2 = UserFactory()
        cls.user3 = UserFactory()
        cls.user4 = UserFactory()
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

    def test_message_fails_if_requests_disabled(self):
        response = self._send_message(
            self.user1, self.user_disabled_msg_requests, "Hi"
        )
        self.assertEqual(response.status_code, 403)

    def test_message_reply_fails_if_not_accepted(self):
        self.user1.is_following.cache_clear()

        response = self._send_message(self.user1, self.user2, "Hi")
        self.assertEqual(201, response.status_code)
        response = self._send_message(self.user2, self.user1, "Yo")
        self.assertEqual(403, response.status_code)

    def test_message_ok_if_previous_request_case_1(self):
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
        # User does not allow messages from strangers
        # but previously accepted a request.
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
        self.user1.is_following.cache_clear()
        self.user1.add_following(to_user=self.user2)
        response = self._send_message(self.user2, self.user1, "Hi")

        self.assertEqual(201, response.status_code)

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
