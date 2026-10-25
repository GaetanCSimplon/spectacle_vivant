from allauth.account.signals import user_signed_up
from django.dispatch import receiver
from django.utils import timezone

from .models import SignupInvitation


@receiver(user_signed_up)
def mark_the_invitation_as_used(request, user, **kwargs):
    SignupInvitation.objects.filter(email=user.email.lower(), used_at__isnull=True).update(
        used_at=timezone.now()
    )
