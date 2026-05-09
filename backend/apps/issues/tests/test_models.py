"""
Tests unitarios para modelos y IssueService (Tareas 5.1).
Usan transaction=True porque crean schemas de tenant reales.
"""
import pytest
from django.db import connection

from apps.tenants.models import Plan
from apps.tenants.services import TenantRegistrationService
from apps.issues.models import Issue, CausaRaiz, SubCausa
from apps.issues.services import IssueService
from apps.issues.exceptions import InvalidTransitionError


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


def _admin(tenant, email):
    from apps.users.models import CustomUser
    connection.set_tenant(tenant)
    return CustomUser.objects.get(email=email)


def _make_issue(tenant, user, **kwargs):
    connection.set_tenant(tenant)
    defaults = dict(
        tipo='incidente', titulo='Test', descripcion='desc',
        fecha_evento='2026-01-01', area='Planta', gravedad='baja',
    )
    defaults.update(kwargs)
    return IssueService.create_issue(**defaults, reportado_por=user)


# ---------------------------------------------------------------------------
# Tarea 5.1 — Tests de modelos y servicio
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_transiciones_validas_cover_all_states():
    estados = {s for s, _ in Issue.ESTADOS}
    assert set(Issue.TRANSICIONES_VALIDAS.keys()) == estados


@pytest.mark.django_db(transaction=True)
def test_queryset_for_user_admin_sees_all():
    tenant = _register('iqadmin', 'IQ Admin', 'admin@iqadmin.com')
    admin = _admin(tenant, 'admin@iqadmin.com')
    connection.set_tenant(tenant)
    from apps.users.models import CustomUser
    resp = CustomUser.objects.create_user(
        email='resp@iqadmin.com', nombre_completo='Resp', role='responsable', password='x'
    )
    _make_issue(tenant, admin)
    _make_issue(tenant, resp)
    connection.set_tenant(tenant)
    assert IssueService.queryset_for_user(admin).count() == 2


@pytest.mark.django_db(transaction=True)
def test_queryset_for_user_responsable_sees_own_only():
    tenant = _register('iqresp', 'IQ Resp', 'admin@iqresp.com')
    admin = _admin(tenant, 'admin@iqresp.com')
    connection.set_tenant(tenant)
    from apps.users.models import CustomUser
    resp = CustomUser.objects.create_user(
        email='resp@iqresp.com', nombre_completo='Resp', role='responsable', password='x'
    )
    _make_issue(tenant, admin)
    _make_issue(tenant, resp)
    connection.set_tenant(tenant)
    assert IssueService.queryset_for_user(resp).count() == 1


@pytest.mark.django_db(transaction=True)
def test_queryset_for_user_verificador_sees_all():
    tenant = _register('iqver', 'IQ Ver', 'admin@iqver.com')
    admin = _admin(tenant, 'admin@iqver.com')
    connection.set_tenant(tenant)
    from apps.users.models import CustomUser
    verif = CustomUser.objects.create_user(
        email='ver@iqver.com', nombre_completo='Ver', role='verificador', password='x'
    )
    _make_issue(tenant, admin)
    _make_issue(tenant, admin)
    connection.set_tenant(tenant)
    assert IssueService.queryset_for_user(verif).count() == 2


@pytest.mark.django_db(transaction=True)
def test_transition_state_valid_creates_historial():
    tenant = _register('iqtrans', 'IQ Trans', 'admin@iqtrans.com')
    admin = _admin(tenant, 'admin@iqtrans.com')
    issue = _make_issue(tenant, admin)
    connection.set_tenant(tenant)
    IssueService.transition_state(issue, 'en_analisis', admin)
    assert issue.estado == 'en_analisis'
    assert issue.historial_estados.count() == 1


@pytest.mark.django_db(transaction=True)
def test_transition_state_invalid_raises():
    tenant = _register('iqinv', 'IQ Inv', 'admin@iqinv.com')
    admin = _admin(tenant, 'admin@iqinv.com')
    issue = _make_issue(tenant, admin)
    connection.set_tenant(tenant)
    with pytest.raises(InvalidTransitionError):
        IssueService.transition_state(issue, 'cerrado', admin)


@pytest.mark.django_db(transaction=True)
def test_upsert_ishikawa_creates_and_preserves():
    tenant = _register('iqishi', 'IQ Ishi', 'admin@iqishi.com')
    admin = _admin(tenant, 'admin@iqishi.com')
    issue = _make_issue(tenant, admin)
    connection.set_tenant(tenant)

    # Primera llamada: crea categoría 'metodo'
    ishi = IssueService.upsert_ishikawa(issue, {
        'metodo': [{'descripcion': 'Procedimiento obsoleto', 'subcausas': [{'descripcion': 'No actualizado'}]}]
    })
    assert ishi.causas.filter(categoria='metodo').count() == 1
    assert ishi.causas.get(categoria='metodo').subcausas.count() == 1

    # Segunda llamada con 'maquina': preserva 'metodo'
    IssueService.upsert_ishikawa(issue, {
        'maquina': [{'descripcion': 'Falla mecánica', 'subcausas': []}]
    })
    ishi.refresh_from_db()
    assert ishi.causas.filter(categoria='metodo').count() == 1
    assert ishi.causas.filter(categoria='maquina').count() == 1


@pytest.mark.django_db(transaction=True)
def test_subcausa_cascade_delete_with_causa():
    tenant = _register('iqcasc', 'IQ Casc', 'admin@iqcasc.com')
    admin = _admin(tenant, 'admin@iqcasc.com')
    issue = _make_issue(tenant, admin)
    connection.set_tenant(tenant)

    ishi = IssueService.upsert_ishikawa(issue, {
        'material': [{'descripcion': 'Causa', 'subcausas': [{'descripcion': 'Sub'}]}]
    })
    causa = ishi.causas.get(categoria='material')
    sub_pk = causa.subcausas.first().pk

    # Eliminar causa → subcausa cae en cascada
    causa.delete()
    assert not SubCausa.objects.filter(pk=sub_pk).exists()
