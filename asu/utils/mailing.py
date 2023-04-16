from typing import Any

from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from django_stubs_ext import StrOrPromise


def send(
    template: str,
    *,
    title: StrOrPromise,
    content: StrOrPromise,
    recipients: list[str],
    context: dict[str, Any] | None = None,
) -> int:
    # todo add i18n support
    context = context or {}
    context.setdefault("title", title)
    context.setdefault("content", content)

    template = "mailing/%s.html" % template
    body = render_to_string(template, context=context)
    email = EmailMessage(title, body, to=recipients)
    email.content_subtype = "html"
    return email.send()
