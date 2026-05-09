"""
Unit tests for TenantRegistrationView (task 3.2).
Static analysis only — Django and DRF are not installed in the dev shell.
"""
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIRequestFactory

from apps.tenants.exceptions import SubdomainAlreadyExistsError
from apps.tenants.views import TenantRegistrationView

factory = APIRequestFactory()
view = TenantRegistrationView.as_view()


def _valid_payload():
    return {
        "nombre_empresa": "ACME Corp",
        "subdominio": "acme",
        "email_admin": "admin@acme.com",
        "password": "Admin123!",
    }


def _make_mock_tenant():
    t = MagicMock()
    t.id = 1
    t.schema_name = "acme"
    t.subscription.fecha_fin = date(2026, 5, 21)
    return t


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

@patch("apps.tenants.views.TenantRegistrationService")
def test_register_returns_201_on_success(MockService):
    MockService.register.return_value = _make_mock_tenant()
    request = factory.post("/api/public/tenants/register/", _valid_payload(), format="json")
    response = view(request)
    assert response.status_code == 201


@patch("apps.tenants.views.TenantRegistrationService")
def test_register_response_body_has_required_fields(MockService):
    MockService.register.return_value = _make_mock_tenant()
    request = factory.post("/api/public/tenants/register/", _valid_payload(), format="json")
    response = view(request)
    for field in ("id", "subdominio", "email_admin", "trial_expires_at", "message"):
        assert field in response.data, f"Missing field: {field}"


@patch("apps.tenants.views.TenantRegistrationService")
def test_register_response_subdominio_matches_input(MockService):
    MockService.register.return_value = _make_mock_tenant()
    request = factory.post("/api/public/tenants/register/", _valid_payload(), format="json")
    response = view(request)
    assert response.data["subdominio"] == "acme"


@patch("apps.tenants.views.TenantRegistrationService")
def test_register_delegates_to_service_with_correct_args(MockService):
    MockService.register.return_value = _make_mock_tenant()
    request = factory.post("/api/public/tenants/register/", _valid_payload(), format="json")
    view(request)
    MockService.register.assert_called_once_with(
        nombre_empresa="ACME Corp",
        subdominio="acme",
        email_admin="admin@acme.com",
        password="Admin123!",
    )


# ---------------------------------------------------------------------------
# Duplicate subdomain → 409
# ---------------------------------------------------------------------------

@patch("apps.tenants.views.TenantRegistrationService")
def test_register_returns_409_on_subdomain_duplicate(MockService):
    MockService.register.side_effect = SubdomainAlreadyExistsError(
        "El subdominio 'acme' ya está registrado."
    )
    request = factory.post("/api/public/tenants/register/", _valid_payload(), format="json")
    response = view(request)
    assert response.status_code == 409


@patch("apps.tenants.views.TenantRegistrationService")
def test_register_409_body_has_code_field(MockService):
    MockService.register.side_effect = SubdomainAlreadyExistsError("duplicate")
    request = factory.post("/api/public/tenants/register/", _valid_payload(), format="json")
    response = view(request)
    assert response.data.get("code") == "subdomain_already_exists"


# ---------------------------------------------------------------------------
# Validation errors → 400
# ---------------------------------------------------------------------------

def test_register_returns_400_on_missing_fields():
    request = factory.post("/api/public/tenants/register/", {}, format="json")
    response = view(request)
    assert response.status_code == 400


def test_register_returns_400_on_invalid_subdomain_format():
    payload = {**_valid_payload(), "subdominio": "INVALID_SUBDOMAIN!"}
    request = factory.post("/api/public/tenants/register/", payload, format="json")
    response = view(request)
    assert response.status_code == 400


def test_register_returns_400_on_invalid_email():
    payload = {**_valid_payload(), "email_admin": "not-an-email"}
    request = factory.post("/api/public/tenants/register/", payload, format="json")
    response = view(request)
    assert response.status_code == 400
