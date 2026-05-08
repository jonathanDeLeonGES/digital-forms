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
