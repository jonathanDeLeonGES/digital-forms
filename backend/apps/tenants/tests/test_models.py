"""
RED phase tests for Tenant and Domain models.
These tests verify the model structure and subdomain validation logic.
"""
import pytest
from django.core.exceptions import ValidationError


# ---------------------------------------------------------------------------
# Tenant model structure
# ---------------------------------------------------------------------------

def test_tenant_model_importable():
    from apps.tenants.models import Tenant
    assert Tenant is not None


def test_domain_model_importable():
    from apps.tenants.models import Domain
    assert Domain is not None


def test_tenant_has_nombre_empresa_field():
    from apps.tenants.models import Tenant
    field = Tenant._meta.get_field('nombre_empresa')
    assert field.max_length == 200


def test_tenant_has_email_admin_field():
    from apps.tenants.models import Tenant
    field = Tenant._meta.get_field('email_admin')
    assert field.__class__.__name__ == 'EmailField'


def test_tenant_has_created_at_field():
    from apps.tenants.models import Tenant
    field = Tenant._meta.get_field('created_at')
    assert field.auto_now_add is True


def test_tenant_auto_create_schema_is_true():
    from apps.tenants.models import Tenant
    assert Tenant.auto_create_schema is True


def test_tenant_auto_drop_schema_is_true():
    from apps.tenants.models import Tenant
    assert Tenant.auto_drop_schema is True


# ---------------------------------------------------------------------------
# Subdomain validator
# ---------------------------------------------------------------------------

def test_validator_importable():
    from apps.tenants.validators import validate_subdomain_format
    assert callable(validate_subdomain_format)


def test_validator_accepts_simple_subdomain():
    from apps.tenants.validators import validate_subdomain_format
    validate_subdomain_format('acme')  # should not raise


def test_validator_accepts_hyphenated_subdomain():
    from apps.tenants.validators import validate_subdomain_format
    validate_subdomain_format('my-company')  # should not raise


def test_validator_accepts_alphanumeric_subdomain():
    from apps.tenants.validators import validate_subdomain_format
    validate_subdomain_format('company123')  # should not raise


def test_validator_accepts_single_char_subdomain():
    from apps.tenants.validators import validate_subdomain_format
    validate_subdomain_format('a')  # should not raise


def test_validator_accepts_single_digit_subdomain():
    from apps.tenants.validators import validate_subdomain_format
    validate_subdomain_format('9')  # should not raise


def test_validator_rejects_uppercase():
    from apps.tenants.validators import validate_subdomain_format
    with pytest.raises(ValidationError):
        validate_subdomain_format('ACME')


def test_validator_rejects_space():
    from apps.tenants.validators import validate_subdomain_format
    with pytest.raises(ValidationError):
        validate_subdomain_format('my tenant')


def test_validator_rejects_leading_hyphen():
    from apps.tenants.validators import validate_subdomain_format
    with pytest.raises(ValidationError):
        validate_subdomain_format('-acme')


def test_validator_rejects_trailing_hyphen():
    from apps.tenants.validators import validate_subdomain_format
    with pytest.raises(ValidationError):
        validate_subdomain_format('acme-')


def test_validator_rejects_underscore():
    from apps.tenants.validators import validate_subdomain_format
    with pytest.raises(ValidationError):
        validate_subdomain_format('my_company')


def test_validator_rejects_dot():
    from apps.tenants.validators import validate_subdomain_format
    with pytest.raises(ValidationError):
        validate_subdomain_format('my.company')


def test_validator_rejects_empty_string():
    from apps.tenants.validators import validate_subdomain_format
    with pytest.raises(ValidationError):
        validate_subdomain_format('')


# ---------------------------------------------------------------------------
# Tenant.clean() applies subdomain validation
# ---------------------------------------------------------------------------

def test_tenant_clean_rejects_invalid_schema_name():
    from apps.tenants.models import Tenant
    tenant = Tenant(
        schema_name='INVALID-UPPER',
        nombre_empresa='Test Corp',
        email_admin='admin@test.com',
    )
    with pytest.raises(ValidationError):
        tenant.clean()


def test_tenant_clean_accepts_valid_schema_name():
    from apps.tenants.models import Tenant
    tenant = Tenant(
        schema_name='valid-name',
        nombre_empresa='Test Corp',
        email_admin='admin@test.com',
    )
    # Should not raise
    tenant.clean()


# ---------------------------------------------------------------------------
# Plan model — RED phase: these fail until Plan is defined in models.py
# ---------------------------------------------------------------------------

def test_plan_has_trial_constant():
    from apps.tenants.models import Plan
    assert Plan.TRIAL == 'trial'


def test_plan_has_enterprise_constant():
    from apps.tenants.models import Plan
    assert Plan.ENTERPRISE == 'enterprise'


def test_plan_nombre_choices_contains_both_plans():
    from apps.tenants.models import Plan
    choice_values = [c[0] for c in Plan.NOMBRE_CHOICES]
    assert 'trial' in choice_values
    assert 'enterprise' in choice_values


# ---------------------------------------------------------------------------
# Subscription.is_active() — RED phase: fail until Subscription is defined
# ---------------------------------------------------------------------------

def _make_subscription(plan_nombre, fecha_fin=None):
    """Build a Subscription instance without hitting the DB.

    Django 5.x valida que el valor asignado a un FK sea una instancia del
    modelo relacionado, por lo que MagicMock() ya no es válido.
    Usamos Plan.__new__(Plan) para crear una instancia real sin persistirla
    y set_cached_value() para inyectarla en la caché interna del descriptor
    FK, evitando la validación de tipo y cualquier consulta a la DB.
    """
    from django.db.models.base import ModelState
    from apps.tenants.models import Plan, Subscription
    sub = Subscription.__new__(Subscription)
    sub._state = ModelState()  # __new__ no llama a __init__, _state no existe
    plan = Plan.__new__(Plan)
    plan.nombre = plan_nombre
    Subscription._meta.get_field("plan").set_cached_value(sub, plan)
    sub.fecha_fin = fecha_fin
    return sub


def test_is_active_trial_with_future_fecha_fin():
    from datetime import date, timedelta
    sub = _make_subscription('trial', fecha_fin=date.today() + timedelta(days=5))
    assert sub.is_active() is True


def test_is_active_trial_expires_today():
    from datetime import date
    sub = _make_subscription('trial', fecha_fin=date.today())
    assert sub.is_active() is True


def test_is_active_trial_expired_yesterday():
    from datetime import date, timedelta
    sub = _make_subscription('trial', fecha_fin=date.today() - timedelta(days=1))
    assert sub.is_active() is False


def test_is_active_enterprise_no_fecha_fin():
    sub = _make_subscription('enterprise', fecha_fin=None)
    assert sub.is_active() is True


def test_is_active_trial_no_fecha_fin():
    sub = _make_subscription('trial', fecha_fin=None)
    assert sub.is_active() is False


def test_subscription_has_num_licencias_field():
    from apps.tenants.models import Subscription
    field = Subscription._meta.get_field('num_licencias')
    assert field.null is True
    assert field.blank is True


def test_subscription_has_fecha_fin_field():
    from apps.tenants.models import Subscription
    field = Subscription._meta.get_field('fecha_fin')
    assert field.null is True
    assert field.blank is True
