"""
Integration tests for auth-rbac: JWT flows, user management, license limits,
and permission enforcement. All tests use transaction=True because they create
real tenant schemas via TenantRegistrationService (DDL cannot be rolled back).
"""
import pytest
from django.db import connection
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.tenants.models import Plan, Subscription
from apps.tenants.services import TenantRegistrationService
from apps.users.models import CustomUser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_plans():
    Plan.objects.get_or_create(nombre=Plan.TRIAL)
    Plan.objects.get_or_create(nombre=Plan.ENTERPRISE)


def _register_tenant(schema, nombre, email_admin, password='Admin123!'):
    connection.set_schema_to_public()
    _ensure_plans()
    return TenantRegistrationService.register(nombre, schema, email_admin, password)


def _create_user(tenant, email, role='admin', password='pass123!', nombre='Test User'):
    connection.set_tenant(tenant)
    return CustomUser.objects.create_user(
        email=email,
        nombre_completo=nombre,
        role=role,
        password=password,
    )


def _get_admin(tenant, email):
    """Fetch the admin user created during tenant registration."""
    connection.set_tenant(tenant)
    return CustomUser.objects.get(email=email)


def _client_for_tenant(tenant, user=None, domain=None):
    """APIClient configured to hit the tenant's domain with optional auth."""
    if domain is None:
        domain = f'{tenant.schema_name}.sgca.com'
    client = APIClient()
    client.defaults['HTTP_HOST'] = domain
    if user is not None:
        connection.set_tenant(tenant)
        access = str(RefreshToken.for_user(user).access_token)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
    return client


# ---------------------------------------------------------------------------
# Task 8.1 — JWT integration tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_login_correct_credentials_returns_200():
    tenant = _register_tenant('jwtlogin', 'JWT Login Co', 'admin@jwtlogin.com')
    user = _create_user(tenant, 'user@jwtlogin.com', password='secret123!')

    client = _client_for_tenant(tenant)
    resp = client.post('/api/auth/login/', {'email': 'user@jwtlogin.com', 'password': 'secret123!'}, format='json')

    assert resp.status_code == 200
    assert 'access' in resp.data
    assert 'refresh' in resp.data


@pytest.mark.django_db(transaction=True)
def test_login_wrong_password_returns_401():
    tenant = _register_tenant('jwtbadpw', 'Bad PW Co', 'admin@jwtbadpw.com')
    _create_user(tenant, 'user@jwtbadpw.com', password='correctpass!')

    client = _client_for_tenant(tenant)
    resp = client.post('/api/auth/login/', {'email': 'user@jwtbadpw.com', 'password': 'wrongpass!'}, format='json')

    assert resp.status_code == 401


@pytest.mark.django_db(transaction=True)
def test_login_inactive_user_returns_401():
    tenant = _register_tenant('jwtinact', 'Inactive Co', 'admin@jwtinact.com')
    user = _create_user(tenant, 'user@jwtinact.com', password='pass123!')
    connection.set_tenant(tenant)
    user.is_active = False
    user.save()

    client = _client_for_tenant(tenant)
    resp = client.post('/api/auth/login/', {'email': 'user@jwtinact.com', 'password': 'pass123!'}, format='json')

    assert resp.status_code == 401


@pytest.mark.django_db(transaction=True)
def test_token_refresh_with_valid_token():
    tenant = _register_tenant('jwtrefresh', 'Refresh Co', 'admin@jwtrefresh.com')
    user = _create_user(tenant, 'user@jwtrefresh.com')
    connection.set_tenant(tenant)
    refresh = RefreshToken.for_user(user)

    client = _client_for_tenant(tenant)
    resp = client.post('/api/auth/refresh/', {'refresh': str(refresh)}, format='json')

    assert resp.status_code == 200
    assert 'access' in resp.data


