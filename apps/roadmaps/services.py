import secrets

from .models import Roadmap, RoadmapSlot


def get_or_create_roadmap(gig):
    """Return the gig's roadmap; a new one is pre-filled from the gig's times."""
    roadmap, created = Roadmap.objects.get_or_create(gig=gig, defaults={"tenant": gig.tenant})
    if created:
        prefill = [
            (RoadmapSlot.Kind.ARRIVAL, gig.get_in_time),
            (RoadmapSlot.Kind.SOUNDCHECK, gig.soundcheck_time),
            (RoadmapSlot.Kind.PERFORMANCE, gig.performance_time),
        ]
        RoadmapSlot.objects.bulk_create(
            RoadmapSlot(tenant=gig.tenant, roadmap=roadmap, kind=kind, time=time)
            for kind, time in prefill
            if time is not None
        )
    return roadmap


def publish(roadmap):
    """Turn sharing on with a brand-new secret token (an old link never comes back)."""
    roadmap.token = secrets.token_urlsafe(32)
    roadmap.is_published = True
    roadmap.save(update_fields=["token", "is_published"])


def revoke(roadmap):
    """Turn sharing off for good: the token is erased."""
    roadmap.token = ""
    roadmap.is_published = False
    roadmap.save(update_fields=["token", "is_published"])


def public_path(token):
    """Path of the public page of a shared roadmap."""
    return f"/feuille-de-route/{token}/"
