"""Payment terms of a date as rules ("10 days after the signature"), and the date each gives.

The contract prints a date when the rule gives one and the rule itself otherwise (before the
signature, "10 days after the signature" has no date yet). Pure functions: no database here
(recette n°1, CTR-05; the choices are the lists of the annex A4).
"""

import calendar
import datetime

from django.db import models
from django.utils.translation import gettext_lazy as _


class DepositTerm(models.TextChoices):
    AT_SIGNATURE = "at_signature", _("À la signature du contrat")
    SIGNATURE_PLUS_10 = "signature_plus_10", _("10 jours après la signature")
    SIGNATURE_PLUS_30 = "signature_plus_30", _("30 jours après la signature")
    END_OF_SIGNATURE_MONTH = "end_of_signature_month", _("Fin du mois de signature")
    DAYS_BEFORE = "days_before", _("Un nombre de jours avant la prestation")
    SPECIFIC = "specific", _("Date précise")


class BalanceTerm(models.TextChoices):
    ON_PERFORMANCE_DAY = "on_performance_day", _("Le jour de la prestation")
    AFTER_ON_INVOICE = "after_on_invoice", _("À l'issue de la prestation, sur facture")
    PERFORMANCE_PLUS_15 = "performance_plus_15", _("15 jours après la prestation")
    PERFORMANCE_PLUS_30 = "performance_plus_30", _("30 jours après la prestation")
    END_OF_NEXT_MONTH = "end_of_next_month", _("Fin du mois suivant la prestation")
    SPECIFIC = "specific", _("Date précise")


# What the contract says. A date known in advance follows it: "15 jours après la prestation,
# soit le 30/03/2027".
DEPOSIT_PHRASES = {
    DepositTerm.AT_SIGNATURE: "à la signature du contrat",
    DepositTerm.SIGNATURE_PLUS_10: "10 jours après la signature du contrat",
    DepositTerm.SIGNATURE_PLUS_30: "30 jours après la signature du contrat",
    DepositTerm.END_OF_SIGNATURE_MONTH: "à la fin du mois de signature du contrat",
}
BALANCE_PHRASES = {
    BalanceTerm.ON_PERFORMANCE_DAY: "le jour de la prestation",
    BalanceTerm.AFTER_ON_INVOICE: "à l'issue de la prestation, sur facture",
    BalanceTerm.PERFORMANCE_PLUS_15: "15 jours après la prestation",
    BalanceTerm.PERFORMANCE_PLUS_30: "30 jours après la prestation",
    BalanceTerm.END_OF_NEXT_MONTH: "à la fin du mois suivant la prestation",
}


def _end_of_month(day):
    return day.replace(day=calendar.monthrange(day.year, day.month)[1])


def _end_of_next_month(day):
    return _end_of_month((day.replace(day=1) + datetime.timedelta(days=32)).replace(day=1))


def deposit_date(term, days, performance_date, signed_on):
    """The day the deposit is due, or None when the rule has no date yet (not signed)."""
    after = datetime.timedelta
    if term == DepositTerm.AT_SIGNATURE:
        return signed_on
    if term == DepositTerm.SIGNATURE_PLUS_10:
        return signed_on and signed_on + after(days=10)
    if term == DepositTerm.SIGNATURE_PLUS_30:
        return signed_on and signed_on + after(days=30)
    if term == DepositTerm.END_OF_SIGNATURE_MONTH:
        return signed_on and _end_of_month(signed_on)
    if term == DepositTerm.DAYS_BEFORE:
        return performance_date - after(days=days) if days is not None else None
    return None


def balance_date(term, performance_date):
    """The day the balance is due, or None for "Date précise" (typed by hand)."""
    after = datetime.timedelta
    if term in (BalanceTerm.ON_PERFORMANCE_DAY, BalanceTerm.AFTER_ON_INVOICE):
        return performance_date
    if term == BalanceTerm.PERFORMANCE_PLUS_15:
        return performance_date + after(days=15)
    if term == BalanceTerm.PERFORMANCE_PLUS_30:
        return performance_date + after(days=30)
    if term == BalanceTerm.END_OF_NEXT_MONTH:
        return _end_of_next_month(performance_date)
    return None


def deposit_short(term, days, due_on):
    """The deposit date for a screen: "12/11/2026", the rule while it has no date, or ""."""
    if due_on:
        return f"{due_on:%d/%m/%Y}"
    if term == DepositTerm.SPECIFIC:
        return ""
    if term == DepositTerm.DAYS_BEFORE:
        return f"{days} j avant la prestation" if days is not None else ""
    return str(DepositTerm(term).label)


def balance_short(term, due_on):
    if due_on:
        return f"{due_on:%d/%m/%Y}"
    return "" if term == BalanceTerm.SPECIFIC else str(BalanceTerm(term).label)


def deposit_phrase(term, days, due_on):
    """ "à la signature du contrat", "le 12/11/2026"…, or "" when nothing is set."""
    if term == DepositTerm.DAYS_BEFORE:
        if days is None:
            return ""
        unit = "jour" if days == 1 else "jours"
        rule = f"{days} {unit} avant la prestation"
    elif term == DepositTerm.SPECIFIC:
        return f"le {due_on:%d/%m/%Y}" if due_on else ""
    else:
        rule = DEPOSIT_PHRASES[term]
    return f"{rule}, soit le {due_on:%d/%m/%Y}" if due_on else rule


def balance_phrase(term, due_on):
    if term == BalanceTerm.SPECIFIC:
        return f"le {due_on:%d/%m/%Y}" if due_on else ""
    rule = BALANCE_PHRASES[term]
    return f"{rule}, soit le {due_on:%d/%m/%Y}" if due_on else rule
