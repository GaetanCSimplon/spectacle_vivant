"""Build issued invoices for tests (a payment needs one)."""

from apps.documents import invoicing
from apps.documents.models import Invoice
from apps.gigs.factories import GigFactory
from apps.tenants.models import Tenant

TENANT_FIELDS = {
    "name": "Compagnie du Soleil",
    "address": "1 rue des Arts, 69001 Lyon",
    "siret": "12345678900012",
    "vat_regime": Tenant.VatRegime.FRANCHISE,
    "iban": "FR1420041010050500013M02606",
}


def make_gig(tenant=None, price="1000.00", **tenant_fields):
    fields = {**TENANT_FIELDS, **tenant_fields}
    extra = {"tenant": tenant} if tenant else {f"tenant__{k}": v for k, v in fields.items()}
    gig = GigFactory(
        price=price,
        promoter__name="Mairie de Nîmes",
        promoter__billing_address="3 place de la Mairie, 30000 Nîmes",
        **extra,
    )
    gig.refresh_from_db()
    return gig


def issued_invoice(gig=None, kind=Invoice.Kind.FULL):
    return invoicing.issue_invoice(invoicing.create_invoice(gig or make_gig(), kind))
