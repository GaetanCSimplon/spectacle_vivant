from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from apps.core.views import TenantScopedMixin
from apps.gigs.models import Gig

from . import rules


class RadarView(TenantScopedMixin, TemplateView):
    """« Ce qui coince » : everything Radar sees for the structure, most serious first."""

    template_name = "radar/radar.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        findings = rules.all_findings(self.request.tenant)
        context["findings"] = findings
        context["counts"] = {
            key: sum(1 for f in findings if f.severity == key) for key in rules.SEVERITIES
        }
        return context


class RadarFragmentMixin(TenantScopedMixin):
    """What the Radar button and its modal show: the alerts of the date being looked at (given
    as ?gig=), plus those of the structure; anywhere else, everything Radar sees."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        gig_id = self.request.GET.get("gig", "")
        if gig_id.isdigit():
            gig = get_object_or_404(Gig, pk=gig_id, tenant=self.request.tenant)
            findings = sorted(
                rules.tenant_findings(self.request.tenant) + rules.for_gig(gig),
                key=lambda f: rules.ORDER[f.severity],
            )
            context["gig"] = gig
        else:
            findings = rules.all_findings(self.request.tenant)
        context["findings"] = findings
        context["counts"] = {
            key: sum(1 for f in findings if f.severity == key) for key in rules.SEVERITIES
        }
        return context


class RadarButtonView(RadarFragmentMixin, TemplateView):
    """The round Radar button with its notification (reloaded after every action)."""

    template_name = "radar/_button.html"


class RadarPanelView(RadarFragmentMixin, TemplateView):
    """The content of the Radar modal, read when the button is clicked."""

    template_name = "radar/_panel.html"
