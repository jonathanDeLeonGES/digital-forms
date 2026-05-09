"""
Tests E2E del flujo completo de issues (Tarea 5.3).

Ejercitan los endpoints de la API de extremo a extremo simulando el
recorrido real de un usuario: desde la creación de un issue hasta el
cierre con historial completo, el aislamiento por rol y el ciclo de
Ishikawa.
"""
import pytest
from django.db import connection
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.tenants.models import Plan
from apps.tenants.services import TenantRegistrationService


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
# E2E 1 — Ciclo completo: crear → transicionar hasta cerrado → historial
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_e2e_full_lifecycle_create_transition_to_closed_with_historial():
    """
    Flujo completo:
    1. Admin crea issue (estado=abierto)
    2. Admin transiciona a en_analisis
    3. Admin transiciona a acciones_generadas
    4. Admin transiciona a cerrado
    5. GET detalle muestra historial con las 3 transiciones
    """
    tenant = _register('e2e1', 'E2E Lifecycle', 'admin@e2e1.com')
    admin = _get_user(tenant, 'admin@e2e1.com')
    client = _client(tenant, admin)

    # 1. Crear issue
    r = client.post('/api/issues/', _issue_payload(), format='json')
    assert r.status_code == 201
    issue_id = r.data['id']
    assert r.data['estado'] == 'abierto'

    # 2. abierto → en_analisis
    r = client.post(f'/api/issues/{issue_id}/transition/', {'estado': 'en_analisis', 'comentario': 'Iniciando análisis'}, format='json')
    assert r.status_code == 200
    assert r.data['estado'] == 'en_analisis'

    # 3. en_analisis → acciones_generadas
    r = client.post(f'/api/issues/{issue_id}/transition/', {'estado': 'acciones_generadas', 'comentario': 'Plan de acción definido'}, format='json')
    assert r.status_code == 200
    assert r.data['estado'] == 'acciones_generadas'

    # 4. acciones_generadas → cerrado
    r = client.post(f'/api/issues/{issue_id}/transition/', {'estado': 'cerrado', 'comentario': 'Issue resuelto'}, format='json')
    assert r.status_code == 200
    assert r.data['estado'] == 'cerrado'

    # 5. Verificar historial en detalle (admin ve historial completo)
    r = client.get(f'/api/issues/{issue_id}/')
    assert r.status_code == 200
    assert r.data['estado'] == 'cerrado'
    historial = r.data.get('historial_estados', [])
    assert len(historial) == 3

    estados = [(h['estado_anterior'], h['estado_nuevo']) for h in historial]
    assert ('abierto', 'en_analisis') in estados
    assert ('en_analisis', 'acciones_generadas') in estados
    assert ('acciones_generadas', 'cerrado') in estados


@pytest.mark.django_db(transaction=True)
def test_e2e_closed_issue_cannot_transition_further():
    """Un issue cerrado no puede hacer más transiciones."""
    tenant = _register('e2e1b', 'E2E Closed', 'admin@e2e1b.com')
    admin = _get_user(tenant, 'admin@e2e1b.com')
    client = _client(tenant, admin)

    r = client.post('/api/issues/', _issue_payload(), format='json')
    issue_id = r.data['id']

    for estado in ['en_analisis', 'acciones_generadas', 'cerrado']:
        client.post(f'/api/issues/{issue_id}/transition/', {'estado': estado}, format='json')

    r = client.post(f'/api/issues/{issue_id}/transition/', {'estado': 'abierto'}, format='json')
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# E2E 2 — Aislamiento por rol: responsable no ve issues ajenos
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_e2e_responsable_cannot_see_other_responsable_issues():
    """
    Flujo:
    1. responsable_a crea issue
    2. responsable_b crea issue
    3. GET /api/issues/ como responsable_a → solo su propio issue
    4. GET /api/issues/ como responsable_b → solo su propio issue
    """
    tenant = _register('e2e2', 'E2E Roles', 'admin@e2e2.com')
    resp_a = _make_user(tenant, 'resp_a@e2e2.com', role='responsable')
    resp_b = _make_user(tenant, 'resp_b@e2e2.com', role='responsable')

    client_a = _client(tenant, resp_a)
    client_b = _client(tenant, resp_b)

    # responsable_a crea su issue
    r = client_a.post('/api/issues/', _issue_payload(titulo='Issue de A'), format='json')
    assert r.status_code == 201
    issue_a_id = r.data['id']

    # responsable_b crea su issue
    r = client_b.post('/api/issues/', _issue_payload(titulo='Issue de B'), format='json')
    assert r.status_code == 201
    issue_b_id = r.data['id']

    # responsable_a ve solo su issue
    r = client_a.get('/api/issues/')
    assert r.status_code == 200
    assert r.data['count'] == 1
    assert r.data['results'][0]['id'] == issue_a_id

    # responsable_b ve solo su issue
    r = client_b.get('/api/issues/')
    assert r.status_code == 200
    assert r.data['count'] == 1
    assert r.data['results'][0]['id'] == issue_b_id

    # responsable_a no puede acceder al detalle del issue de B
    r = client_a.get(f'/api/issues/{issue_b_id}/')
    assert r.status_code == 404


