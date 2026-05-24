"""Tests de integración de API para acciones (Task 7.2 & 7.3)."""
import pytest
from django.db import connection
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.tenants.models import Plan
from apps.tenants.services import TenantRegistrationService
from apps.issues.services import IssueService
from apps.acciones.services import AccionService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_plans():
    connection.set_schema_to_public()
    Plan.objects.get_or_create(nombre=Plan.TRIAL)
    Plan.objects.get_or_create(nombre=Plan.ENTERPRISE)


def _register(schema, nombre, email):
    connection.set_schema_to_public()
    _ensure_plans()
    return TenantRegistrationService.register(nombre, schema, email, 'Admin123!')


def _get_user(tenant, email):
    from apps.users.models import CustomUser
    connection.set_tenant(tenant)
    return CustomUser.objects.get(email=email)


def _make_user(tenant, email, role):
    from apps.users.models import CustomUser
    connection.set_tenant(tenant)
    return CustomUser.objects.create_user(
        email=email, nombre_completo='User', role=role, password='pass!'
    )


def _client(tenant, user=None):
    client = APIClient()
    client.defaults['HTTP_HOST'] = f'{tenant.schema_name}.localhost'
    if user:
        connection.set_tenant(tenant)
        token = str(RefreshToken.for_user(user).access_token)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    return client


_ISSUE_CHAIN = ['abierto', 'en_analisis', 'acciones_generadas', 'cerrado']

def _make_issue(tenant, user, estado='abierto'):
    connection.set_tenant(tenant)
    issue = IssueService.create_issue(
        tipo='incidente', titulo='Test', descripcion='desc',
        fecha_evento='2026-01-01', area='Planta', gravedad='baja',
        reportado_por=user,
    )
    for s in _ISSUE_CHAIN[1:_ISSUE_CHAIN.index(estado) + 1]:
        IssueService.transition_state(issue, s, user)
    return issue


