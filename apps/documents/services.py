from django.core.files.base import ContentFile
from django.utils import timezone

from apps.core.services import render_pdf
from apps.tenants.models import Tenant

from .models import Contract

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


def build_contract_context(gig, contract=None):
    return {
        "contract": contract,
        "party": PARTY_FORMS[gig.tenant.contract_party_label],
        "vat_exempt": gig.tenant.vat_regime != Tenant.VatRegime.TAXABLE,
        "gig": gig,
        "tenant": gig.tenant,
        "promoter": gig.promoter,
        "venue": gig.venue,
        "show": gig.show,
        "today": timezone.now().date(),
    }


def generate_contract_pdf(gig):
    """Render the contract PDF for a gig and store it on its Contract.

    A signed contract keeps its figée PDF: it is never regenerated (RG-08).
    """
    contract, _created = Contract.objects.get_or_create(gig=gig, tenant=gig.tenant)
    if contract.status == Contract.Status.SIGNED:
        return contract

    pdf_bytes = render_pdf("documents/contract_pdf.html", build_contract_context(gig, contract))
    contract.pdf_file.save(f"contrat-{gig.pk}.pdf", ContentFile(pdf_bytes), save=False)
    contract.generated_at = timezone.now()
    contract.save()
    return contract
