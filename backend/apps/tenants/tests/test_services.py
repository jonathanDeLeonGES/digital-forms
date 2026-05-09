"""
RED phase: tests for TenantRegistrationService.
Before services.py exists, all tests fail with ImportError.
After implementation, all pass via static analysis (Django not installed in shell).
"""
from contextlib import contextmanager
from datetime import date, timedelta
from unittest.mock import MagicMock, call, patch

import pytest

from apps.tenants.exceptions import SubdomainAlreadyExistsError
from apps.tenants.services import TenantRegistrationService


@pytest.fixture(autouse=True)
def patch_transaction_atomic():
    @contextmanager
    def noop():
        yield

    with patch("apps.tenants.services.transaction.atomic", noop):
        yield


@pytest.fixture(autouse=True)
def patch_connection():
    with patch("apps.tenants.services.connection") as mock_conn:
        yield mock_conn


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

@patch("apps.tenants.services.CustomUser", create=True)
@patch("apps.tenants.services.Subscription")
@patch("apps.tenants.services.Plan")
@patch("apps.tenants.services.Domain")
@patch("apps.tenants.services.Tenant")
def test_register_saves_tenant_with_correct_fields(MockTenant, MockDomain, MockPlan, MockSub, MockUser):
    mock_tenant = _make_mock_tenant()
    MockTenant.return_value = mock_tenant
    MockPlan.TRIAL = "trial"
    MockPlan.objects.get.return_value = _make_mock_plan()

    TenantRegistrationService.register("ACME Corp", "acme", "admin@acme.com", "pass1234")

    MockTenant.assert_called_once_with(
        schema_name="acme",
        nombre_empresa="ACME Corp",
        email_admin="admin@acme.com",
    )
    mock_tenant.save.assert_called_once()


@patch("apps.tenants.services.CustomUser", create=True)
@patch("apps.tenants.services.Subscription")
@patch("apps.tenants.services.Plan")
@patch("apps.tenants.services.Domain")
@patch("apps.tenants.services.Tenant")
def test_register_creates_domain_with_correct_url(MockTenant, MockDomain, MockPlan, MockSub, MockUser):
    mock_tenant = _make_mock_tenant()
    MockTenant.return_value = mock_tenant
    MockPlan.TRIAL = "trial"
    MockPlan.objects.get.return_value = _make_mock_plan()

    TenantRegistrationService.register("ACME Corp", "acme", "admin@acme.com", "pass1234")

    MockDomain.assert_called_once_with(
        domain="acme.sgca.com",
        tenant=mock_tenant,
        is_primary=True,
    )
    MockDomain.return_value.save.assert_called_once()


@patch("apps.tenants.services.CustomUser", create=True)
@patch("apps.tenants.services.Subscription")
@patch("apps.tenants.services.Plan")
@patch("apps.tenants.services.Domain")
@patch("apps.tenants.services.Tenant")
def test_register_creates_trial_subscription_14_days(MockTenant, MockDomain, MockPlan, MockSub, MockUser):
    mock_tenant = _make_mock_tenant()
    MockTenant.return_value = mock_tenant
    MockPlan.TRIAL = "trial"
    mock_plan = _make_mock_plan()
    MockPlan.objects.get.return_value = mock_plan

    TenantRegistrationService.register("ACME Corp", "acme", "admin@acme.com", "pass1234")

    MockSub.objects.create.assert_called_once_with(
        tenant=mock_tenant,
        plan=mock_plan,
        fecha_fin=date.today() + timedelta(days=14),
    )


@patch("apps.tenants.services.CustomUser", create=True)
@patch("apps.tenants.services.Subscription")
@patch("apps.tenants.services.Plan")
@patch("apps.tenants.services.Domain")
@patch("apps.tenants.services.Tenant")
def test_register_creates_admin_user_in_tenant_schema(MockTenant, MockDomain, MockPlan, MockSub, MockUser):
    mock_tenant = _make_mock_tenant()
    MockTenant.return_value = mock_tenant
    MockPlan.TRIAL = "trial"
    MockPlan.objects.get.return_value = _make_mock_plan()

    TenantRegistrationService.register("ACME Corp", "acme", "admin@acme.com", "pass1234")

    MockUser.objects.create_user.assert_called_once_with(
        email="admin@acme.com",
        nombre_completo="ACME Corp",
        role="admin",
        password="pass1234",
    )


@patch("apps.tenants.services.CustomUser", create=True)
@patch("apps.tenants.services.Subscription")
@patch("apps.tenants.services.Plan")
@patch("apps.tenants.services.Domain")
@patch("apps.tenants.services.Tenant")
def test_register_returns_tenant(MockTenant, MockDomain, MockPlan, MockSub, MockUser):
    mock_tenant = _make_mock_tenant()
    MockTenant.return_value = mock_tenant
    MockPlan.TRIAL = "trial"
    MockPlan.objects.get.return_value = _make_mock_plan()

    result = TenantRegistrationService.register("ACME Corp", "acme", "admin@acme.com", "pass1234")

    assert result is mock_tenant


