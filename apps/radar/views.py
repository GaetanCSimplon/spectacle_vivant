from django.views.generic import TemplateView

from apps.core.views import TenantScopedMixin

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
