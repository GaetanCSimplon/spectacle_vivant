"""Registry of TenantOwnedModel subclasses covered by an isolation test.

Each isolation test module must call `mark_isolation_tested(Model)` at
import time. `test_tenant_coverage.py` checks that every concrete
TenantOwnedModel subclass in the project appears here.
"""

_TESTED_MODELS = set()


def mark_isolation_tested(model):
    _TESTED_MODELS.add(model)


def tested_models():
    return set(_TESTED_MODELS)
