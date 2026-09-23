from django.shortcuts import get_object_or_404

from apps.addressbook.models import Promoter, Venue
from apps.catalog.models import Show

from .models import Gig


def get_wizard_related_objects(organization, data):
    """Fetch the Show/Promoter/Venue chosen in the wizard, scoped to the organization."""
    show = get_object_or_404(Show, pk=data["show_id"], organization=organization)
    promoter = get_object_or_404(Promoter, pk=data["promoter_id"], organization=organization)
    venue = get_object_or_404(Venue, pk=data["venue_id"], organization=organization)
    return show, promoter, venue


def create_gig_from_wizard_data(organization, data):
    show, promoter, venue = get_wizard_related_objects(organization, data)
    return Gig.objects.create(
        organization=organization,
        show=show,
        promoter=promoter,
        venue=venue,
        date=data["date"],
        price=data["price"],
        conditions=data.get("conditions", ""),
    )
