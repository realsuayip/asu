from __future__ import annotations

from typing import Any

from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.encoding import force_str

from django_stubs_ext import StrOrPromise

from asu.core.celery import app

__all__ = ["send"]


def _send_sync(
    template: str,
    *,
    title: StrOrPromise,
    content: StrOrPromise = "",
    recipients: list[str],
    context: dict[str, Any] | None = None,
    language: str,
) -> int:
    context = context or {}
    context.setdefault("title", title)
    context.setdefault("content", content)

    template = "mailing/%s.html" % template

    with translation.override(language):
        body = render_to_string(template, context=context)
        email = EmailMessage(force_str(title), body, to=recipients)

    email.content_subtype = "html"
    return email.send()


@app.task(name="asu.core.utils.tasks.send_mail")
def _send_async(*args: Any, **kwargs: Any) -> int:
    return _send_sync(*args, **kwargs)


def send(
    template: str,
    *,
    title: StrOrPromise,
    content: StrOrPromise = "",
    recipients: list[str],
    context: dict[str, Any] | None = None,
    language: str | None = None,
    sync: bool = False,
) -> int:
    language = language or translation.get_language()
    with translation.override(language):
        args: Any = [template]
        kwargs: Any = {
            "title": force_str(title),
            "content": force_str(content),
            "recipients": recipients,
            "context": context,
            "language": language,
        }
    if sync:
        return _send_sync(*args, **kwargs)
    _send_async.apply_async(args=args, kwargs=kwargs)
    return 0
