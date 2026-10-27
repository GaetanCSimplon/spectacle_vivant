"""Fill in the map point of the venues and lodgings saved before the map preview existed."""

import time

from django.core.management.base import BaseCommand

from apps.addressbook.models import Venue
from apps.roadmaps.models import Lodging

# The service of OpenStreetMap asks for at most one request per second.
PAUSE_SECONDS = 1.1


class Command(BaseCommand):
    help = "Look up the map point of every venue and lodging whose address has none yet."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Look every address up again, even those already looked up (after a fix).",
        )

    def handle(self, *args, **options):
        done = skipped = 0
        for model in (Venue, Lodging):
            for place in model.objects.iterator():
                query = place.one_line_address
                if not query or (query == place.geocoded_address and not options["all"]):
                    continue
                if options["all"]:
                    place.geocoded_address = ""  # forces the lookup in save()
                place.save()  # looks the address up (see GeoPointMixin)
                if place.geocoded_address == query:
                    done += 1
                else:
                    skipped += 1  # the service did not answer: a later run tries again
                time.sleep(PAUSE_SECONDS)
        self.stdout.write(f"{done} place(s) located, {skipped} to retry.")
