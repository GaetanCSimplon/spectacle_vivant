from allauth.account.forms import SignupForm
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import SignupInvitation


class InvitedSignupForm(SignupForm):
    """The sign-up form, restricted to invited addresses while `SIGNUP_REQUIRES_INVITATION` is on.

    Checked here and not in the adapter's `clean_email`, which the password-reset and
    add-an-address forms also use. The refusal says nothing about existing accounts.
    """

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if (
            settings.SIGNUP_REQUIRES_INVITATION
            and not SignupInvitation.objects.filter(email=email).exists()
        ):
            raise ValidationError(
                _(
                    "L'inscription se fait sur invitation. Pour en demander une, "
                    "écrivez-nous depuis la page Contact."
                )
            )
        return super().clean_email()
