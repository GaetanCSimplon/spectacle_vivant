"""Fails if a TenantOwnedModel subclass has no isolation test.

Importing test_tenant_isolation populates the registry via its
mark_isolation_tested() calls (pytest has already imported every test
module by the time tests run, but we import explicitly here too so this
test is not order-dependent).
"""

from django.apps import apps

from apps.core.models import TenantOwnedModel
from apps.core.tests import (
    isolation_registry,
    test_tenant_isolation,  # noqa: F401
)


def _tenant_owned_models():
    return {
        model
        for model in apps.get_models()
        if issubclass(model, TenantOwnedModel) and not model._meta.abstract
    }


def test_every_tenant_owned_model_has_an_isolation_test():
    untested = _tenant_owned_models() - isolation_registry.tested_models()

    assert not untested, (
        "Ces modèles TenantOwnedModel n'ont pas de test d'isolation : "
        f"{sorted(m.__name__ for m in untested)}"
    )
