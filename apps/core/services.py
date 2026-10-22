from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from weasyprint import HTML


def render_pdf(template_name, context=None):
    """Render a Django template to PDF bytes via WeasyPrint."""
    html = render_to_string(template_name, context or {})
    return HTML(string=html).write_pdf()


CONTACT_WINDOW = 3600


def contact_quota_left():
    """False once too many contact messages went out this hour (the whole site, not per person).

    The visitor's address is not reliable behind the host's proxy, so the cap is global: it
    protects the inbox and the e-mail quota from a flood. The cache is per process, so the
    real ceiling is the limit times the number of workers.
    """
    key = "contact-messages-sent"
    cache.add(key, 0, CONTACT_WINDOW)
    return cache.get(key, 0) < settings.CONTACT_HOURLY_LIMIT


def send_contact_message(name, email, message):
    """E-mail a message from the contact form to the team. Nothing is stored.

    The sender is our own address (a visitor's address would fail the SPF check); the
    visitor's address is the reply-to. Raises OSError (incl. SMTP errors) when it cannot send.
    """
    mail = EmailMessage(
        subject="[Bòrd Pro] Message depuis le site",
        body=f"De : {name} <{email}>\n\n{message}\n",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.CONTACT_EMAIL],
        reply_to=[email],
    )
    mail.send()
    try:
        cache.incr("contact-messages-sent")
    except ValueError:
        cache.set("contact-messages-sent", 1, CONTACT_WINDOW)
