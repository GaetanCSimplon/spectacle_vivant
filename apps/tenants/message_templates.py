"""The e-mails the user sends from their own mail software, and the texts they can rewrite.

Four messages (annex B of the recette 1 feedback). Each has a default subject and text written
with `[Variables]`; the structure may replace them (`MessageTemplate`). A variable is only
replaced by plain text, never read as code, and a text that uses an unknown one is refused when
it is saved. Without a saved text, the default is used: nothing changes until the user edits.
"""

import re

from django.utils.translation import gettext_lazy as _

from .models import MessageTemplate

SUBJECT_MAX = 200
BODY_MAX = 2000

FORM = MessageTemplate.Kind.FORM
CONTRACT = MessageTemplate.Kind.CONTRACT
REMINDER = MessageTemplate.Kind.REMINDER
INFO = MessageTemplate.Kind.INFO

# What each variable stands for (shown next to the editor).
MEANING = {
    "Contact": _("le nom du contact qui reçoit le message"),
    "Titre du spectacle": _("le titre du spectacle"),
    "Nom du groupe": _("le nom de votre structure"),
    "Date": _("la date du concert (jj/mm/aaaa)"),
    "Ville": _("la ville du lieu"),
    "Date et ville": _("la date, suivie de « à » et de la ville si elle est connue"),
    "Statut": _("Option, Confirmé ou Annulé"),
    "Lien": _("le lien à ouvrir (valable 7 jours)"),
    "Acompte": _("la phrase sur l'acompte, vide s'il n'y en a pas"),
    "Date d'envoi": _("la date d'envoi du contrat"),
    "Signature": _("votre signature (le nom de votre structure)"),
}

_COMMON = [
    "Contact",
    "Titre du spectacle",
    "Nom du groupe",
    "Date",
    "Ville",
    "Date et ville",
    "Statut",
    "Signature",
]
VARIABLES = {
    FORM: [*_COMMON, "Lien"],
    CONTRACT: [*_COMMON, "Lien", "Acompte"],
    REMINDER: [*_COMMON, "Date d'envoi"],
    INFO: ["Contact", "Nom du groupe", "Lien", "Signature"],
}

LABELS = {
    FORM: _("Formulaire de l'organisateur"),
    CONTRACT: _("Envoi du contrat"),
    REMINDER: _("Relance d'un contrat non signé"),
    INFO: _("Formulaire d'un contact ou d'un membre de l'équipe"),
}

_SIGNATURE = "Bien cordialement,\n[Signature]"
_PREFIX = "[Titre du spectacle] – [Nom du groupe] – [Date]"

DEFAULTS = {
    FORM: {
        "subject": (_PREFIX + " – [Statut] – Informations organisateur"),
        "body": (
            "Bonjour [Contact],\n\n"
            "Suite à nos échanges au sujet de [Titre du spectacle] ([Nom du groupe]) le "
            "[Date et ville], je vous remercie de compléter ce formulaire en ligne :\n\n[Lien]\n\n"
            "Il nous permettra d'établir le contrat de cession et la feuille de route. "
            "Comptez environ 5 minutes. Seront demandés : coordonnées légales de votre "
            "structure (SIRET, adresse, représentant légal, licence d'entrepreneur de "
            "spectacles) et vos contacts (administration, technique, accueil).\n\n"
            "Je reste à votre disposition pour toute question.\n\n"
        )
        + _SIGNATURE,
        "short": ("Bonjour [Contact],\n\nMerci de compléter ce formulaire en ligne :\n\n[Lien]\n\n")
        + _SIGNATURE,
    },
    CONTRACT: {
        "subject": (_PREFIX + " – [Statut] – Contrat de cession"),
        "body": (
            "Bonjour [Contact],\n\n"
            "Vous trouverez ci-dessous le lien pour télécharger le contrat de cession pour "
            "[Titre du spectacle] le [Date et ville] :\n\n[Lien]\n\n(Ce lien est valable 7 jours.)"
            "\n\nMerci de nous le retourner signé dès que possible. [Acompte]\n\n"
        )
        + _SIGNATURE,
        "short": (
            "Bonjour [Contact],\n\n"
            "Vous trouverez ci-dessous le lien pour télécharger le contrat de cession pour "
            "[Titre du spectacle] le [Date et ville] :\n\n[Lien]\n\n(Ce lien est valable 7 jours.)"
            "\n\n"
        )
        + _SIGNATURE,
    },
    REMINDER: {
        "subject": (_PREFIX + " – Relance contrat de cession"),
        "body": (
            "Bonjour [Contact],\n\nSauf erreur de ma part, nous n'avons pas encore reçu le "
            "contrat signé pour [Titre du spectacle] le [Date], envoyé le [Date d'envoi]. "
            "Pourriez-vous nous le retourner dès que possible ?\n\n"
        )
        + _SIGNATURE,
    },
    INFO: {
        "subject": ("Vos informations – [Nom du groupe]"),
        "body": (
            "Bonjour [Contact],\n\nMerci de compléter vos informations en ligne :\n\n[Lien]\n\n"
            "(Ce lien est valable 7 jours.)\n\n"
        )
        + _SIGNATURE,
    },
}

