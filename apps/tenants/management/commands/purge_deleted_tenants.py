from django.core.management.base import BaseCommand

from apps.tenants.services import purge_due_tenants


class Command(BaseCommand):
    help = "Delete the tenants whose deletion was requested more than 30 days ago."

    def handle(self, *args, **options):
        count = purge_due_tenants()
        # Only a count: never print names or e-mails (they would end up in the logs).
        self.stdout.write(f"{count} tenant(s) purged.")
