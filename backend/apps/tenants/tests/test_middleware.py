"""
Unit tests for AccessPolicyMiddleware (task 4).
Uses Django RequestFactory — no database required.
"""
import json
from unittest.mock import MagicMock

import pytest
from django.test import RequestFactory

from apps.tenants.middleware import AccessPolicyMiddleware

factory = RequestFactory()


def _ok_response():
    return MagicMock(status_code=200)


def _middleware(get_response=None):
    if get_response is None:
        get_response = MagicMock(return_value=_ok_response())
    return AccessPolicyMiddleware(get_response), get_response


def _tenant(is_active=True):
    t = MagicMock()
    t.subscription.is_active.return_value = is_active
    return t


# ---------------------------------------------------------------------------
# Public schema (no tenant attribute) → always pass
# ---------------------------------------------------------------------------

def test_public_schema_passes():
    mw, get_response = _middleware()
    request = factory.get("/some/path/")
    mw(request)
    get_response.assert_called_once_with(request)


# ---------------------------------------------------------------------------
# Tenant with active subscription → pass
# ---------------------------------------------------------------------------

def test_active_trial_tenant_passes():
    mw, get_response = _middleware()
    request = factory.get("/tenant/resource/")
    request.tenant = _tenant(is_active=True)
    response = mw(request)
    get_response.assert_called_once_with(request)


def test_active_enterprise_tenant_passes():
    mw, get_response = _middleware()
    request = factory.get("/tenant/resource/")
    request.tenant = _tenant(is_active=True)
    response = mw(request)
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Tenant with expired subscription → 402
# ---------------------------------------------------------------------------

def test_expired_trial_returns_402():
    mw, _ = _middleware()
    request = factory.get("/tenant/resource/")
    request.tenant = _tenant(is_active=False)
    response = mw(request)
    assert response.status_code == 402


def test_expired_trial_body_has_code():
    mw, _ = _middleware()
    request = factory.get("/tenant/resource/")
    request.tenant = _tenant(is_active=False)
    response = mw(request)
    body = json.loads(response.content)
    assert body.get("code") == "trial_expired"


def test_expired_trial_get_response_not_called():
    get_response = MagicMock(return_value=_ok_response())
    mw = AccessPolicyMiddleware(get_response)
    request = factory.get("/tenant/resource/")
    request.tenant = _tenant(is_active=False)
    mw(request)
    get_response.assert_not_called()


# ---------------------------------------------------------------------------
# Whitelist paths — expired tenant still passes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", [
    "/admin/",
    "/admin/tenants/tenant/",
    "/api/public/tenants/register/",
    "/static/app.css",
    "/media/uploads/file.pdf",
])
def test_whitelist_path_passes_even_with_expired_tenant(path):
    mw, get_response = _middleware()
    request = factory.get(path)
    request.tenant = _tenant(is_active=False)
    mw(request)
    get_response.assert_called_once_with(request)