@pytest.mark.django_db(transaction=True)
def test_e2e_verificador_sees_all_issues_but_cannot_create():
    """
    Verificador ve todos los issues (de cualquier responsable) pero no puede crear.
    """
    tenant = _register('e2e2b', 'E2E Verif', 'admin@e2e2b.com')
    admin = _get_user(tenant, 'admin@e2e2b.com')
    resp = _make_user(tenant, 'resp@e2e2b.com', role='responsable')
    ver = _make_user(tenant, 'ver@e2e2b.com', role='verificador')

    client_admin = _client(tenant, admin)
    client_resp = _client(tenant, resp)
    client_ver = _client(tenant, ver)

    # Admin y responsable crean un issue cada uno
    client_admin.post('/api/issues/', _issue_payload(titulo='Issue Admin'), format='json')
    client_resp.post('/api/issues/', _issue_payload(titulo='Issue Resp'), format='json')

    # Verificador ve ambos
    r = client_ver.get('/api/issues/')
    assert r.status_code == 200
    assert r.data['count'] == 2

    # Verificador no puede crear
    r = client_ver.post('/api/issues/', _issue_payload(), format='json')
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# E2E 3 — Ciclo Ishikawa: PUT 3 categorías → GET muestra las 6
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_e2e_ishikawa_put_3_categories_get_shows_all_6():
    """
    Flujo:
    1. Crear issue
    2. PUT ishikawa con causas en 3 categorías (metodo, maquina, material)
    3. GET ishikawa devuelve las 6 categorías: 3 con causas, 3 vacías
    """
    tenant = _register('e2e3', 'E2E Ishi', 'admin@e2e3.com')
    admin = _get_user(tenant, 'admin@e2e3.com')
    client = _client(tenant, admin)

    r = client.post('/api/issues/', _issue_payload(), format='json')
    assert r.status_code == 201
    issue_id = r.data['id']

    payload = {
        'causas': [
            {
                'categoria': 'metodo',
                'descripcion': 'Procedimiento obsoleto',
                'subcausas': [{'descripcion': 'Falta de revisión periódica'}],
            },
            {
                'categoria': 'maquina',
                'descripcion': 'Falla mecánica',
                'subcausas': [],
            },
            {
                'categoria': 'material',
                'descripcion': 'Material defectuoso',
                'subcausas': [
                    {'descripcion': 'Proveedor sin certificación'},
                    {'descripcion': 'Sin control de calidad'},
                ],
            },
        ]
    }

    r = client.put(f'/api/issues/{issue_id}/ishikawa/', payload, format='json')
    assert r.status_code == 200

    r = client.get(f'/api/issues/{issue_id}/ishikawa/')
    assert r.status_code == 200

    categorias = r.data['categorias']
    all_six = {'metodo', 'maquina', 'material', 'mano_de_obra', 'medicion', 'medio_ambiente'}
    assert set(categorias.keys()) == all_six

    # Las 3 enviadas tienen causas
    assert len(categorias['metodo']) == 1
    assert categorias['metodo'][0]['descripcion'] == 'Procedimiento obsoleto'
    assert len(categorias['metodo'][0]['subcausas']) == 1

    assert len(categorias['maquina']) == 1
    assert len(categorias['maquina'][0]['subcausas']) == 0

    assert len(categorias['material']) == 1
    assert len(categorias['material'][0]['subcausas']) == 2

    # Las 3 no enviadas están vacías
    assert categorias['mano_de_obra'] == []
    assert categorias['medicion'] == []
    assert categorias['medio_ambiente'] == []


@pytest.mark.django_db(transaction=True)
def test_e2e_ishikawa_second_put_preserves_untouched_categories():
    """
    Un segundo PUT con categorías diferentes preserva las anteriores
    que no se reenvíen.
    """
    tenant = _register('e2e3b', 'E2E Ishi2', 'admin@e2e3b.com')
    admin = _get_user(tenant, 'admin@e2e3b.com')
    client = _client(tenant, admin)

    r = client.post('/api/issues/', _issue_payload(), format='json')
    issue_id = r.data['id']

    # Primer PUT: solo metodo
    client.put(f'/api/issues/{issue_id}/ishikawa/', {
        'causas': [{'categoria': 'metodo', 'descripcion': 'Causa A', 'subcausas': []}]
    }, format='json')

    # Segundo PUT: solo maquina (metodo no se envía → debe conservarse)
    r = client.put(f'/api/issues/{issue_id}/ishikawa/', {
        'causas': [{'categoria': 'maquina', 'descripcion': 'Causa B', 'subcausas': []}]
    }, format='json')
    assert r.status_code == 200

    r = client.get(f'/api/issues/{issue_id}/ishikawa/')
    categorias = r.data['categorias']
    assert len(categorias['metodo']) == 1   # preservada
    assert len(categorias['maquina']) == 1  # nueva
