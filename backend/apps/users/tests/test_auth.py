"""
Unit tests for auth-rbac: CustomUser model, JWT token claims,
login/refresh/logout views, and permission classes.
Integration tests are in test_users.py and test_permissions.py.
"""
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Task 2.1 — CustomUser model structure
# ---------------------------------------------------------------------------

def test_custom_user_importable():
    from apps.users.models import CustomUser
    assert CustomUser is not None


def test_custom_user_email_is_username_field():
    from apps.users.models import CustomUser
    assert CustomUser.USERNAME_FIELD == 'email'


def test_custom_user_has_no_username_field():
    from apps.users.models import CustomUser
    field_names = [f.name for f in CustomUser._meta.get_fields()]
    assert 'username' not in field_names


def test_custom_user_has_nombre_completo_field():
    from apps.users.models import CustomUser
    field = CustomUser._meta.get_field('nombre_completo')
    assert field.max_length == 200


def test_custom_user_has_role_field():
    from apps.users.models import CustomUser
    field = CustomUser._meta.get_field('role')
    assert field.max_length == 20


def test_custom_user_role_choices_has_four_values():
    from apps.users.models import CustomUser
    role_values = [c[0] for c in CustomUser.ROLES]
    assert set(role_values) == {'admin', 'responsable', 'supervisor', 'verificador'}


def test_custom_user_email_is_unique():
    from apps.users.models import CustomUser
    field = CustomUser._meta.get_field('email')
    assert field.unique is True


def test_custom_user_has_created_at_auto_now_add():
    from apps.users.models import CustomUser
    field = CustomUser._meta.get_field('created_at')
    assert field.auto_now_add is True


# ---------------------------------------------------------------------------
# Task 3.1 — CustomTokenObtainPairSerializer claims
# ---------------------------------------------------------------------------

def test_token_serializer_importable():
    from apps.users.tokens import CustomTokenObtainPairSerializer
    assert CustomTokenObtainPairSerializer is not None


def test_token_serializer_adds_role_and_tenant_claims():
    from apps.users.tokens import CustomTokenObtainPairSerializer

    mock_user = MagicMock()
    mock_user.role = 'supervisor'

    with patch('apps.users.tokens.connection') as mock_conn:
        mock_conn.schema_name = 'empresa_test'
        with patch(
            'rest_framework_simplejwt.serializers.TokenObtainPairSerializer.get_token'
        ) as mock_super:
            mock_token = {}
            mock_super.return_value = mock_token

            result = CustomTokenObtainPairSerializer.get_token(mock_user)

            assert result['role'] == 'supervisor'
            assert result['tenant'] == 'empresa_test'


# ---------------------------------------------------------------------------
# Task 4.1 — RequireRole and IsAdminTenant permissions
# ---------------------------------------------------------------------------

def test_require_role_importable():
    from apps.users.permissions import IsAdminTenant, RequireRole
    assert callable(RequireRole)
    assert callable(IsAdminTenant)


def test_require_role_allows_matching_role():
    from apps.users.permissions import RequireRole
    perm = RequireRole('admin', 'supervisor')
    request = MagicMock()
    request.user.is_authenticated = True
    request.user.role = 'admin'
    assert perm.has_permission(request, None) is True


def test_require_role_allows_second_matching_role():
    from apps.users.permissions import RequireRole
    perm = RequireRole('admin', 'supervisor')
    request = MagicMock()
    request.user.is_authenticated = True
    request.user.role = 'supervisor'
    assert perm.has_permission(request, None) is True


def test_require_role_rejects_wrong_role():
    from apps.users.permissions import RequireRole
    perm = RequireRole('admin')
    request = MagicMock()
    request.user.is_authenticated = True
    request.user.role = 'responsable'
    assert perm.has_permission(request, None) is False


def test_require_role_rejects_anonymous():
    from apps.users.permissions import RequireRole
    perm = RequireRole('admin')
    request = MagicMock()
    request.user.is_authenticated = False
    assert perm.has_permission(request, None) is False


def test_is_admin_tenant_allows_admin():
    from apps.users.permissions import IsAdminTenant
    perm = IsAdminTenant()
    request = MagicMock()
    request.user.is_authenticated = True
    request.user.role = 'admin'
    assert perm.has_permission(request, None) is True


@pytest.mark.parametrize('role', ['responsable', 'supervisor', 'verificador'])
def test_is_admin_tenant_rejects_non_admin(role):
    from apps.users.permissions import IsAdminTenant
    perm = IsAdminTenant()
    request = MagicMock()
    request.user.is_authenticated = True
    request.user.role = role
    assert perm.has_permission(request, None) is False


# ---------------------------------------------------------------------------
# Task 5.1 — UserManagementService structure
# ---------------------------------------------------------------------------

def test_service_importable():
    from apps.users.services import UserManagementService
    svc = UserManagementService()
    assert hasattr(svc, 'create_user')
    assert hasattr(svc, 'update_user')
    assert hasattr(svc, 'deactivate_user')
    assert hasattr(svc, '_check_license_limit')


def test_exceptions_importable():
    from apps.users.exceptions import (
        EmailAlreadyExistsError,
        LicenseLimitExceededError,
        UserNotFoundError,
    )
    assert True