@pytest.mark.django_db(transaction=True)
def test_logout_blacklists_refresh_token():
    tenant = _register_tenant('jwtlogout', 'Logout Co', 'admin@jwtlogout.com')
    user = _create_user(tenant, 'user@jwtlogout.com')
    connection.set_tenant(tenant)
    refresh = RefreshToken.for_user(user)

    client = _client_for_tenant(tenant, user)
    resp = client.post('/api/auth/logout/', {'refresh': str(refresh)}, format='json')
    assert resp.status_code == 204

    resp2 = client.post('/api/auth/refresh/', {'refresh': str(refresh)}, format='json')
    assert resp2.status_code == 401


@pytest.mark.django_db(transaction=True)
def test_login_same_email_different_schemas_are_isolated():
    """Same email in two tenants: authenticating in one doesn't grant access to the other."""
    tenant_a = _register_tenant('isola', 'Isolation A', 'admin@isola.com')
    tenant_b = _register_tenant('isolb', 'Isolation B', 'admin@isolb.com')

    _create_user(tenant_a, 'shared@email.com', password='passA!')
    _create_user(tenant_b, 'shared@email.com', password='passB!')

    # Login to tenant A with tenant A password → success
    client_a = _client_for_tenant(tenant_a)
    resp = client_a.post('/api/auth/login/', {'email': 'shared@email.com', 'password': 'passA!'}, format='json')
    assert resp.status_code == 200

    # Login to tenant B with tenant A password → 401 (different credential)
    client_b = _client_for_tenant(tenant_b)
    resp2 = client_b.post('/api/auth/login/', {'email': 'shared@email.com', 'password': 'passA!'}, format='json')
    assert resp2.status_code == 401


# ---------------------------------------------------------------------------
# Task 8.2 — User management and license integration tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_admin_creates_user_returns_201():
    tenant = _register_tenant('umcreate', 'UM Create', 'admin@umcreate.com')
    admin = _get_admin(tenant, 'admin@umcreate.com')
    client = _client_for_tenant(tenant, admin)

    resp = client.post('/api/users/', {
        'nombre_completo': 'New User',
        'email': 'new@umcreate.com',
        'password': 'newpass123!',
        'role': 'responsable',
    }, format='json')

    assert resp.status_code == 201
    assert resp.data['email'] == 'new@umcreate.com'
    assert resp.data['role'] == 'responsable'


@pytest.mark.django_db(transaction=True)
def test_create_user_invalid_fields_returns_400():
    tenant = _register_tenant('uminvalid', 'UM Invalid', 'admin@uminvalid.com')
    admin = _get_admin(tenant, 'admin@uminvalid.com')
    client = _client_for_tenant(tenant, admin)

    resp = client.post('/api/users/', {'email': 'not-an-email'}, format='json')
    assert resp.status_code == 400


@pytest.mark.django_db(transaction=True)
def test_create_user_duplicate_email_returns_400():
    tenant = _register_tenant('umdup', 'UM Dup', 'admin@umdup.com')
    admin = _get_admin(tenant, 'admin@umdup.com')
    _create_user(tenant, 'existing@umdup.com')

    client = _client_for_tenant(tenant, admin)
    resp = client.post('/api/users/', {
        'nombre_completo': 'Dup',
        'email': 'existing@umdup.com',
        'password': 'pass123!',
        'role': 'responsable',
    }, format='json')
    assert resp.status_code == 400


@pytest.mark.django_db(transaction=True)
def test_deactivate_user_sets_is_active_false():
    tenant = _register_tenant('umdeact', 'UM Deact', 'admin@umdeact.com')
    admin = _get_admin(tenant, 'admin@umdeact.com')
    user = _create_user(tenant, 'user@umdeact.com', role='responsable')
    client = _client_for_tenant(tenant, admin)

    resp = client.post(f'/api/users/{user.id}/deactivate/')
    assert resp.status_code == 200

    connection.set_tenant(tenant)
    user.refresh_from_db()
    assert user.is_active is False


@pytest.mark.django_db(transaction=True)
def test_deactivated_user_cannot_login():
    tenant = _register_tenant('umdeactlogin', 'UM Deact Login', 'admin@umdeactlogin.com')
    admin = _get_admin(tenant, 'admin@umdeactlogin.com')
    user = _create_user(tenant, 'user@umdeactlogin.com', password='secret!')
    client = _client_for_tenant(tenant, admin)

    # Deactivate
    client.post(f'/api/users/{user.id}/deactivate/')

    # Try to login
    login_client = _client_for_tenant(tenant)
    resp = login_client.post('/api/auth/login/', {'email': 'user@umdeactlogin.com', 'password': 'secret!'}, format='json')
    assert resp.status_code == 401


