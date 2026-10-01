from decimal import ROUND_HALF_UP, Decimal

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.core.services import render_pdf
from apps.gigs.models import Gig
from apps.tenants.models import Tenant

from .models import Contract, ContractSequence, ContractVersion

TWO_PLACES = Decimal("0.01")

# How the tenant is named in the contract body, with the article each
# grammatical use needs (subject / "à" / "de").
PARTY_FORMS = {
    Tenant.ContractPartyLabel.PRODUCER: {
        "subject": "LE PRODUCTEUR",
        "to": "AU PRODUCTEUR",
        "of": "DU PRODUCTEUR",
    },
    Tenant.ContractPartyLabel.ARTIST: {
        "subject": "L'ARTISTE",
        "to": "À L'ARTISTE",
        "of": "DE L'ARTISTE",
    },
}


class ContractNotAvailable(Exception):
    """A contract cannot be produced for a cancelled gig."""


def _compute_vat(gig, tenant):
    """Return (vat_amount, total_with_vat), or (None, None) if the rate is not known yet."""
    if tenant.vat_regime != Tenant.VatRegime.TAXABLE or tenant.vat_rate is None:
        return None, None

    vat_amount = (gig.price * Decimal(tenant.vat_rate) / Decimal("100")).quantize(
        TWO_PLACES, rounding=ROUND_HALF_UP
    )
    return vat_amount, gig.price + vat_amount


def build_contract_context(gig, contract=None):
    vat_amount, total_with_vat = _compute_vat(gig, gig.tenant)
    return {
        "contract": contract,
        "party": PARTY_FORMS[gig.tenant.contract_party_label],
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


def render_contract_pdf(gig, contract=None):
    """Render the contract PDF bytes without storing anything (used for the preview)."""
    return render_pdf("documents/contract_pdf.html", build_contract_context(gig, contract))


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
        pdf_bytes = render_contract_pdf(gig, contract)
        version = ContractVersion(
            tenant=gig.tenant, contract=contract, number=number, created_by=user
        )
        version.pdf_file.save(f"{contract.reference}-v{number}.pdf", ContentFile(pdf_bytes))
    return contract
