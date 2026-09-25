from django.http import FileResponse
from django.shortcuts import get_object_or_404, render
from django.views import View

from apps.core.views import TenantScopedMixin
from apps.gigs.models import Gig

from . import services


class ContractReadyView(TenantScopedMixin, View):
    def get(self, request, gig_id):
        gig = get_object_or_404(Gig, pk=gig_id, tenant=request.tenant)
        return render(request, "documents/contract_ready.html", {"gig": gig})


class ContractPreviewView(TenantScopedMixin, View):
    def get(self, request, gig_id):
        gig = get_object_or_404(Gig, pk=gig_id, tenant=request.tenant)
        contract = services.generate_contract_pdf(gig)
        return FileResponse(contract.pdf_file.open("rb"), content_type="application/pdf")


class ContractDownloadView(TenantScopedMixin, View):
    def get(self, request, gig_id):
        gig = get_object_or_404(Gig, pk=gig_id, tenant=request.tenant)
        contract = services.generate_contract_pdf(gig)
        return FileResponse(
            contract.pdf_file.open("rb"),
            content_type="application/pdf",
            as_attachment=True,
            filename=f"contrat-{gig.pk}.pdf",
        )
