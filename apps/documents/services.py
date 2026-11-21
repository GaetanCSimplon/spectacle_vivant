import datetime
import secrets
from decimal import ROUND_HALF_UP, Decimal

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from django.utils.formats import number_format
from django.utils.translation import gettext_lazy as _

from apps.core.services import render_pdf
from apps.gigs import hospitality
from apps.gigs import services as gig_services
from apps.gigs.models import Gig
from apps.tenants import logo as logo_files
from apps.tenants.models import Tenant

from . import annexes as annex_files
from . import checks
from .invoicing import money, vat_mentions
from .models import (
    Contract,
    ContractSequence,
    ContractShareLink,
    ContractVariant,
    ContractVersion,
)

TWO_PLACES = Decimal("0.01")

CONTRACT_TEMPLATE = "documents/contracts/contract.html"
BLANK = "……"


def contract_variant(tenant):
    """Article 5 with or without VAT: only the VAT regime of the structure decides (spec 03, D1)."""
    if tenant.vat_regime == Tenant.VatRegime.TAXABLE:
        return ContractVariant.WITH_VAT
    return ContractVariant.WITHOUT_VAT


ContractAnnexError = annex_files.ContractAnnexError

NO_ANNEXES = _("Régénérez le contrat : cette version ne contient pas ses annexes.")


class ContractNotAvailable(Exception):
    """A contract cannot be produced for a cancelled gig."""


class ContractSigningError(Exception):
    """The contract cannot be marked as signed (or get its signed PDF) right now."""


def _compute_vat(gig, tenant):
    """Return (vat_amount, total_with_vat), or (None, None) if the rate is not known yet."""
    if tenant.vat_regime != Tenant.VatRegime.TAXABLE or tenant.vat_rate is None:
        return None, None

    vat_amount = (gig.price * Decimal(tenant.vat_rate) / Decimal("100")).quantize(
        TWO_PLACES, rounding=ROUND_HALF_UP
    )
    return vat_amount, gig.price + vat_amount


def payment_schedule(gig):
    """Deposit, balance and total of the price, with and without VAT (None when unknown).

    The deposit follows the gig's `deposit_percent`; the balance is what is left, so that
    the two always add up to the total, to the cent.
    """
    tenant = gig.tenant
    price = money(gig.price)
    deposit_ht = money(price * Decimal(str(gig.deposit_percent)) / 100)
    balance_ht = price - deposit_ht
    if tenant.vat_regime != Tenant.VatRegime.TAXABLE:
        total_ttc, deposit_ttc = price, deposit_ht
    elif tenant.vat_rate is None:
        total_ttc = deposit_ttc = None
    else:
        factor = 1 + Decimal(tenant.vat_rate) / 100
        total_ttc = money(price * factor)
        deposit_ttc = money(deposit_ht * factor)
    return {
        "deposit_ht": deposit_ht,
        "deposit_ttc": deposit_ttc,
        "balance_ht": balance_ht,
        "balance_ttc": None if total_ttc is None else total_ttc - deposit_ttc,
        "total_ht": price,
        "total_ttc": total_ttc,
    }


def _licence_text(obj):
    """The licence line: the number with its categories and validity, or the reason for a waiver."""
    if obj.licence_exempt:
        reason = obj.licence_exemption_reason
        return f"dispense de licence ({reason})" if reason else "dispense de licence"
    parts = [obj.licence_number, obj.licence_categories]
    if getattr(obj, "licence_valid_until", None):
        parts.append(f"valable jusqu'au {obj.licence_valid_until:%d/%m/%Y}")
    return ", ".join(part for part in parts if part)


def build_fiscal_snapshot(tenant):
    """The fiscal regime the contract is written with, frozen with each version (spec 03, §2.3)."""
    regime = tenant.vat_regime
    taxable = regime == Tenant.VatRegime.TAXABLE
    mention = tenant.vat_exemption_note or " ".join(vat_mentions(regime))
    return {
        "regime": regime,
        # "20" or "5,5": the French way, without trailing zeros.
        "rate": f"{Decimal(str(tenant.vat_rate)).normalize():f}".replace(".", ",")
        if taxable and tenant.vat_rate is not None
        else "",
        "mention": mention,
        "vat_number": tenant.vat_number,
        "taken_on": timezone.localdate().isoformat(),
    }


