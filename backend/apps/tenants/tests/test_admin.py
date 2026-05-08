"""
Unit tests for TenantAdmin and SubscriptionAdmin (tasks 5.1 and 5.2).
Static analysis only — mocks replace ORM calls, no DB required.
"""
from datetime import date, timedelta
from unittest.mock import MagicMock, patch, call

import pytest

from apps.tenants.admin import (
    ChangeToEnterpriseForm,
    ExtendTrialForm,
    TenantAdmin,
    SubscriptionAdmin,
    UpdateLicenseCountForm,
)


# ---------------------------------------------------------------------------
# ChangeToEnterpriseForm validation
# ---------------------------------------------------------------------------

def test_enterprise_form_valid_with_positive_licencias():
    form = ChangeToEnterpriseForm(data={"num_licencias": 10})
    assert form.is_valid()


def test_enterprise_form_invalid_with_zero_licencias():
    form = ChangeToEnterpriseForm(data={"num_licencias": 0})
    assert not form.is_valid()
    assert "num_licencias" in form.errors


def test_enterprise_form_invalid_with_negative_licencias():
    form = ChangeToEnterpriseForm(data={"num_licencias": -1})
    assert not form.is_valid()


# ---------------------------------------------------------------------------
# ExtendTrialForm validation
# ---------------------------------------------------------------------------

def test_extend_trial_form_valid_with_future_date():
    future = date.today() + timedelta(days=7)
    form = ExtendTrialForm(data={"fecha_fin": future.isoformat()})
    assert form.is_valid()


def test_extend_trial_form_invalid_with_today():
    form = ExtendTrialForm(data={"fecha_fin": date.today().isoformat()})
    assert not form.is_valid()
    assert "fecha_fin" in form.errors


def test_extend_trial_form_invalid_with_past_date():
    past = date.today() - timedelta(days=1)
    form = ExtendTrialForm(data={"fecha_fin": past.isoformat()})
    assert not form.is_valid()


# ---------------------------------------------------------------------------
# UpdateLicenseCountForm validation
# ---------------------------------------------------------------------------

def test_update_license_form_valid_with_positive():
    form = UpdateLicenseCountForm(data={"num_licencias": 5})
    assert form.is_valid()


def test_update_license_form_invalid_with_zero():
    form = UpdateLicenseCountForm(data={"num_licencias": 0})
    assert not form.is_valid()
    assert "num_licencias" in form.errors


# ---------------------------------------------------------------------------
# TenantAdmin computed columns
# ---------------------------------------------------------------------------

def _make_tenant_admin():
    from django.contrib.admin import site
    return TenantAdmin(model=MagicMock(), admin_site=site)


def test_get_subdominio_returns_schema_name():
    ta = _make_tenant_admin()
    obj = MagicMock()
    obj.schema_name = "acme"
    assert ta.get_subdominio(obj) == "acme"


def test_get_plan_actual_returns_plan_nombre():
    ta = _make_tenant_admin()
    obj = MagicMock()
    obj.subscription.plan.nombre = "trial"
    assert ta.get_plan_actual(obj) == "trial"


def test_get_estado_acceso_active():
    ta = _make_tenant_admin()
    obj = MagicMock()
    obj.subscription.is_active.return_value = True
    assert ta.get_estado_acceso(obj) == "Activo"


def test_get_estado_acceso_blocked():
    ta = _make_tenant_admin()
    obj = MagicMock()
    obj.subscription.is_active.return_value = False
    assert ta.get_estado_acceso(obj) == "Bloqueado"


def test_get_trial_expires_at_returns_fecha_fin():
    ta = _make_tenant_admin()
    obj = MagicMock()
    obj.subscription.fecha_fin = date(2026, 6, 1)
    assert ta.get_trial_expires_at(obj) == date(2026, 6, 1)


def test_get_num_licencias_returns_dash_when_none():
    ta = _make_tenant_admin()
    obj = MagicMock()
    obj.subscription.num_licencias = None
    assert ta.get_num_licencias(obj) == "—"


def test_get_num_licencias_returns_value():
    ta = _make_tenant_admin()
    obj = MagicMock()
    obj.subscription.num_licencias = 20
    assert ta.get_num_licencias(obj) == 20


# ---------------------------------------------------------------------------
# TenantAdmin.change_to_enterprise action — intermediate page
# ---------------------------------------------------------------------------

@patch("apps.tenants.admin.Plan")
@patch("apps.tenants.admin.Tenant")
def test_change_to_enterprise_renders_template_on_get(MockTenant, MockPlan):
    ta = _make_tenant_admin()
    request = MagicMock()
    request.POST.get.return_value = None  # no _apply
    queryset = MagicMock()

    response = ta.change_to_enterprise(request, queryset)

    assert hasattr(response, "template_name") or response is not None


@patch("apps.tenants.admin.Plan")
@patch("apps.tenants.admin.Tenant")
def test_change_to_enterprise_updates_subscriptions_on_apply(MockTenant, MockPlan):
    ta = _make_tenant_admin()

    mock_sub = MagicMock()
    mock_tenant_obj = MagicMock()
    mock_tenant_obj.subscription = mock_sub

    enterprise_plan = MagicMock()
    MockPlan.objects.get.return_value = enterprise_plan
    MockPlan.ENTERPRISE = "enterprise"

    MockTenant.objects.filter.return_value.select_related.return_value = [mock_tenant_obj]

    request = MagicMock()
    request.POST.get.return_value = "1"  # _apply present
    request.POST.__getitem__ = MagicMock(return_value="10")
    request.POST.getlist.return_value = ["1"]
    # Simulate valid form data
    request.POST.get = lambda key, default=None: {
        "_apply": "1",
        "num_licencias": "10",
    }.get(key, default)

    # Build a real POST dict for the form
    with patch.object(ta, "message_user"):
        with patch("apps.tenants.admin.ChangeToEnterpriseForm") as MockForm:
            form_instance = MagicMock()
            form_instance.is_valid.return_value = True
            form_instance.cleaned_data = {"num_licencias": 10}
            MockForm.return_value = form_instance

            ta.change_to_enterprise(request, MagicMock())

    mock_sub.save.assert_called_once()
    assert mock_sub.fecha_fin is None
    assert mock_sub.num_licencias == 10
    assert mock_sub.plan == enterprise_plan
