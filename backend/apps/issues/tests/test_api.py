"""
Tests de integración para endpoints de issues (Tarea 5.2).
"""
import pytest
from django.db import connection
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.tenants.models import Plan
from apps.tenants.services import TenantRegistrationService
from apps.issues.services import IssueService


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


def _make_user(tenant, email, role='responsable'):
    from apps.users.models import CustomUser
    connection.set_tenant(tenant)
    return CustomUser.objects.create_user(
        email=email, nombre_completo='User', role=role, password='pass123!'
    )


def _client(tenant, user=None):
    client = APIClient()
    client.defaults['HTTP_HOST'] = f'{tenant.schema_name}.sgca.com'
    if user:
        connection.set_tenant(tenant)
        token = str(RefreshToken.for_user(user).access_token)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    return client


def _issue_payload(**overrides):
    base = {
        'tipo': 'incidente',
        'titulo': 'Accidente en planta',
        'descripcion': 'Descripción del accidente',
        'fecha_evento': '2026-01-15',
        'area': 'Producción',
        'gravedad': 'alta',
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Tarea 5.2 — Tests de API
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_create_issue_returns_201():
    tenant = _register('iaapi', 'IA API', 'admin@iaapi.com')
    admin = _get_user(tenant, 'admin@iaapi.com')
    client = _client(tenant, admin)

    resp = client.post('/api/issues/', _issue_payload(), format='json')
    assert resp.status_code == 201
    assert resp.data['titulo'] == 'Accidente en planta'
    assert resp.data['estado'] == 'abierto'


@pytest.mark.django_db(transaction=True)
def test_create_issue_missing_field_returns_400():
    tenant = _register('iabad', 'IA Bad', 'admin@iabad.com')
    admin = _get_user(tenant, 'admin@iabad.com')
    client = _client(tenant, admin)

    resp = client.post('/api/issues/', {'titulo': 'Solo titulo'}, format='json')
    assert resp.status_code == 400


@pytest.mark.django_db(transaction=True)
def test_list_issues_filter_by_estado():
    tenant = _register('iafilt', 'IA Filt', 'admin@iafilt.com')
    admin = _get_user(tenant, 'admin@iafilt.com')
    connection.set_tenant(tenant)
    IssueService.create_issue(**{k: v for k, v in _issue_payload().items()}, reportado_por=admin)
    issue2 = IssueService.create_issue(**{k: v for k, v in _issue_payload(titulo='Otro').items()}, reportado_por=admin)
    IssueService.transition_state(issue2, 'en_analisis', admin)

    client = _client(tenant, admin)
    resp = client.get('/api/issues/?estado=abierto')
    assert resp.status_code == 200
    assert resp.data['count'] == 1


@pytest.mark.django_db(transaction=True)
def test_list_issues_filter_by_tipo():
    tenant = _register('iafilt2', 'IA Filt2', 'admin@iafilt2.com')
    admin = _get_user(tenant, 'admin@iafilt2.com')
    connection.set_tenant(tenant)
    IssueService.create_issue(**{k: v for k, v in _issue_payload(tipo='incidente').items()}, reportado_por=admin)
    IssueService.create_issue(**{k: v for k, v in _issue_payload(tipo='casi_incidente').items()}, reportado_por=admin)

    client = _client(tenant, admin)
    resp = client.get('/api/issues/?tipo=incidente')
    assert resp.status_code == 200
    assert resp.data['count'] == 1


@pytest.mark.django_db(transaction=True)
def test_responsable_sees_only_own_issues():
    tenant = _register('iaresp', 'IA Resp', 'admin@iaresp.com')
    admin = _get_user(tenant, 'admin@iaresp.com')
    resp_user = _make_user(tenant, 'resp@iaresp.com', role='responsable')
    connection.set_tenant(tenant)
    IssueService.create_issue(**{k: v for k, v in _issue_payload().items()}, reportado_por=admin)
    IssueService.create_issue(**{k: v for k, v in _issue_payload().items()}, reportado_por=resp_user)

    client = _client(tenant, resp_user)
    r = client.get('/api/issues/')
    assert r.status_code == 200
    assert r.data['count'] == 1


@pytest.mark.django_db(transaction=True)
def test_verificador_cannot_create_issue():
    tenant = _register('iaver', 'IA Ver', 'admin@iaver.com')
    ver = _make_user(tenant, 'ver@iaver.com', role='verificador')
    client = _client(tenant, ver)

    resp = client.post('/api/issues/', _issue_payload(), format='json')
    assert resp.status_code == 403


@pytest.mark.django_db(transaction=True)
def test_verificador_can_list_issues():
    tenant = _register('iaver2', 'IA Ver2', 'admin@iaver2.com')
    admin = _get_user(tenant, 'admin@iaver2.com')
    ver = _make_user(tenant, 'ver@iaver2.com', role='verificador')
    connection.set_tenant(tenant)
    IssueService.create_issue(**{k: v for k, v in _issue_payload().items()}, reportado_por=admin)

    client = _client(tenant, ver)
    resp = client.get('/api/issues/')
    assert resp.status_code == 200
    assert resp.data['count'] == 1


@pytest.mark.django_db(transaction=True)
def test_transition_valid_returns_200_with_historial():
    tenant = _register('iatrans', 'IA Trans', 'admin@iatrans.com')
    admin = _get_user(tenant, 'admin@iatrans.com')
    connection.set_tenant(tenant)
    issue = IssueService.create_issue(**{k: v for k, v in _issue_payload().items()}, reportado_por=admin)

    client = _client(tenant, admin)
    resp = client.post(f'/api/issues/{issue.pk}/transition/', {'estado': 'en_analisis'}, format='json')
    assert resp.status_code == 200
    assert resp.data['estado'] == 'en_analisis'


@pytest.mark.django_db(transaction=True)
def test_transition_invalid_returns_400():
    tenant = _register('iatrinv', 'IA TrInv', 'admin@iatrinv.com')
    admin = _get_user(tenant, 'admin@iatrinv.com')
    connection.set_tenant(tenant)
    issue = IssueService.create_issue(**{k: v for k, v in _issue_payload().items()}, reportado_por=admin)

    client = _client(tenant, admin)
    resp = client.post(f'/api/issues/{issue.pk}/transition/', {'estado': 'cerrado'}, format='json')
    assert resp.status_code == 400


@pytest.mark.django_db(transaction=True)
def test_ishikawa_get_404_when_not_exists():
    tenant = _register('iagishi', 'IA GIshi', 'admin@iagishi.com')
    admin = _get_user(tenant, 'admin@iagishi.com')
    connection.set_tenant(tenant)
    issue = IssueService.create_issue(**{k: v for k, v in _issue_payload().items()}, reportado_por=admin)

    client = _client(tenant, admin)
    resp = client.get(f'/api/issues/{issue.pk}/ishikawa/')
    assert resp.status_code == 404


@pytest.mark.django_db(transaction=True)
def test_ishikawa_put_creates_and_returns_all_categories():
    tenant = _register('iapishi', 'IA PIshi', 'admin@iapishi.com')
    admin = _get_user(tenant, 'admin@iapishi.com')
    connection.set_tenant(tenant)
    issue = IssueService.create_issue(**{k: v for k, v in _issue_payload().items()}, reportado_por=admin)

    client = _client(tenant, admin)
    payload = {
        'causas': [
            {'categoria': 'metodo', 'descripcion': 'Proc obsoleto', 'subcausas': [{'descripcion': 'Sin rev.'}]},
            {'categoria': 'maquina', 'descripcion': 'Falla', 'subcausas': []},
        ]
    }
    resp = client.put(f'/api/issues/{issue.pk}/ishikawa/', payload, format='json')
    assert resp.status_code == 200
    assert 'categorias' in resp.data
    assert len(resp.data['categorias']['metodo']) == 1
    assert len(resp.data['categorias']['maquina']) == 1
    assert len(resp.data['categorias']['material']) == 0


@pytest.mark.django_db(transaction=True)
def test_tenant_isolation_issue_not_visible_from_other_tenant():
    tenant_a = _register('iaiso1', 'IA Iso A', 'admin@iaiso1.com')
    tenant_b = _register('iaiso2', 'IA Iso B', 'admin@iaiso2.com')
    admin_a = _get_user(tenant_a, 'admin@iaiso1.com')
    admin_b = _get_user(tenant_b, 'admin@iaiso2.com')

    connection.set_tenant(tenant_a)
    issue = IssueService.create_issue(**{k: v for k, v in _issue_payload().items()}, reportado_por=admin_a)

    client_b = _client(tenant_b, admin_b)
    resp = client_b.get(f'/api/issues/{issue.pk}/')
    assert resp.status_code == 404


@pytest.mark.django_db(transaction=True)
def test_unauthenticated_returns_401():
    tenant = _register('iaauth', 'IA Auth', 'admin@iaauth.com')
    client = _client(tenant)
    resp = client.get('/api/issues/')
    assert resp.status_code == 401
