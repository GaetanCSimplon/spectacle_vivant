from decimal import ROUND_HALF_UP, Decimal

from django.core.files.base import ContentFile
from django.utils import timezone

from apps.core.services import render_pdf
from apps.gigs.models import Gig
from apps.tenants.models import Tenant

from .models import Contract

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


def generate_contract_pdf(gig):
    """Render the contract PDF for a gig and store it on its Contract.

    A signed contract keeps its figée PDF: it is never regenerated (RG-08).
    A cancelled gig gets no new contract: an existing one stays as it is.
    """
    contract = Contract.objects.filter(gig=gig, tenant=gig.tenant).first()
    if contract and contract.status == Contract.Status.SIGNED:
        return contract
    if gig.status == Gig.Status.CANCELLED:
        if contract and contract.pdf_file:
            return contract
        raise ContractNotAvailable
    if contract is None:
        contract = Contract.objects.create(gig=gig, tenant=gig.tenant)

    pdf_bytes = render_contract_pdf(gig, contract)
    contract.pdf_file.save(f"contrat-{gig.pk}.pdf", ContentFile(pdf_bytes), save=False)
    contract.generated_at = timezone.now()
    contract.save()
    return contract
