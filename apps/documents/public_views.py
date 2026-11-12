"""The page a contract's recipient reaches from the link in the e-mail (CTR-08). No account.

The secret token gives access to one PDF (the version that was sent) and to nothing else.
"""

from django.http import FileResponse, Http404
from django.shortcuts import render
from django.views import View

from apps.core.views import protect_secret_page

from . import services


class PublicContractDownloadView(View):
    def get(self, request, token):
        link = services.find_share_link(token)
        if link is None:
            raise Http404  # an unknown token gets the same answer as any unknown page
        if not link.is_active:
            response = render(
                request, "public/contract_link_closed.html", {"tenant": link.tenant}, status=410
            )
            return protect_secret_page(response)
        version = link.version
        response = FileResponse(
            version.pdf_file.open("rb"),
            content_type="application/pdf",
            as_attachment=True,
            filename=f"{link.contract.reference or 'contrat'}-v{version.number}.pdf",
        )
        return protect_secret_page(response)