def build_parties_snapshot(gig, contract=None):
    """Who signs, as written in the contract: producer (the tenant) and organiser."""
    tenant, promoter = gig.tenant, gig.promoter
    producer_name = (contract and contract.signatory_name) or tenant.representative_name
    producer_role = (contract and contract.signatory_role) or tenant.representative_role
    return {
        "producer": {
            "name": tenant.name,
            "legal_form": tenant.legal_form,
            "address": tenant.one_line_address,
            "siret": tenant.siret,
            "signatory_name": producer_name,
            "signatory_role": producer_role,
            "licence": _licence_text(tenant),
            "contact_name": tenant.contact_name,
            "contact_email": tenant.email,
            "contact_phone": tenant.phone,
        },
        "organiser": {
            "name": promoter.name,
            "legal_form": promoter.legal_form or ("Particulier" if promoter.is_private else ""),
            "address": promoter.one_line_address,
            "siret": promoter.siret,
            "is_private": promoter.is_private,
            "signatory_name": promoter.representative_name,
            "signatory_role": promoter.representative_role,
            "licence": _licence_text(promoter),
            "contact_name": promoter.admin_contact_name,
            "contact_email": promoter.admin_contact_email or promoter.email,
            "contact_phone": promoter.admin_contact_phone or promoter.phone,
        },
    }


def _payment_text(gig, payment, variant):
    """The schedule sentence of article 5 (a deposit and a balance, or a single payment)."""
    with_vat = variant == ContractVariant.WITH_VAT

    def amount(ht, ttc):
        if with_vat and ttc is not None:
            return f"{number_format(ttc, decimal_pos=2)} € TTC"
        if with_vat:
            return f"{number_format(ht, decimal_pos=2)} € HT"
        return f"{number_format(ht, decimal_pos=2)} € net de TVA"

    balance_when = gig.balance_due_phrase
    if gig.deposit_required:
        deposit = f"Acompte de {amount(payment['deposit_ht'], payment['deposit_ttc'])}"
        if gig.deposit_due_phrase:
            deposit += f", exigible {gig.deposit_due_phrase}"
        balance = f"Solde de {amount(payment['balance_ht'], payment['balance_ttc'])}"
        if balance_when:
            balance += f", exigible {balance_when}"
        return f"{deposit}. {balance}."
    total = f"Paiement de {amount(payment['total_ht'], payment['total_ttc'])}"
    return f"{total}, exigible {balance_when}." if balance_when else f"{total}."


def _outdoor_clause(gig):
    if gig.setting != Gig.Setting.OUTDOOR:
        return "Sans objet : la représentation a lieu en intérieur."
    parts = [str(gig.get_outdoor_fallback_display())]
    for label, text in (
        ("Modalités du repli", gig.outdoor_fallback_details),
        ("Décision de maintien, de report ou d'arrêt", gig.outdoor_procedure),
        ("Référents des deux parties", gig.outdoor_referents),
        ("Conditions financières", gig.outdoor_financial_terms),
    ):
        if text.strip():
            parts.append(f"{label} : {' '.join(text.split())}")
    return " ".join(part if part.endswith(".") else part + "." for part in parts if part)


def _transport_text(gig):
    covered = hospitality.compose(gig.transport_covered_by, None, None, gig.transport_notes)
    return ". ".join(part for part in (covered, gig.local_transport) if part)


def _extra_fees_text(gig):
    if not gig.extra_fees_description.strip():
        return "Aucun"
    amount = (
        f" ({number_format(gig.extra_fees_amount, decimal_pos=2)} €)"
        if gig.extra_fees_amount is not None
        else ""
    )
    return f"{gig.extra_fees_description.strip()}{amount}"


def contract_key_facts(gig):
    """What a contract states that a later change of the date can contradict (RAD-11)."""
    return {
        "price": f"{Decimal(gig.price):.2f}",
        "date": gig.date.isoformat(),
        "venue_id": gig.venue_id,
        "venue": gig.venue.name,
    }


