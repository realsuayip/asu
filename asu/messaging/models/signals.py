from functools import partial
from typing import Any

from django.db import transaction
from django.db.models.signals import m2m_changed, post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from asu.messaging.models import Conversation, ConversationRequest, Message

Assignment = Conversation.messages.through
"""m2m model that assigns messages to conversations."""


@receiver(post_save, sender=Message, dispatch_uid="deliver_message")
def deliver_message(instance: Message, created: bool, **kwargs: Any) -> None:
    if not created:
        return

    sender, recipient = instance.sender, instance.recipient

    # If conversation objects between these two people is not created,
    # create them. Otherwise, fetch their ID to perform related assignments.
    holder, _ = sender.conversations.get_or_create(target=recipient)
    target, _ = recipient.conversations.get_or_create(target=sender)

    # Similarly, create a conversation request if not exists. This way, The
    # user has ability to see which conversations are newly requested. Requests
    # are automatically accepted in case recipient follows the sender.
    request, _ = ConversationRequest.objects.compose(sender, recipient)

    if (not request.is_accepted) and instance.has_receipt:
        # Disable read receipts (regardless of user preference) in case
        # the conversation is yet to be accepted.
        instance.has_receipt = False
        instance.save(update_fields=["has_receipt"])

    # Assign messages to conversations. Each conversation tracks the list of
    # messages separately, this way one user can delete a message (or the
    # whole conversation) while the other preserves it.
    Assignment.objects.bulk_create(
        [
            Assignment(conversation=holder, message=instance),
            Assignment(conversation=target, message=instance),
        ]
    )

    # Update modification timestamps for related conversations so that when
    # ordering by modified, conversations with recent activity rise to top.
    Conversation.objects.filter(pk__in=[holder.pk, target.pk]).update(
        date_modified=timezone.now()
    )

    relay = partial(instance.websocket_send, target.pk)
    transaction.on_commit(relay)


@receiver(m2m_changed, sender=Conversation.messages.through)
def delete_orphan_messages_individual(
    action: str, pk_set: list[str], **kwargs: Any
) -> None:
    if (
        action == "post_remove"
        and not Conversation.objects.filter(messages__in=pk_set).exists()
    ):
        Message.objects.filter(pk__in=pk_set).delete()


@receiver(pre_delete, sender=Conversation)
def delete_orphan_messages_bulk(instance: Conversation, **kwargs: Any) -> None:
    instance.messages.remove(*instance.messages.all())
