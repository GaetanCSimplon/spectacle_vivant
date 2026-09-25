from django.shortcuts import get_object_or_404

from apps.addressbook.models import Promoter, Venue
from apps.catalog.models import Show

from .models import Gig


def get_wizard_related_objects(tenant, data):
    """Fetch the Show/Promoter/Venue chosen in the wizard, scoped to the tenant."""
    show = get_object_or_404(Show, pk=data["show_id"], tenant=tenant)
    promoter = get_object_or_404(Promoter, pk=data["promoter_id"], tenant=tenant)
    venue = get_object_or_404(Venue, pk=data["venue_id"], tenant=tenant)
    return show, promoter, venue


def create_gig_from_wizard_data(tenant, data):
    show, promoter, venue = get_wizard_related_objects(tenant, data)
    return Gig.objects.create(
        tenant=tenant,
        show=show,
        promoter=promoter,
        venue=venue,
        date=data["date"],
        price=data["price"],
        conditions=data.get("conditions", ""),
    )