def build_contract_context(
    gig, contract=None, draft_anomalies=None, snapshots=None, version=None, annexes=None
):
    """Everything the contract template reads; `snapshots` = (fiscal, parties) of a version."""
    variant = contract_variant(gig.tenant)
    fiscal, parties = snapshots or (
        build_fiscal_snapshot(gig.tenant),
        build_parties_snapshot(gig, contract),
    )
    payment = payment_schedule(gig)
    vat_amount, _total = _compute_vat(gig, gig.tenant)
    return {
        "variant": variant,
        "with_vat": variant == ContractVariant.WITH_VAT,
        "fiscal": fiscal,
        "parties": parties,
        "payment": payment,
        "vat_amount": vat_amount,
        "payment_text": _payment_text(gig, payment, variant),
        "outdoor_clause": _outdoor_clause(gig),
        "transport_text": _transport_text(gig),
        "extra_fees_text": _extra_fees_text(gig),
        "reference": contract.reference if contract and contract.reference else "Brouillon",
        "version": version,
        "annexes": annexes or {},
        "contract": contract,
        "gig": gig,
        "tenant": gig.tenant,
        "logo_uri": logo_files.data_uri(gig.tenant.logo.name),
        "promoter": gig.promoter,
        "venue": gig.venue,
        "show": gig.show,
        "today": timezone.localdate(),
        # Set only for a preview of a contract that cannot be generated yet (spec 03, §10).
        "draft_anomalies": draft_anomalies,
    }


def build_annexes(gig):
    """The annexes of a date as of today: ({key: description}, [pdf bytes])."""
    return annex_files.build_annexes(gig, timezone.localdate(), _transport_text(gig))


def render_contract_pdf(gig, contract=None, draft_anomalies=None, snapshots=None, version=None):
    """The contract and its annexes as one PDF, without storing anything (used for the preview).

    Raises ContractAnnexError if an annex cannot be read: never a silently incomplete file.
    """
    descriptions, pdfs = build_annexes(gig)
    context = build_contract_context(
        gig, contract, draft_anomalies, snapshots, version, annexes=descriptions
    )
    return annex_files.assemble(render_pdf(CONTRACT_TEMPLATE, context), pdfs), descriptions


def next_contract_reference(tenant):
    """Hand out the next contract reference of the year, e.g. C-2026-007.

    Must run inside the transaction that creates the contract: the sequence row is
    locked, and a rollback gives the number back, so there is never a gap.
    """
    year = timezone.localdate().year
    ContractSequence.objects.get_or_create(tenant=tenant, year=year)
    sequence = ContractSequence.objects.select_for_update().get(tenant=tenant, year=year)
    sequence.last_number += 1
    sequence.save(update_fields=["last_number"])
    return f"C-{year}-{sequence.last_number:03d}"


def generate_contract_pdf(gig, user=None):
    """Render the contract PDF for a gig and store it as a new version.

    Each call adds a version; older ones are kept. A signed contract keeps its
    figée PDF: it is never regenerated (RG-08). A cancelled gig gets no new
    contract: an existing one stays as it is.
    """
    with transaction.atomic():
        contract = Contract.objects.select_for_update().filter(gig=gig, tenant=gig.tenant).first()
        if contract and contract.status == Contract.Status.SIGNED:
            return contract
        if gig.status == Gig.Status.CANCELLED:
            if contract and contract.latest_version:
                return contract
            raise ContractNotAvailable
        if contract is None:
            contract = Contract.objects.create(gig=gig, tenant=gig.tenant)
        if not contract.reference:
            contract.reference = next_contract_reference(gig.tenant)
            contract.save(update_fields=["reference"])

        latest = contract.latest_version
        number = latest.number + 1 if latest else 1
        snapshots = (build_fiscal_snapshot(gig.tenant), build_parties_snapshot(gig, contract))
        pdf_bytes, descriptions = render_contract_pdf(
            gig, contract, snapshots=snapshots, version=number
        )
        version = ContractVersion(
            tenant=gig.tenant,
            contract=contract,
            number=number,
            created_by=user,
            variant=contract_variant(gig.tenant),
            fiscal_snapshot=snapshots[0],
            parties_snapshot=snapshots[1],
            annexes_snapshot=list(descriptions.values()),
            facts_fingerprint=checks.facts_fingerprint(gig, contract),
            key_facts=contract_key_facts(gig),
        )
        version.pdf_file.save(f"{contract.reference}-v{number}.pdf", ContentFile(pdf_bytes))
        # The version that was sent is no longer the latest one.
        if contract.sent_at:
            contract.sent_at = None
            contract.save(update_fields=["sent_at"])
    return contract


