from django.conf import settings


def signup_policy(request):
    return {"signup_requires_invitation": settings.SIGNUP_REQUIRES_INVITATION}
