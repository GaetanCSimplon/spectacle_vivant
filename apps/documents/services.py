from decimal import ROUND_HALF_UP, Decimal

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.services import render_pdf
from apps.gigs import services as gig_services
from apps.gigs.models import Gig
from apps.tenants.models import Tenant

from .invoicing import legal_mentions, money
from .models import Contract, ContractSequence, ContractTemplate, ContractVersion

TWO_PLACES = Decimal("0.01")

# The tenant is always "LE PRODUCTEUR" in the contract body, with the article each
# grammatical use needs (subject / "à" / "de").
PARTY_FORMS = {
    "subject": "LE PRODUCTEUR",
    "to": "AU PRODUCTEUR",
    "of": "DU PRODUCTEUR",
}


# The wordings that have a template file. A model is offered to users only once it is listed here.
CONTRACT_TEMPLATES = {
    ContractTemplate.MODEL_1: "documents/contracts/model_1.html",
    ContractTemplate.MODEL_2: "documents/contracts/model_2.html",
}
DEFAULT_CONTRACT_TEMPLATE = ContractTemplate.MODEL_1


def available_contract_templates():
    """The (value, label) choices a user can pick from."""
    return [choice for choice in ContractTemplate.choices if choice[0] in CONTRACT_TEMPLATES]


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


def build_contract_context(gig, contract=None):
    vat_amount, total_with_vat = _compute_vat(gig, gig.tenant)
    return {
        "payment": payment_schedule(gig),
        "vat_mentions": legal_mentions({"vat_regime": gig.tenant.vat_regime}, False, False),
        "contract": contract,
        "party": PARTY_FORMS,
        "vat_exempt": gig.tenant.vat_regime != Tenant.VatRegime.TAXABLE,
        "vat_amount": vat_amount,
        "total_with_vat": total_with_vat,
        "gig": gig,
        "tenant": gig.tenant,
        "promoter": gig.promoter,
        "venue": gig.venue,
        "show": gig.show,
        "today": timezone.now().date(),
    }


def render_contract_pdf(gig, contract=None, template=None):
    """Render the contract PDF bytes without storing anything (used for the preview).

    `template` is the wording to use; by default the one the contract already has.
    """
    template = template or (contract.template if contract else DEFAULT_CONTRACT_TEMPLATE)
    return render_pdf(CONTRACT_TEMPLATES[template], build_contract_context(gig, contract))


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


def generate_contract_pdf(gig, user=None, template=None):
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
        template = template or (contract.template if contract else DEFAULT_CONTRACT_TEMPLATE)
        if template not in CONTRACT_TEMPLATES:
            raise ValueError(f"Unknown contract template: {template}")
        if contract is None:
            contract = Contract.objects.create(gig=gig, tenant=gig.tenant, template=template)
        elif contract.template != template:
            contract.template = template
            contract.save(update_fields=["template"])
        if not contract.reference:
            contract.reference = next_contract_reference(gig.tenant)
            contract.save(update_fields=["reference"])

        latest = contract.latest_version
        number = latest.number + 1 if latest else 1
        pdf_bytes = render_contract_pdf(gig, contract, template)
        version = ContractVersion(
            tenant=gig.tenant, contract=contract, number=number, created_by=user, template=template
        )
        version.pdf_file.save(f"{contract.reference}-v{number}.pdf", ContentFile(pdf_bytes))
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