_VARIABLE = re.compile(r"\[([^\[\]\n]+)\]")


def used_variables(text):
    return _VARIABLE.findall(text or "")


def unknown_variables(kind, text):
    """The bracketed words of `text` that are not variables of this message (in order, once)."""
    known = VARIABLES[kind]
    found = []
    for name in used_variables(text):
        if name not in known and name not in found:
            found.append(name)
    return found


def fill(text, values):
    """Replace each known `[Variable]` by its plain text, in one pass (a value is never
    searched again for variables), then tidy what an empty value leaves behind."""
    text = _VARIABLE.sub(lambda m: str(values.get(m.group(1), m.group(0))), str(text))
    text = re.sub(r" +,", ",", text)  # "Bonjour [Contact]," without a contact
    text = "\n".join(line.rstrip() for line in text.splitlines())
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def default(kind):
    return {key: str(value) for key, value in DEFAULTS[kind].items()}


def resolve(tenant, kind):
    """The subject and texts to use: the structure's own if it wrote some, else the defaults."""
    texts = default(kind)
    saved = MessageTemplate.objects.filter(tenant=tenant, kind=kind).first()
    if saved:
        texts["subject"], texts["body"] = saved.subject, saved.body
    return texts


def render(tenant, kind, values, short=False):
    texts = resolve(tenant, kind)
    body = texts["short"] if short and "short" in texts else texts["body"]
    return fill(texts["subject"], values), fill(body, values)


SAMPLE = {
    "Contact": "Marie Durand",
    "Titre du spectacle": "Nuit blanche",
    "Nom du groupe": "Les Cigales",
    "Date": "12/10/2027",
    "Ville": "Lyon",
    "Date et ville": "12/10/2027 à Lyon",
    "Statut": "Confirmé",
    "Lien": "https://…/lien-valable-7-jours",
    "Acompte": "L'acompte de 30 % est à régler à la signature.",
    "Date d'envoi": "01/10/2027",
    "Signature": "Les Cigales",
}


def preview(subject, body):
    """The text as the recipient would read it, with example values."""
    return fill(subject, SAMPLE), fill(body, SAMPLE)


def sections(tenant):
    """What the settings page shows for each message: texts in use, the variables, and whether
    the structure wrote its own."""
    saved = {t.kind: t for t in MessageTemplate.objects.filter(tenant=tenant)}
    result = []
    for kind in MessageTemplate.Kind.values:
        texts = resolve(tenant, kind)
        result.append(
            {
                "kind": kind,
                "label": LABELS[kind],
                "custom": kind in saved,
                "texts": texts,
                "variables": [(name, MEANING[name]) for name in VARIABLES[kind]],
            }
        )
    return result
