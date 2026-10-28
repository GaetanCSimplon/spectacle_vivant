"""Account adapter: an e-mail that cannot be sent never ends in an error page.

While the mail service is down, badly set up (wrong login, domain not validated) or slow, django
raises while allauth sends the confirmation or reset e-mail, and the visitor would get a 500 page
after their account was created. Here the failure is turned into a clear message on the next page;
the account stays, and the confirmation is sent again at the next sign-in attempt.
"""

import logging
import smtplib

from allauth.account.adapter import DefaultAccountAdapter
from allauth.core import context
from django.contrib import messages
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)

SENT_MESSAGE = "account/messages/email_confirmation_sent.txt"


class AccountAdapter(DefaultAccountAdapter):
    def add_message(self, request, level, message_template=None, *args, **kwargs):
        """Skip "Confirmation email sent to ..." when the sending just failed (it would say the
        opposite of the error shown beside it)."""
        if message_template == SENT_MESSAGE and getattr(request, "account_mail_failed", False):
            return
        super().add_message(request, level, message_template, *args, **kwargs)

    def send_mail(self, template_prefix, email, context_data):
        try:
            super().send_mail(template_prefix, email, context_data)
        except (smtplib.SMTPException, OSError) as error:
            # Only the kind of failure is logged: never the address (personal data, CLAUDE.md §6.3).
            logger.error("An account e-mail could not be sent (%s).", type(error).__name__)
            request = context.request
            if request is not None:
                request.account_mail_failed = True
                messages.error(
                    request,
                    _(
                        "Nous n'avons pas pu envoyer l'e-mail. Votre demande est bien "
                        "enregistrée : réessayez dans quelques minutes (reconnectez-vous pour "
                        "recevoir de nouveau le lien de confirmation) ou écrivez-nous depuis "
                        "la page Contact."
                    ),
                )
