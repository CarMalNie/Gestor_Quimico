"""Shared fixtures for app_quimico tests."""

import pytest

from app_quimico.utils import invalidar_cache_pesos


@pytest.fixture(autouse=True)
def _reset_weight_cache():
    """Keeps the module-global weight cache from leaking stale rows across tests
    (the cache is process-global while the DB rolls back between tests)."""
    invalidar_cache_pesos()
    yield
    invalidar_cache_pesos()