def _accion_payload(issue_id, responsable_id, **overrides):
    base = {
        'issue_id': issue_id,
        'tipo': 'correctiva',
        'resultado_esperado': 'Corregir el proceso fallido',
        'responsable_id': responsable_id,
        'fecha_limite': '2026-12-31',
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Task 7.2 — Tests de integración de API
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_create_accion_admin_returns_201():
    tenant = _register('aapi1', 'AAPI1', 'admin@aapi1.com')
    admin = _get_user(tenant, 'admin@aapi1.com')
    resp_user = _make_user(tenant, 'r@aapi1.com', 'responsable')
    issue = _make_issue(tenant, admin, estado='en_analisis')
    client = _client(tenant, admin)

    r = client.post('/api/acciones/', _accion_payload(issue.id, resp_user.id), format='json')
    assert r.status_code == 201
    assert r.data['estado'] == 'abierto'
    assert r.data['tipo'] == 'correctiva'


@pytest.mark.django_db(transaction=True)
def test_create_accion_responsable_returns_403():
    tenant = _register('aapi2', 'AAPI2', 'admin@aapi2.com')
    admin = _get_user(tenant, 'admin@aapi2.com')
    resp_user = _make_user(tenant, 'r@aapi2.com', 'responsable')
    issue = _make_issue(tenant, admin)
    client = _client(tenant, resp_user)

    r = client.post('/api/acciones/', _accion_payload(issue.id, resp_user.id), format='json')
    assert r.status_code == 403


@pytest.mark.django_db(transaction=True)
def test_create_accion_invalid_issue_returns_400():
    tenant = _register('aapi3', 'AAPI3', 'admin@aapi3.com')
    admin = _get_user(tenant, 'admin@aapi3.com')
    resp_user = _make_user(tenant, 'r@aapi3.com', 'responsable')
    client = _client(tenant, admin)

    r = client.post('/api/acciones/', _accion_payload(99999, resp_user.id), format='json')
    assert r.status_code == 400


@pytest.mark.django_db(transaction=True)
def test_list_acciones_scope_by_role():
    tenant = _register('aapi4', 'AAPI4', 'admin@aapi4.com')
    admin = _get_user(tenant, 'admin@aapi4.com')
    resp1 = _make_user(tenant, 'r1@aapi4.com', 'responsable')
    resp2 = _make_user(tenant, 'r2@aapi4.com', 'responsable')
    issue = _make_issue(tenant, admin, estado='en_analisis')
    connection.set_tenant(tenant)
    AccionService.create_accion(issue, 'correctiva', 'res', resp1, '2026-12-31', admin)
    AccionService.create_accion(issue, 'preventiva', 'res', resp2, '2026-12-31', admin)

    client_resp1 = _client(tenant, resp1)
    r = client_resp1.get('/api/acciones/')
    assert r.status_code == 200
    assert r.data['count'] == 1

    client_admin = _client(tenant, admin)
    r = client_admin.get('/api/acciones/')
    assert r.status_code == 200
    assert r.data['count'] == 2


@pytest.mark.django_db(transaction=True)
def test_transition_valid_updates_state():
    tenant = _register('aapi5', 'AAPI5', 'admin@aapi5.com')
    admin = _get_user(tenant, 'admin@aapi5.com')
    resp = _make_user(tenant, 'r@aapi5.com', 'responsable')
    issue = _make_issue(tenant, admin, estado='en_analisis')
    connection.set_tenant(tenant)
    accion = AccionService.create_accion(issue, 'correctiva', 'res', resp, '2026-12-31', admin)
    client = _client(tenant, resp)

    r = client.post(
        f'/api/acciones/{accion.id}/transition/',
        {'estado': 'en_proceso', 'comentario': 'Iniciando'},
        format='json',
    )
    assert r.status_code == 200
    assert r.data['estado'] == 'en_proceso'


@pytest.mark.django_db(transaction=True)
def test_transition_invalid_returns_400():
    tenant = _register('aapi6', 'AAPI6', 'admin@aapi6.com')
    admin = _get_user(tenant, 'admin@aapi6.com')
    resp = _make_user(tenant, 'r@aapi6.com', 'responsable')
    issue = _make_issue(tenant, admin, estado='en_analisis')
    connection.set_tenant(tenant)
    accion = AccionService.create_accion(issue, 'correctiva', 'res', resp, '2026-12-31', admin)
    client = _client(tenant, admin)

    r = client.post(
        f'/api/acciones/{accion.id}/transition/',
        {'estado': 'verificado'},
        format='json',
    )
    assert r.status_code == 400


@pytest.mark.django_db(transaction=True)
def test_transition_wrong_role_returns_403():
    tenant = _register('aapi7', 'AAPI7', 'admin@aapi7.com')
    admin = _get_user(tenant, 'admin@aapi7.com')
    resp = _make_user(tenant, 'r@aapi7.com', 'responsable')
    sup = _make_user(tenant, 'sup@aapi7.com', 'supervisor')
    issue = _make_issue(tenant, admin, estado='en_analisis')
    connection.set_tenant(tenant)
    accion = AccionService.create_accion(issue, 'correctiva', 'res', resp, '2026-12-31', admin)
    connection.set_tenant(tenant)
    AccionService.transition_state(accion, 'en_proceso', resp)
    # supervisor intenta cerrar → OK, pero verificador intenta cerrar → 403
    ver = _make_user(tenant, 'ver@aapi7.com', 'verificador')
    client = _client(tenant, ver)
    r = client.post(f'/api/acciones/{accion.id}/transition/', {'estado': 'cerrado'}, format='json')
    assert r.status_code == 403


@pytest.mark.django_db(transaction=True)
def test_historial_visible_for_admin():
    tenant = _register('aapi8', 'AAPI8', 'admin@aapi8.com')
    admin = _get_user(tenant, 'admin@aapi8.com')
    resp = _make_user(tenant, 'r@aapi8.com', 'responsable')
    issue = _make_issue(tenant, admin, estado='en_analisis')
    connection.set_tenant(tenant)
    accion = AccionService.create_accion(issue, 'correctiva', 'res', resp, '2026-12-31', admin)
    connection.set_tenant(tenant)
    AccionService.transition_state(accion, 'en_proceso', resp)
    client = _client(tenant, admin)

    r = client.get(f'/api/acciones/{accion.id}/historial/')
    assert r.status_code == 200
    assert len(r.data) == 1


@pytest.mark.django_db(transaction=True)
def test_historial_forbidden_for_responsable():
    tenant = _register('aapi9', 'AAPI9', 'admin@aapi9.com')
    admin = _get_user(tenant, 'admin@aapi9.com')
    resp = _make_user(tenant, 'r@aapi9.com', 'responsable')
    issue = _make_issue(tenant, admin, estado='en_analisis')
    connection.set_tenant(tenant)
    accion = AccionService.create_accion(issue, 'correctiva', 'res', resp, '2026-12-31', admin)
    client = _client(tenant, resp)

    r = client.get(f'/api/acciones/{accion.id}/historial/')
    assert r.status_code == 403


@pytest.mark.django_db(transaction=True)
def test_update_verified_accion_returns_400():
    tenant = _register('aapi10', 'AAPI10', 'admin@aapi10.com')
    admin = _get_user(tenant, 'admin@aapi10.com')
    resp = _make_user(tenant, 'r@aapi10.com', 'responsable')
    sup = _make_user(tenant, 'sup@aapi10.com', 'supervisor')
    ver = _make_user(tenant, 'ver@aapi10.com', 'verificador')
    issue = _make_issue(tenant, admin, estado='en_analisis')
    connection.set_tenant(tenant)
    accion = AccionService.create_accion(issue, 'correctiva', 'res', resp, '2026-12-31', admin)
    connection.set_tenant(tenant)
    AccionService.transition_state(accion, 'en_proceso', resp)
    AccionService.transition_state(accion, 'cerrado', sup)
    AccionService.transition_state(accion, 'verificado', ver)
    client = _client(tenant, admin)
    connection.set_tenant(tenant)

    r = client.patch(
        f'/api/acciones/{accion.id}/',
        {'resultado_esperado': 'nuevo'},
        format='json',
    )
    assert r.status_code == 400


@pytest.mark.django_db(transaction=True)
def test_update_accion_non_admin_returns_403():
    tenant = _register('aapi11', 'AAPI11', 'admin@aapi11.com')
    admin = _get_user(tenant, 'admin@aapi11.com')
    resp = _make_user(tenant, 'r@aapi11.com', 'responsable')
    issue = _make_issue(tenant, admin, estado='en_analisis')
    connection.set_tenant(tenant)
    accion = AccionService.create_accion(issue, 'correctiva', 'res', resp, '2026-12-31', admin)
    client = _client(tenant, resp)

    r = client.patch(
        f'/api/acciones/{accion.id}/',
        {'resultado_esperado': 'nuevo'},
        format='json',
    )
    assert r.status_code == 403


@pytest.mark.django_db(transaction=True)
def test_tenant_isolation():
    tenant_a = _register('aapita', 'AAPITA', 'admin@aapita.com')
    tenant_b = _register('aapitb', 'AAPITB', 'admin@aapitb.com')
    admin_a = _get_user(tenant_a, 'admin@aapita.com')
    admin_b = _get_user(tenant_b, 'admin@aapitb.com')
    resp_a = _make_user(tenant_a, 'r@aapita.com', 'responsable')
    issue_a = _make_issue(tenant_a, admin_a, estado='en_analisis')
    connection.set_tenant(tenant_a)
    accion = AccionService.create_accion(issue_a, 'correctiva', 'res', resp_a, '2026-12-31', admin_a)

    client_b = _client(tenant_b, admin_b)
    r = client_b.get(f'/api/acciones/{accion.id}/')
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Task 7.3 — Test E2E del flujo completo
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_e2e_full_lifecycle():
    tenant = _register('ae2e1', 'AE2E1', 'admin@ae2e1.com')
    admin = _get_user(tenant, 'admin@ae2e1.com')
    resp = _make_user(tenant, 'r@ae2e1.com', 'responsable')
    sup = _make_user(tenant, 'sup@ae2e1.com', 'supervisor')
    ver = _make_user(tenant, 'ver@ae2e1.com', 'verificador')

    # Admin crea issue y lo mueve a en_analisis
    issue = _make_issue(tenant, admin, estado='en_analisis')

    # Admin crea acción → issue auto-transiciona a acciones_generadas
    client_admin = _client(tenant, admin)
    r = client_admin.post(
        '/api/acciones/',
        _accion_payload(issue.id, resp.id),
        format='json',
    )
    assert r.status_code == 201
    accion_id = r.data['id']
    issue.refresh_from_db()
    assert issue.estado == 'acciones_generadas'

    # Responsable inicia
    client_resp = _client(tenant, resp)
    r = client_resp.post(
        f'/api/acciones/{accion_id}/transition/',
        {'estado': 'en_proceso', 'comentario': 'Trabajando'},
        format='json',
    )
    assert r.status_code == 200
    assert r.data['estado'] == 'en_proceso'

    # Supervisor cierra
    client_sup = _client(tenant, sup)
    r = client_sup.post(
        f'/api/acciones/{accion_id}/transition/',
        {'estado': 'cerrado', 'comentario': 'Revisado'},
        format='json',
    )
    assert r.status_code == 200
    assert r.data['estado'] == 'cerrado'

    # Verificador verifica
    client_ver = _client(tenant, ver)
    r = client_ver.post(
        f'/api/acciones/{accion_id}/transition/',
        {'estado': 'verificado', 'comentario': 'Eficaz'},
        format='json',
    )
    assert r.status_code == 200
    assert r.data['estado'] == 'verificado'

    # Admin verifica historial: 3 entradas
    r = client_admin.get(f'/api/acciones/{accion_id}/historial/')
    assert r.status_code == 200
    assert len(r.data) == 3
