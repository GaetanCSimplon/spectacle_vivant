"""Fragments for the two look-ups of apps/core/lookups.py (HTMX). Signed-in users only."""

import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from . import lookups


class CompanySearchView(LoginRequiredMixin, View):
    """The companies matching what is typed in the search box, as buttons to pick from."""

    def get(self, request):
        query = request.GET.get("q", "")
        if lookups.allowed(request.user.pk, "companies"):
            search = lookups.search_companies(query)
        else:
            search = lookups.CompanySearch(available=False)
        return render(request, "core/_company_results.html", {"search": search, "query": query})


class CommuneSearchView(LoginRequiredMixin, View):
    """The communes of a postal code, as the options of the city field (a `<datalist>`)."""

    def get(self, request):
        if lookups.allowed(request.user.pk, "communes"):
            search = lookups.search_communes(request.GET.get("postal_code", ""))
        else:
            search = lookups.CommuneSearch(available=False)
        response = render(request, "core/_commune_options.html", {"search": search})
        if len(search.names) == 1:
            # The city field fills itself when it is empty (see the widget in core/forms.py).
            response["HX-Trigger"] = json.dumps({"commune-found": {"name": search.names[0]}})
        return response
