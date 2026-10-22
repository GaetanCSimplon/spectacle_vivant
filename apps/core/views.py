from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.templatetags.static import static
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.finance.dashboard import build_dashboard

from .services import render_pdf


class TenantScopedMixin(LoginRequiredMixin):
    """Restrict a generic view to objects of the current tenant.

    Requires `request.tenant` (set by TenantMiddleware). Views
    using this mixin must never let the tenant be chosen by the
    client: it is always taken from the request.
    """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.tenant is None:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().filter(tenant=self.request.tenant)

    def form_valid(self, form):
        # DeleteView's form has no `instance` (nothing to set the tenant on).
        if hasattr(form, "instance"):
            form.instance.tenant = self.request.tenant
        return super().form_valid(form)


def csrf_failure(request, reason=""):
    """The page shown when the security check of a form fails.

    Not only "the form expired": a closed session, blocked cookies or a wrong origin end
    here too. It is rendered with the request, so that a visitor without an account (an
    organiser answering a link) is not sent to a login page.
    """
    return render(request, "403_csrf.html", {"reason": reason}, status=403)


def protect_secret_page(response, referrer="no-referrer"):
    """The token is in the URL: keep these pages out of caches, search engines and Referer.

    A page that contains a form must pass `referrer="same-origin"`: with "no-referrer"
    browsers send `Origin: null` when the form is submitted, and Django's CSRF check then
    answers 403. "same-origin" still sends no Referer to other sites.
    """
    response["Cache-Control"] = "no-store"
    response["X-Robots-Tag"] = "noindex, nofollow"
    response["Referrer-Policy"] = referrer
    return response


def wants_fragment(request):
    """True for a live HTMX request that must get only a page fragment.

    A boosted link is a full page navigation, and so is the browser Back
    button when htmx restores history: both need the whole page.
    """
    htmx = request.htmx
    return bool(htmx) and not htmx.boosted and not htmx.history_restore_request


class SearchListMixin:
    """Filter a ListView with `?q=` (case-insensitive, on `search_fields`).

    A live-search request (HTMX) gets only the results fragment
    (`results_template_name`); a normal request gets the whole page.
    Put it after TenantScopedMixin: the search only narrows an already
    tenant-scoped queryset.
    """

    search_fields = ()
    results_template_name = None

    def get_search_query(self):
        return self.request.GET.get("q", "").strip()

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.get_search_query()
        if query:
            condition = Q()
            for field in self.search_fields:
                condition |= Q(**{f"{field}__icontains": query})
            queryset = queryset.filter(condition)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.get_search_query()
        return context

    def get_template_names(self):
        if wants_fragment(self.request) and self.results_template_name:
            return [self.results_template_name]
        return super().get_template_names()


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "core/home.html"

    results_template_name = "core/_upcoming_card.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tenant"] = self.request.tenant
        if self.request.tenant is not None:
            period = self.request.GET.get("periode", "")
            context.update(build_dashboard(self.request.tenant, timezone.localdate(), period))
        return context

    def get_template_names(self):
        # The Week / Month / Year switch swaps only the "Prochaines dates" card.
        if wants_fragment(self.request) and self.request.tenant is not None:
            return [self.results_template_name]
        return super().get_template_names()


def home(request):
    """`/`: the dashboard for a logged-in user, the presentation page for a visitor."""
    if request.user.is_authenticated:
        return HomeView.as_view()(request)
    return LandingView.as_view()(request)


class SitePageView(TemplateView):
    """A page of the public presentation site: no login, no tenant, nothing but static text."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contact_email"] = settings.CONTACT_EMAIL
        context["indexable"] = settings.SITE_INDEXABLE
        return context


class LandingView(SitePageView):
    template_name = "site/home.html"


class FeaturesView(SitePageView):
    template_name = "site/features.html"


class ContactView(SitePageView):
    template_name = "site/contact.html"


def robots_txt(request):
    """Keep crawlers out of the app, and out of everything while the site is not indexable."""
    if settings.SITE_INDEXABLE:
        sitemap = request.build_absolute_uri("/sitemap.xml")
        lines = ["User-agent: *", "Allow: /$", "Allow: /fonctionnalites/", "Allow: /contact/"]
        lines += ["Disallow: /", f"Sitemap: {sitemap}"]
    else:
        lines = ["User-agent: *", "Disallow: /"]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


class HelloPdfView(LoginRequiredMixin, View):
    """Disposable view: validates that WeasyPrint works end to end.

    To be removed once a real PDF (e.g. generate_contract_pdf) exists.
    """

    def get(self, request, *args, **kwargs):
        pdf = render_pdf("core/hello_pdf.html")
        return HttpResponse(pdf, content_type="application/pdf")


def favicon(request):
    """Browsers and crawlers ask for /favicon.ico by themselves: send them to the brand icon."""
    return HttpResponseRedirect(static("brand/favicon.ico"))


def apple_touch_icon(request):
    """iOS asks for /apple-touch-icon.png when a page does not declare one."""
    return HttpResponseRedirect(static("brand/apple-touch-icon.png"))