@pytest.mark.django_db(transaction=True)
def test_non_admin_cannot_list_users_returns_403():
    tenant = _register_tenant('umnoadmin', 'UM No Admin', 'admin@umnoadmin.com')
    responsable = _create_user(tenant, 'resp@umnoadmin.com', role='responsable')
    client = _client_for_tenant(tenant, responsable)

    resp = client.get('/api/users/')
    assert resp.status_code == 403


@pytest.mark.django_db(transaction=True)
def test_enterprise_plan_at_limit_blocks_new_user():
    tenant = _register_tenant('umlimit', 'UM Limit', 'admin@umlimit.com')
    admin = _get_admin(tenant, 'admin@umlimit.com')

    # Switch to enterprise plan with limit 1 (admin is the 1 active user)
    connection.set_schema_to_public()
    enterprise = Plan.objects.get(nombre=Plan.ENTERPRISE)
    sub = Subscription.objects.get(tenant=tenant)
    sub.plan = enterprise
    sub.num_licencias = 1
    sub.fecha_fin = None
    sub.save()
    connection.set_tenant(tenant)

    client = _client_for_tenant(tenant, admin)
    resp = client.post('/api/users/', {
        'nombre_completo': 'Over Limit',
        'email': 'over@umlimit.com',
        'password': 'pass123!',
        'role': 'responsable',
    }, format='json')
    assert resp.status_code == 400
    assert 'licencias' in resp.data.get('detail', '').lower()


@pytest.mark.django_db(transaction=True)
def test_trial_plan_has_no_license_limit():
    tenant = _register_tenant('umtrial', 'UM Trial', 'admin@umtrial.com')
    admin = _get_admin(tenant, 'admin@umtrial.com')

    # Trial plan with num_licencias=1 should NOT block creation
    connection.set_schema_to_public()
    trial = Plan.objects.get(nombre=Plan.TRIAL)
    sub = Subscription.objects.get(tenant=tenant)
    sub.num_licencias = 1
    sub.save()
    connection.set_tenant(tenant)

    client = _client_for_tenant(tenant, admin)
    resp = client.post('/api/users/', {
        'nombre_completo': 'New User',
        'email': 'new@umtrial.com',
        'password': 'pass123!',
        'role': 'responsable',
    }, format='json')
    assert resp.status_code == 201


@pytest.mark.django_db(transaction=True)
def test_after_deactivate_can_add_under_enterprise_limit():
    tenant = _register_tenant('umdeact2', 'UM Deact 2', 'admin@umdeact2.com')
    admin = _get_admin(tenant, 'admin@umdeact2.com')
    extra = _create_user(tenant, 'extra@umdeact2.com', role='responsable')

    # Set enterprise plan limit = 2 (admin + extra = 2, at limit)
    connection.set_schema_to_public()
    enterprise = Plan.objects.get(nombre=Plan.ENTERPRISE)
    sub = Subscription.objects.get(tenant=tenant)
    sub.plan = enterprise
    sub.num_licencias = 2
    sub.fecha_fin = None
    sub.save()
    connection.set_tenant(tenant)

    client = _client_for_tenant(tenant, admin)

    # At limit: 2 active / 2 limit → should block
    resp = client.post('/api/users/', {
        'nombre_completo': 'Third',
        'email': 'third@umdeact2.com',
        'password': 'pass123!',
        'role': 'responsable',
    }, format='json')
    assert resp.status_code == 400

    # Deactivate extra → 1 active / 2 limit → should allow
    client.post(f'/api/users/{extra.id}/deactivate/')

    resp2 = client.post('/api/users/', {
        'nombre_completo': 'Third',
        'email': 'third@umdeact2.com',
        'password': 'pass123!',
        'role': 'responsable',
    }, format='json')
    assert resp2.status_code == 201


