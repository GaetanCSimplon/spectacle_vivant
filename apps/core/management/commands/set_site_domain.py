from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Point the Site at the real domain: allauth builds the links of its e-mails from it."""

    help = "Set the domain of the current Site from DJANGO_SITE_DOMAIN."

    def handle(self, *args, **options):
        domain = getattr(settings, "SITE_DOMAIN", "")
        if not domain:
            raise CommandError("DJANGO_SITE_DOMAIN is not set.")
        Site.objects.update_or_create(
            pk=settings.SITE_ID, defaults={"domain": domain, "name": "Bòrd Pro"}
        )
        self.stdout.write(f"Site domain set to {domain}")
