from typing import TYPE_CHECKING, Any

from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import translation

if TYPE_CHECKING:
    from django_stubs_ext import StrOrPromise


def determine_language(lang_code: str | None) -> str:
    current = translation.get_language()
    if lang_code is None:
        return current

    try:
        return translation.get_supported_language_variant(lang_code)
    except LookupError:
        return current


def send(
    template: str,
    *,
    title: "StrOrPromise",
    content: "StrOrPromise",
    recipients: list[str],
    context: dict[str, Any] | None = None,
    lang_code: str | None = None,
) -> int:
    language = determine_language(lang_code)

    context = context or {}
    context.setdefault("title", title)
    context.setdefault("content", content)

    template = "mailing/%s.html" % template

    with translation.override(language):
        body = render_to_string(template, context=context)

    email = EmailMessage(title, body, to=recipients)
    email.content_subtype = "html"
    return email.send()
