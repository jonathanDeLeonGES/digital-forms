"""
RED phase: tests for TenantRegistrationService.
Before services.py exists, all tests fail with ImportError.
After implementation, all pass via static analysis (Django not installed in shell).
"""
from datetime import date, timedelta
from unittest.mock import MagicMock, call, patch

import pytest

from apps.tenants.exceptions import SubdomainAlreadyExistsError
from apps.tenants.services import TenantRegistrationService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_tenant():
    t = MagicMock()
    t.schema_name = "acme"
    return t


def _make_mock_plan():
    p = MagicMock()
    p.nombre = "trial"
    return p


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

@patch("apps.tenants.services.Subscription")
@patch("apps.tenants.services.Plan")
@patch("apps.tenants.services.Domain")
@patch("apps.tenants.services.Tenant")
def test_register_saves_tenant_with_correct_fields(MockTenant, MockDomain, MockPlan, MockSub):
    mock_tenant = _make_mock_tenant()
    MockTenant.return_value = mock_tenant
    MockPlan.TRIAL = "trial"
    MockPlan.objects.get.return_value = _make_mock_plan()

    TenantRegistrationService.register("ACME Corp", "acme", "admin@acme.com")

    MockTenant.assert_called_once_with(
        schema_name="acme",
        nombre_empresa="ACME Corp",
        email_admin="admin@acme.com",
    )
    mock_tenant.save.assert_called_once()


@patch("apps.tenants.services.Subscription")
@patch("apps.tenants.services.Plan")
@patch("apps.tenants.services.Domain")
@patch("apps.tenants.services.Tenant")
def test_register_creates_domain_with_correct_url(MockTenant, MockDomain, MockPlan, MockSub):
    mock_tenant = _make_mock_tenant()
    MockTenant.return_value = mock_tenant
    MockPlan.TRIAL = "trial"
    MockPlan.objects.get.return_value = _make_mock_plan()

    TenantRegistrationService.register("ACME Corp", "acme", "admin@acme.com")

    MockDomain.assert_called_once_with(
        domain="acme.sgca.com",
        tenant=mock_tenant,
        is_primary=True,
    )
    MockDomain.return_value.save.assert_called_once()


@patch("apps.tenants.services.Subscription")
@patch("apps.tenants.services.Plan")
@patch("apps.tenants.services.Domain")
@patch("apps.tenants.services.Tenant")
def test_register_creates_trial_subscription_14_days(MockTenant, MockDomain, MockPlan, MockSub):
    mock_tenant = _make_mock_tenant()
    MockTenant.return_value = mock_tenant
    MockPlan.TRIAL = "trial"
    mock_plan = _make_mock_plan()
    MockPlan.objects.get.return_value = mock_plan

    TenantRegistrationService.register("ACME Corp", "acme", "admin@acme.com")

    MockSub.objects.create.assert_called_once_with(
        tenant=mock_tenant,
        plan=mock_plan,
        fecha_fin=date.today() + timedelta(days=14),
    )


@patch("apps.tenants.services.Subscription")
@patch("apps.tenants.services.Plan")
@patch("apps.tenants.services.Domain")
@patch("apps.tenants.services.Tenant")
def test_register_returns_tenant(MockTenant, MockDomain, MockPlan, MockSub):
    mock_tenant = _make_mock_tenant()
    MockTenant.return_value = mock_tenant
    MockPlan.TRIAL = "trial"
    MockPlan.objects.get.return_value = _make_mock_plan()

    result = TenantRegistrationService.register("ACME Corp", "acme", "admin@acme.com")

    assert result is mock_tenant


# ---------------------------------------------------------------------------
# Subdomain duplicate — IntegrityError on Domain.save()
# ---------------------------------------------------------------------------

@patch("apps.tenants.services.Subscription")
@patch("apps.tenants.services.Plan")
@patch("apps.tenants.services.Domain")
@patch("apps.tenants.services.Tenant")
def test_register_raises_subdomain_error_on_integrity_error(
    MockTenant, MockDomain, MockPlan, MockSub
):
    from django.db import IntegrityError as DjangoIntegrityError

    mock_tenant = _make_mock_tenant()
    MockTenant.return_value = mock_tenant
    MockDomain.return_value.save.side_effect = DjangoIntegrityError("unique constraint")

    with pytest.raises(SubdomainAlreadyExistsError):
        TenantRegistrationService.register("ACME Corp", "acme", "admin@acme.com")


@patch("apps.tenants.services.Subscription")
@patch("apps.tenants.services.Plan")
@patch("apps.tenants.services.Domain")
@patch("apps.tenants.services.Tenant")
def test_register_deletes_tenant_on_subdomain_duplicate(
    MockTenant, MockDomain, MockPlan, MockSub
):
    from django.db import IntegrityError as DjangoIntegrityError

    mock_tenant = _make_mock_tenant()
    MockTenant.return_value = mock_tenant
    MockDomain.return_value.save.side_effect = DjangoIntegrityError("unique constraint")

    with pytest.raises(SubdomainAlreadyExistsError):
        TenantRegistrationService.register("ACME Corp", "acme", "admin@acme.com")

    mock_tenant.delete.assert_called_once()


@patch("apps.tenants.services.Subscription")
@patch("apps.tenants.services.Plan")
@patch("apps.tenants.services.Domain")
@patch("apps.tenants.services.Tenant")
def test_no_orphan_on_domain_integrity_error(MockTenant, MockDomain, MockPlan, MockSub):
    """Tenant must be deleted (no orphan) when domain save raises IntegrityError."""
    from django.db import IntegrityError as DjangoIntegrityError

    mock_tenant = _make_mock_tenant()
    MockTenant.return_value = mock_tenant
    MockDomain.return_value.save.side_effect = DjangoIntegrityError("unique constraint")

    with pytest.raises(SubdomainAlreadyExistsError):
        TenantRegistrationService.register("ACME Corp", "acme", "admin@acme.com")

    # Schema was cleaned up — no orphan tenant
    mock_tenant.delete.assert_called_once()
    MockSub.objects.create.assert_not_called()


# ---------------------------------------------------------------------------
# Subscription failure — generic Exception
# ---------------------------------------------------------------------------

@patch("apps.tenants.services.Subscription")
@patch("apps.tenants.services.Plan")
@patch("apps.tenants.services.Domain")
@patch("apps.tenants.services.Tenant")
def test_register_deletes_tenant_on_subscription_failure(
    MockTenant, MockDomain, MockPlan, MockSub
):
    mock_tenant = _make_mock_tenant()
    MockTenant.return_value = mock_tenant
    MockPlan.TRIAL = "trial"
    MockPlan.objects.get.return_value = _make_mock_plan()
    MockSub.objects.create.side_effect = RuntimeError("DB down")

    with pytest.raises(RuntimeError):
        TenantRegistrationService.register("ACME Corp", "acme", "admin@acme.com")

    mock_tenant.delete.assert_called_once()


@patch("apps.tenants.services.Subscription")
@patch("apps.tenants.services.Plan")
@patch("apps.tenants.services.Domain")
@patch("apps.tenants.services.Tenant")
def test_register_does_not_swallow_non_integrity_exceptions(
    MockTenant, MockDomain, MockPlan, MockSub
):
    mock_tenant = _make_mock_tenant()
    MockTenant.return_value = mock_tenant
    MockPlan.TRIAL = "trial"
    MockPlan.objects.get.side_effect = RuntimeError("trial plan missing")

    with pytest.raises(Exception):
        TenantRegistrationService.register("ACME Corp", "acme", "admin@acme.com")

    mock_tenant.delete.assert_called_once()
