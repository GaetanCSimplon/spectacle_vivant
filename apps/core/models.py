from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from .addresses import DEPARTMENT_CHOICES, format_address


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
        return self.full_address.replace("\n", ", ")


class Note(TenantOwnedModel):
    """Disposable model used only to validate the tenant isolation mechanism."""

    text = models.TextField(blank=True)

    def __str__(self):
        return self.text[:50]
