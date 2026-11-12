"""E-mails the user sends from their own mail software (annex B of the recette 1 feedback).

The app sends nothing itself: it builds the message and a `mailto:` link that opens it in the
user's mail software, with the recipient, the subject and the text filled in. A `mailto:` cannot
attach a file, so the contract message carries a download link instead.
"""

from urllib.parse import quote

from django.utils.translation import gettext as _

from apps.addressbook.models import Contact
from apps.tenants import message_templates

# Some mail software cuts a link longer than this; the short body is used beyond it.
MAILTO_LIMIT = 1900


def recipient(gig):
    """The first contact of the organiser who has an e-mail address, or None."""
    return (
        Contact.objects.filter(tenant=gig.tenant, promoters=gig.promoter)
        .exclude(email="")
        .order_by("name")
        .first()
    )


def status_label(gig):
    """The "Statut" of the subject line: Option, Confirmé or Annulé (a signed date is confirmed)."""
    if gig.status == gig.Status.OPTION:
        return _("Option")
    if gig.status == gig.Status.CANCELLED:
        return _("Annulé")
    return _("Confirmé")


def values(gig, contact, link="", sent_on=None):
    """What each `[Variable]` of the message texts stands for, as plain text."""
    when = gig.date.strftime("%d/%m/%Y")
    city = gig.venue.city
    deposit = ""
    phrase = gig.deposit_due_phrase
    if gig.deposit_percent and phrase:
        deposit = _("L'acompte de %(percent)s %% est à régler %(when)s.") % {
            "percent": f"{gig.deposit_percent:g}",
            "when": phrase,
        }
    return {
        "Contact": contact.name if contact else "",
        "Titre du spectacle": gig.show.title,
        "Nom du groupe": gig.tenant.name,
        "Date": when,
        "Ville": city,
        "Date et ville": _("%(date)s à %(city)s") % {"date": when, "city": city} if city else when,
        "Statut": status_label(gig),
        "Lien": link,
        "Acompte": deposit,
        "Date d'envoi": sent_on.strftime("%d/%m/%Y") if sent_on else "",
        "Signature": gig.tenant.name,
    }


def _mailto(to, subject_line, body):
    subject_part, body_part = quote(subject_line, safe=""), quote(body, safe="")
    return f"mailto:{quote(to, safe='@')}?subject={subject_part}&body={body_part}"


def build(gig, link, kind):
    """What the page needs: the link to open the mail software, the text to copy, and what is
    missing (no contact with an e-mail address: the button is replaced by an explanation)."""
    contact = recipient(gig)
    data = values(gig, contact, link)
    subject_line, body = message_templates.render(gig.tenant, kind, data)
    result = {
        "subject": subject_line,
        "body": body,
        "link": link,
        "to": contact.email if contact else "",
        "mailto": "",
    }
    if contact:
        url = _mailto(contact.email, subject_line, body)
        if len(url) > MAILTO_LIMIT:
            short = message_templates.render(gig.tenant, kind, data, short=True)[1]
            url = _mailto(contact.email, subject_line, short)
        result["mailto"] = url
    return result


def form_mail(gig, link):
    return build(gig, link, message_templates.FORM)


def contract_mail(gig, link):
    return build(gig, link, message_templates.CONTRACT)


def reminder_mail(gig, sent_on):
    """The reminder for a contract sent and not signed (B3). No link: the contract is already
    with the organiser."""
    contact = recipient(gig)
    data = values(gig, contact, sent_on=sent_on)
    subject_line, body = message_templates.render(gig.tenant, message_templates.REMINDER, data)
    return {
        "subject": subject_line,
        "body": body,
        "to": contact.email if contact else "",
        "mailto": _mailto(contact.email, subject_line, body) if contact else "",
    }
