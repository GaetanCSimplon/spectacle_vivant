from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class SitePagesSitemap(Sitemap):
    """The pages of the presentation site (the app itself is never listed)."""

    changefreq = "monthly"
    protocol = "https"

    def items(self):
        return ["home", "site-features", "site-contact"]

    def location(self, item):
        return reverse(item)
