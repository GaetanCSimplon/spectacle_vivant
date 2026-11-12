"""E-mails the user sends from their own mail software (annex B of the recette 1 feedback).

The app sends nothing itself: it builds the message and a `mailto:` link that opens it in the
user's mail software, with the recipient, the subject and the text filled in. A `mailto:` cannot
attach a file, so the contract message carries a download link instead.
"""

from urllib.parse import quote

from django.utils.translation import gettext as _

from apps.addressbook.models import Contact

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


def subject(gig, topic):
    parts = [
        gig.show.title,
        gig.tenant.name,
        gig.date.strftime("%d/%m/%Y"),
        status_label(gig),
        topic,
    ]
    return " – ".join(parts)


def _greeting(contact):
    return _("Bonjour %(name)s,") % {"name": contact.name} if contact else _("Bonjour,")


def _signature(gig):
    return _("Bien cordialement,\n%(name)s") % {"name": gig.tenant.name}


def _where(gig):
    return _(" à %(city)s") % {"city": gig.venue.city} if gig.venue.city else ""


def form_body(gig, link, contact, short=False):
    when = gig.date.strftime("%d/%m/%Y")
    if short:
        middle = _("Merci de compléter ce formulaire en ligne :\n\n%(link)s") % {"link": link}
    else:
        middle = _(
            "Suite à nos échanges au sujet de %(show)s (%(group)s) le %(date)s%(where)s, "
            "je vous remercie de compléter ce formulaire en ligne :\n\n%(link)s\n\n"
            "Il nous permettra d'établir le contrat de cession et la feuille de route. "
            "Comptez environ 5 minutes. Seront demandés : coordonnées légales de votre "
            "structure (SIRET, adresse, représentant légal, licence d'entrepreneur de "
            "spectacles) et vos contacts (administration, technique, accueil).\n\n"
            "Je reste à votre disposition pour toute question."
        ) % {
            "show": gig.show.title,
            "group": gig.tenant.name,
            "date": when,
            "where": _where(gig),
            "link": link,
        }
    return f"{_greeting(contact)}\n\n{middle}\n\n{_signature(gig)}"


def contract_body(gig, link, contact, short=False):
    when = gig.date.strftime("%d/%m/%Y")
    intro = _(
        "Vous trouverez ci-dessous le lien pour télécharger le contrat de cession pour "
        "%(show)s le %(date)s%(where)s :\n\n%(link)s\n\n(Ce lien est valable 7 jours.)"
    ) % {"show": gig.show.title, "date": when, "where": _where(gig), "link": link}
    if short:
        return f"{_greeting(contact)}\n\n{intro}\n\n{_signature(gig)}"
    asks = _("Merci de nous le retourner signé dès que possible.")
    deposit = ""
    phrase = gig.deposit_due_phrase
    if gig.deposit_percent and phrase:
        deposit = " " + _("L'acompte de %(percent)s %% est à régler %(when)s.") % {
            "percent": f"{gig.deposit_percent:g}",
            "when": phrase,
        }
    return f"{_greeting(contact)}\n\n{intro}\n\n{asks}{deposit}\n\n{_signature(gig)}"


def _mailto(to, subject_line, body):
    subject_part, body_part = quote(subject_line, safe=""), quote(body, safe="")
    return f"mailto:{quote(to, safe='@')}?subject={subject_part}&body={body_part}"


def build(gig, link, topic, body_builder):
    """What the page needs: the link to open the mail software, the text to copy, and what is
    missing (no contact with an e-mail address: the button is replaced by an explanation)."""
    contact = recipient(gig)
    subject_line = subject(gig, topic)
    body = body_builder(gig, link, contact)
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
            url = _mailto(contact.email, subject_line, body_builder(gig, link, contact, short=True))
        result["mailto"] = url
    return result


def form_mail(gig, link):
    return build(gig, link, _("Informations organisateur"), form_body)


def contract_mail(gig, link):
    return build(gig, link, _("Contrat de cession"), contract_body)


def reminder_body(gig, sent_on, contact):
    return _(
        "%(greeting)s\n\nSauf erreur de ma part, nous n'avons pas encore reçu le contrat signé "
        "pour %(show)s le %(date)s, envoyé le %(sent)s. Pourriez-vous nous le retourner dès que "
        "possible ?\n\n%(signature)s"
    ) % {
        "greeting": _greeting(contact),
        "show": gig.show.title,
        "date": gig.date.strftime("%d/%m/%Y"),
        "sent": sent_on.strftime("%d/%m/%Y"),
        "signature": _signature(gig),
    }


def reminder_mail(gig, sent_on):
    """The reminder for a contract sent and not signed (B3). No link: the contract is already
    with the organiser. The subject has no status, as in the model."""
    contact = recipient(gig)
    subject_line = " – ".join(
        [
            gig.show.title,
            gig.tenant.name,
            gig.date.strftime("%d/%m/%Y"),
            _("Relance contrat de cession"),
        ]
    )
    body = reminder_body(gig, sent_on, contact)
    return {
        "subject": subject_line,
        "body": body,
        "to": contact.email if contact else "",
        "mailto": _mailto(contact.email, subject_line, body) if contact else "",
    }
