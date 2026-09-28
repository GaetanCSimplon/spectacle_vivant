from django.db import transaction

from apps.accounts.models import Membership

from .models import Tenant


def create_tenant_for_user(user, **tenant_fields):
    """Create a Tenant and make `user` its owner, atomically."""
    with transaction.atomic():
        tenant = Tenant.objects.create(**tenant_fields)
        Membership.objects.create(user=user, tenant=tenant, role=Membership.Role.OWNER)
    return tenant