# ---------------------------------------------------------------------------
# Task 8.3 — Profile and permission tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_get_profile_returns_user_data():
    tenant = _register_tenant('profget', 'Prof Get', 'admin@profget.com')
    user = _create_user(tenant, 'user@profget.com', role='supervisor', nombre='Prof User')
    client = _client_for_tenant(tenant, user)

    resp = client.get('/api/users/me/')
    assert resp.status_code == 200
    assert resp.data['email'] == 'user@profget.com'
    assert resp.data['nombre_completo'] == 'Prof User'
    assert resp.data['role'] == 'supervisor'


@pytest.mark.django_db(transaction=True)
def test_put_profile_updates_nombre_completo():
    tenant = _register_tenant('profput', 'Prof Put', 'admin@profput.com')
    user = _create_user(tenant, 'user@profput.com')
    client = _client_for_tenant(tenant, user)

    resp = client.put('/api/users/me/', {'nombre_completo': 'Updated Name'}, format='json')
    assert resp.status_code == 200
    assert resp.data['nombre_completo'] == 'Updated Name'


@pytest.mark.django_db(transaction=True)
def test_put_profile_with_duplicate_email_returns_400():
    tenant = _register_tenant('profemaildup', 'Prof Email Dup', 'admin@profemaildup.com')
    user = _create_user(tenant, 'user@profemaildup.com')
    _create_user(tenant, 'other@profemaildup.com', role='responsable')
    client = _client_for_tenant(tenant, user)

    resp = client.put('/api/users/me/', {'email': 'other@profemaildup.com'}, format='json')
    assert resp.status_code == 400
    assert 'email' in resp.data


@pytest.mark.django_db(transaction=True)
def test_change_password_correct_current_returns_200():
    tenant = _register_tenant('profchpw', 'Prof ChPw', 'admin@profchpw.com')
    user = _create_user(tenant, 'user@profchpw.com', password='oldpass123!')
    client = _client_for_tenant(tenant, user)

    resp = client.put('/api/users/me/change-password/', {
        'current_password': 'oldpass123!',
        'new_password': 'newpass456!',
    }, format='json')
    assert resp.status_code == 200


@pytest.mark.django_db(transaction=True)
def test_change_password_wrong_current_returns_400():
    tenant = _register_tenant('profchpwbad', 'Prof ChPw Bad', 'admin@profchpwbad.com')
    user = _create_user(tenant, 'user@profchpwbad.com', password='correct!')
    client = _client_for_tenant(tenant, user)

    resp = client.put('/api/users/me/change-password/', {
        'current_password': 'wrongpass',
        'new_password': 'newpass456!',
    }, format='json')
    assert resp.status_code == 400
    assert 'current_password' in resp.data


@pytest.mark.django_db(transaction=True)
def test_unauthenticated_cannot_access_profile():
    tenant = _register_tenant('profunauth', 'Prof Unauth', 'admin@profunauth.com')
    client = _client_for_tenant(tenant)

    resp = client.get('/api/users/me/')
    assert resp.status_code == 401


@pytest.mark.django_db(transaction=True)
def test_require_role_supervisor_allows_supervisor_rejects_admin():
    """Unit-style test for RequireRole class."""
    from unittest.mock import MagicMock
    from apps.users.permissions import RequireRole

    perm = RequireRole('supervisor')

    req_supervisor = MagicMock()
    req_supervisor.user.is_authenticated = True
    req_supervisor.user.role = 'supervisor'
    assert perm.has_permission(req_supervisor, None) is True

    req_admin = MagicMock()
    req_admin.user.is_authenticated = True
    req_admin.user.role = 'admin'
    assert perm.has_permission(req_admin, None) is False


@pytest.mark.django_db(transaction=True)
def test_is_admin_tenant_rejects_all_non_admin_roles():
    from unittest.mock import MagicMock
    from apps.users.permissions import IsAdminTenant

    perm = IsAdminTenant()
    for role in ('responsable', 'supervisor', 'verificador'):
        req = MagicMock()
        req.user.is_authenticated = True
        req.user.role = role
        assert perm.has_permission(req, None) is False, f"Expected False for {role}"
