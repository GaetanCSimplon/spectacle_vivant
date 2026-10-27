from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from .addresses import DEPARTMENT_CHOICES, format_address
from .geocoding import embed_url, geocode


class TenantOwnedModel(models.Model):
    """Abstract base for models scoped to a Tenant."""

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
    )

    class Meta:
        abstract = True


class AddressMixin(models.Model):
    """Postal code, city and department next to a model's own street field.

    The street keeps the name the model already has (`address`, `billing_address`);
    `street_field` says which one it is. An old address typed as one block of text stays in
    the street field: the other fields are simply empty until the user completes them.
    """

    street_field = "address"

    postal_code = models.CharField(
        _("code postal"),
        max_length=5,
        blank=True,
        validators=[
            RegexValidator(r"^\d{5}$", _("Un code postal compte 5 chiffres, par exemple 34000."))
        ],
    )
    city = models.CharField(_("ville"), max_length=100, blank=True)
    department = models.CharField(
        _("département"), max_length=3, blank=True, choices=DEPARTMENT_CHOICES
    )

    class Meta:
        abstract = True

    @property
    def full_address(self):
        """What is printed on documents and sheets: the street, then postal code and city."""
        return format_address(getattr(self, self.street_field), self.postal_code, self.city)

    @property
    def one_line_address(self):
        """The same address on one line, for a map search or a "copy the address" button."""
        # A street typed in a text box carries "\r\n": one clean line, no stray carriage return.
        lines = (line.strip() for line in self.full_address.splitlines())
        return ", ".join(line for line in lines if line)


class GeoPointMixin(AddressMixin):
    """An address that also remembers its place on the map (for the roadmap's map preview).

    The point is looked up when the address changes, at save time, and only then. If the lookup
    fails, the point is dropped (it would belong to the old address) and the next save tries
    again; an address the service does not know is remembered, so it is not asked again.
    """

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, editable=False)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, editable=False)
    # The one-line address the point was looked up for: tells when it is out of date.
    geocoded_address = models.CharField(max_length=500, blank=True, editable=False)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if kwargs.get("update_fields") is None:
            self.refresh_point()
        super().save(*args, **kwargs)

    @property
    def has_point(self):
        return self.latitude is not None and self.longitude is not None

    @property
    def map_embed_url(self):
        return embed_url(self.latitude, self.longitude) if self.has_point else ""

    def refresh_point(self):
        """Look the address up again if it changed since the last lookup."""
        query = self.one_line_address
        if query == self.geocoded_address:
            return
        self.latitude = self.longitude = None
        if not query:
            self.geocoded_address = ""
            return
        result = geocode(query)
        if result.status in ("found", "not_found"):
            self.geocoded_address = query
            self.latitude, self.longitude = result.latitude, result.longitude


class Note(TenantOwnedModel):
    """Disposable model used only to validate the tenant isolation mechanism."""

    text = models.TextField(blank=True)

    def __str__(self):
        return self.text[:50]
