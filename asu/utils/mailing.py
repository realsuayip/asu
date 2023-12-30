from __future__ import annotations

from typing import Any

from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.encoding import force_str

from django_stubs_ext import StrOrPromise


def send(
    template: str,
    *,
    title: StrOrPromise,
    content: StrOrPromise,
    recipients: list[str],
    context: dict[str, Any] | None = None,
    lang_code: str | None = None,
) -> int:
    language = lang_code or translation.get_language()

    context = context or {}
    context.setdefault("title", title)
    context.setdefault("content", content)

    template = "mailing/%s.html" % template

    with translation.override(language):
        body = render_to_string(template, context=context)
        email = EmailMessage(force_str(title), body, to=recipients)

    email.content_subtype = "html"
    return email.send()
