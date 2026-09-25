from .models import Membership


def is_tenant_owner(user, tenant):
    return Membership.objects.filter(user=user, tenant=tenant, role=Membership.Role.OWNER).exists()
