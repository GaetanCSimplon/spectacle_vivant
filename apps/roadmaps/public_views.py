"""The page an organiser reaches from the "Régie de tournée" link (F-90). No account needed.

The secret token is the only access right and it gives access to nothing but one form: it shows
the name of the structure, the show, the date and the venue (what the organiser already knows),
never a price or a document. Pages are kept out of caches and search engines, like the shared
roadmap and the organiser's form.
"""

from django.http import Http404
from django.shortcuts import redirect, render
from django.views import View

from apps.core.views import protect_secret_page

from . import tour_requests
from .forms import TourRequestForm
from .models import RoadmapRequest

# "no-referrer" would make the browser send `Origin: null` with the form: CSRF check fails.
SAME_ORIGIN = "same-origin"


class PublicTourFormView(View):
    template_name = "public/tour_form.html"

    def get_request(self, token):
        tour_request = tour_requests.find_request(token)
        if tour_request is None:
            raise Http404  # an unknown token gets the same answer as any unknown page
        return tour_request

    def closed(self, request, tour_request):
        response = render(
            request, "public/tour_form_closed.html", {"tenant": tour_request.tenant}, status=410
        )
        return protect_secret_page(response, referrer=SAME_ORIGIN)

    def page(self, request, tour_request, form):
        context = {
            "form": form,
            "tenant": tour_request.tenant,
            "gig": tour_request.gig,
            "step": request.GET.get("etape"),
        }
        return protect_secret_page(render(request, self.template_name, context), SAME_ORIGIN)

    def get(self, request, token):
        tour_request = self.get_request(token)
        if tour_request.status != RoadmapRequest.Status.ACTIVE:
            return self.closed(request, tour_request)
        return self.page(request, tour_request, TourRequestForm())

    def post(self, request, token):
        tour_request = self.get_request(token)
        if tour_request.status != RoadmapRequest.Status.ACTIVE:
            return self.closed(request, tour_request)
        form = TourRequestForm(request.POST)
        if not form.is_valid():
            return self.page(request, tour_request, form)
        try:
            tour_requests.submit_response(tour_request, form.cleaned_data)
        except tour_requests.RequestClosed:
            return self.closed(request, tour_request)
        return protect_secret_page(redirect("tour-form-thanks"), SAME_ORIGIN)


class PublicTourFormThanksView(View):
    def get(self, request):
        return protect_secret_page(render(request, "public/tour_form_thanks.html"), SAME_ORIGIN)