# ---------------------------------------------------------------------------
# Subdomain duplicate — IntegrityError on Domain.save()
# ---------------------------------------------------------------------------

@patch("apps.tenants.services.CustomUser", create=True)
@patch("apps.tenants.services.Subscription")
@patch("apps.tenants.services.Plan")
@patch("apps.tenants.services.Domain")
@patch("apps.tenants.services.Tenant")
def test_register_raises_subdomain_error_on_integrity_error(
    MockTenant, MockDomain, MockPlan, MockSub, MockUser
):
    from django.db import IntegrityError as DjangoIntegrityError

    mock_tenant = _make_mock_tenant()
    MockTenant.return_value = mock_tenant
    MockDomain.return_value.save.side_effect = DjangoIntegrityError("unique constraint")

    with pytest.raises(SubdomainAlreadyExistsError):
        TenantRegistrationService.register("ACME Corp", "acme", "admin@acme.com", "pass1234")


@patch("apps.tenants.services.CustomUser", create=True)
@patch("apps.tenants.services.Subscription")
@patch("apps.tenants.services.Plan")
@patch("apps.tenants.services.Domain")
@patch("apps.tenants.services.Tenant")
def test_register_deletes_tenant_on_subdomain_duplicate(
    MockTenant, MockDomain, MockPlan, MockSub, MockUser
):
    from django.db import IntegrityError as DjangoIntegrityError

    mock_tenant = _make_mock_tenant()
    MockTenant.return_value = mock_tenant
    MockDomain.return_value.save.side_effect = DjangoIntegrityError("unique constraint")

    with pytest.raises(SubdomainAlreadyExistsError):
        TenantRegistrationService.register("ACME Corp", "acme", "admin@acme.com", "pass1234")

    mock_tenant.delete.assert_called_once()


@patch("apps.tenants.services.CustomUser", create=True)
@patch("apps.tenants.services.Subscription")
@patch("apps.tenants.services.Plan")
@patch("apps.tenants.services.Domain")
@patch("apps.tenants.services.Tenant")
def test_no_orphan_on_domain_integrity_error(MockTenant, MockDomain, MockPlan, MockSub, MockUser):
    """Tenant must be deleted (no orphan) when domain save raises IntegrityError."""
    from django.db import IntegrityError as DjangoIntegrityError

    mock_tenant = _make_mock_tenant()
    MockTenant.return_value = mock_tenant
    MockDomain.return_value.save.side_effect = DjangoIntegrityError("unique constraint")

    with pytest.raises(SubdomainAlreadyExistsError):
        TenantRegistrationService.register("ACME Corp", "acme", "admin@acme.com", "pass1234")

    mock_tenant.delete.assert_called_once()
    MockSub.objects.create.assert_not_called()


# ---------------------------------------------------------------------------
# Subscription failure — generic Exception
# ---------------------------------------------------------------------------

@patch("apps.tenants.services.CustomUser", create=True)
@patch("apps.tenants.services.Subscription")
@patch("apps.tenants.services.Plan")
@patch("apps.tenants.services.Domain")
@patch("apps.tenants.services.Tenant")
def test_register_deletes_tenant_on_subscription_failure(
    MockTenant, MockDomain, MockPlan, MockSub, MockUser
):
    mock_tenant = _make_mock_tenant()
    MockTenant.return_value = mock_tenant
    MockPlan.TRIAL = "trial"
    MockPlan.objects.get.return_value = _make_mock_plan()
    MockSub.objects.create.side_effect = RuntimeError("DB down")

    with pytest.raises(RuntimeError):
        TenantRegistrationService.register("ACME Corp", "acme", "admin@acme.com", "pass1234")

    mock_tenant.delete.assert_called_once()


@patch("apps.tenants.services.CustomUser", create=True)
@patch("apps.tenants.services.Subscription")
@patch("apps.tenants.services.Plan")
@patch("apps.tenants.services.Domain")
@patch("apps.tenants.services.Tenant")
def test_register_does_not_swallow_non_integrity_exceptions(
    MockTenant, MockDomain, MockPlan, MockSub, MockUser
):
    mock_tenant = _make_mock_tenant()
    MockTenant.return_value = mock_tenant
    MockPlan.TRIAL = "trial"
    MockPlan.objects.get.side_effect = RuntimeError("trial plan missing")

    with pytest.raises(Exception):
        TenantRegistrationService.register("ACME Corp", "acme", "admin@acme.com", "pass1234")

    mock_tenant.delete.assert_called_once()
