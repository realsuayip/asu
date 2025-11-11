from django.core import mail
from django.utils.translation import gettext_lazy as _

from asu.core.utils import mailing


def test_send_mail() -> None:
    mailing.send(
        "empty",
        title="Hello World",
        content="Howdy?",
        recipients=["someone@example.com"],
    )

    email = mail.outbox[0]
    assert len(mail.outbox) == 1
    assert email.subject == "Hello World"
    assert email.body.strip() == "Howdy?"
    assert email.recipients() == ["someone@example.com"]
    assert email.content_subtype == "html"


def test_send_mail_respects_language() -> None:
    mailing.send(
        "empty",
        title=_("German"),
        content=_("Swedish"),
        recipients=["someone@example.com"],
        language="tr",
    )

    email = mail.outbox[0]
    assert email.subject == "Almanca"
    assert email.body.strip() == "İsveççe"
