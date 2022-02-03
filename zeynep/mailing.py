from django.core.mail import EmailMessage
from django.template.loader import render_to_string


def send(template, *, title, content, recipients, context=None):
    # todo add i18n support
    context = context or {}
    context.setdefault("title", title)
    context.setdefault("content", content)

    template = "mailing/%s.html" % template
    body = render_to_string(template, context=context)
    email = EmailMessage(title, body, to=recipients)
    email.content_subtype = "html"
    return email.send()