def mark_contract_sent(gig):
    """Record that the latest version was sent to the promoter (the app sends nothing itself)."""
    with transaction.atomic():
        contract = Contract.objects.select_for_update().filter(gig=gig, tenant=gig.tenant).first()
        if contract is None or contract.latest_version is None:
            raise ContractSigningError(_("Générez d'abord le contrat avant de le marquer envoyé."))
        if not contract.latest_version.annexes_snapshot:
            raise ContractSigningError(NO_ANNEXES)
        if contract.status == Contract.Status.SIGNED:
            raise ContractSigningError(_("Ce contrat est signé : il est déjà envoyé."))
        contract.sent_at = timezone.now()
        contract.save(update_fields=["sent_at"])
    return contract


def unmark_contract_sent(gig):
    """Take the "sent" mark back (a mistaken click). A signed contract keeps it."""
    with transaction.atomic():
        contract = Contract.objects.select_for_update().filter(gig=gig, tenant=gig.tenant).first()
        if contract is None:
            raise ContractSigningError(_("Contrat introuvable."))
        if contract.status == Contract.Status.SIGNED:
            raise ContractSigningError(_("Ce contrat est signé : il ne peut plus être modifié."))
        contract.sent_at = None
        contract.save(update_fields=["sent_at"])
    return contract


def mark_contract_signed(gig, signed_pdf=None):
    """Freeze the latest version as the signed contract and move the gig to `signed`.

    The signature itself happens outside the app (RG-08: from now on the PDF never
    changes). Everything happens in one transaction: either the contract and the
    gig are both signed, or nothing is.
    """
    with transaction.atomic():
        contract = Contract.objects.select_for_update().filter(gig=gig, tenant=gig.tenant).first()
        if contract is None or contract.latest_version is None:
            raise ContractSigningError(_("Générez d'abord le contrat avant de le marquer signé."))
        if contract.status == Contract.Status.SIGNED:
            raise ContractSigningError(_("Ce contrat est déjà signé."))
        if gig.status != Gig.Status.CONFIRMED:
            raise ContractSigningError(
                _("La date doit être confirmée avant de marquer le contrat signé.")
            )
        try:
            gig_services.change_status(gig, Gig.Status.SIGNED)
        except gig_services.InvalidTransition as error:
            raise ContractSigningError(error.args[0]) from error

        contract.status = Contract.Status.SIGNED
        contract.signed_at = timezone.now()
        contract.signed_version = contract.latest_version
        if signed_pdf:
            contract.signed_pdf = signed_pdf
        contract.save()
        # The deposit due "10 days after the signature" now has its date.
        gig_services.refresh_due_dates(gig)
    return contract


def attach_signed_pdf(gig, signed_pdf):
    """Add the scan of the signed contract afterwards. It is added once, never replaced."""
    with transaction.atomic():
        contract = Contract.objects.select_for_update().filter(gig=gig, tenant=gig.tenant).first()
        if contract is None or contract.status != Contract.Status.SIGNED:
            raise ContractSigningError(_("Le contrat n'est pas signé."))
        if contract.signed_pdf:
            raise ContractSigningError(_("Le PDF signé est déjà enregistré."))
        contract.signed_pdf = signed_pdf
        contract.save(update_fields=["signed_pdf"])
    return contract


SHARE_LINK_DAYS = 7


def create_share_link(contract, user):
    """A link to the latest version, valid for a week. The previous active links are cancelled."""
    version = contract.latest_version
    if version is None:
        raise ContractSigningError(_("Générez d'abord le contrat avant de l'envoyer."))
    if not version.annexes_snapshot:
        raise ContractSigningError(NO_ANNEXES)
    now = timezone.now()
    with transaction.atomic():
        contract.share_links.filter(revoked_at=None).update(revoked_at=now)
        return ContractShareLink.objects.create(
            tenant=contract.tenant,
            contract=contract,
            version=version,
            token=secrets.token_urlsafe(32),
            created_by=user,
            expires_at=now + datetime.timedelta(days=SHARE_LINK_DAYS),
        )


def active_share_link(contract):
    """The link the user can still send for the latest version, if any."""
    if contract is None or contract.pk is None:
        return None
    link = contract.share_links.select_related("version").first()
    if link and link.is_active and link.version_id == getattr(contract.latest_version, "pk", None):
        return link
    return None


def find_share_link(token):
    return (
        ContractShareLink.objects.select_related("version", "contract", "tenant")
        .filter(token=token)
        .first()
    )
