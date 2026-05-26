"""
Integration tests for PlanService and FileStorageService (Tasks 5.1, 5.2).
Tests run with real PostgreSQL schemas via django-tenants.
"""
import io
import pytest
from django.db import connection

from apps.tenants.models import Plan
from apps.tenants.services import TenantRegistrationService


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _ensure_plans():
    connection.set_schema_to_public()
    Plan.objects.get_or_create(nombre=Plan.TRIAL)
    Plan.objects.get_or_create(nombre=Plan.ENTERPRISE)


def _register(schema, nombre, email):
    connection.set_schema_to_public()
    _ensure_plans()
    return TenantRegistrationService.register(nombre, schema, email, 'Admin123!')


def _get_admin(tenant):
    from apps.users.models import CustomUser
    connection.set_tenant(tenant)
    return CustomUser.objects.filter(role='admin').first()


def _make_user(tenant, email, role):
    from apps.users.models import CustomUser
    connection.set_tenant(tenant)
    return CustomUser.objects.create_user(email=email, nombre_completo='Test', role=role, password='pass!')


def _make_issue(tenant, user):
    from apps.issues.services import IssueService
    connection.set_tenant(tenant)
    issue = IssueService.create_issue(
        tipo='incidente', titulo='Test', descripcion='desc',
        fecha_evento='2026-01-01', area='Planta', gravedad='baja',
        reportado_por=user,
    )
    IssueService.transition_state(issue, 'en_analisis', user)
    return issue


def _make_accion(tenant, issue, responsable, created_by):
    from apps.acciones.services import AccionService
    connection.set_tenant(tenant)
    return AccionService.create_accion(
        issue=issue, tipo='correctiva', resultado_esperado='Res',
        responsable=responsable, fecha_limite='2026-12-31', created_by=created_by,
    )


def _make_plan(tenant, accion, actividades_data):
    from apps.planes.services import PlanService
    connection.set_tenant(tenant)
    return PlanService.create_plan(accion, actividades_data, accion.created_by)


# ---------------------------------------------------------------------------
# Task 2.1 — PlanService CRUD
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_create_plan_success():
    tenant = _register('sv1', 'SV Tenant 1', 'admin@sv1.com')
    admin = _get_admin(tenant)
    resp = _make_user(tenant, 'resp@sv1.com', 'responsable')
    issue = _make_issue(tenant, admin)
    accion = _make_accion(tenant, issue, resp, admin)

    connection.set_tenant(tenant)
    from apps.planes.services import PlanService
    plan = PlanService.create_plan(accion, [
        {'descripcion': 'Act 1', 'responsable': resp, 'fecha_limite': '2026-12-31'},
    ], admin)

    assert plan.pk is not None
    assert plan.actividades.count() == 1
    assert plan.progreso == 0


@pytest.mark.django_db(transaction=True)
def test_create_plan_duplicate_raises():
    tenant = _register('sv2', 'SV Tenant 2', 'admin@sv2.com')
    admin = _get_admin(tenant)
    resp = _make_user(tenant, 'resp@sv2.com', 'responsable')
    issue = _make_issue(tenant, admin)
    accion = _make_accion(tenant, issue, resp, admin)

    connection.set_tenant(tenant)
    from apps.planes.services import PlanService
    from rest_framework.exceptions import ValidationError
    PlanService.create_plan(accion, [{'descripcion': 'A', 'responsable': resp, 'fecha_limite': '2026-12-31'}], admin)

    with pytest.raises(ValidationError):
        PlanService.create_plan(accion, [{'descripcion': 'B', 'responsable': resp, 'fecha_limite': '2026-12-31'}], admin)


@pytest.mark.django_db(transaction=True)
def test_delete_actividad_last_raises():
    tenant = _register('sv3', 'SV Tenant 3', 'admin@sv3.com')
    admin = _get_admin(tenant)
    resp = _make_user(tenant, 'resp@sv3.com', 'responsable')
    issue = _make_issue(tenant, admin)
    accion = _make_accion(tenant, issue, resp, admin)

    connection.set_tenant(tenant)
    from apps.planes.services import PlanService
    from apps.planes.exceptions import LastActividadError
    plan = PlanService.create_plan(accion, [{'descripcion': 'Única', 'responsable': resp, 'fecha_limite': '2026-12-31'}], admin)
    actividad = plan.actividades.first()

    with pytest.raises(LastActividadError):
        PlanService.delete_actividad(actividad, admin)


@pytest.mark.django_db(transaction=True)
def test_update_actividad_responsable_only_descripcion():
    tenant = _register('sv4', 'SV Tenant 4', 'admin@sv4.com')
    admin = _get_admin(tenant)
    resp = _make_user(tenant, 'resp@sv4.com', 'responsable')
    issue = _make_issue(tenant, admin)
    accion = _make_accion(tenant, issue, resp, admin)

    connection.set_tenant(tenant)
    from apps.planes.services import PlanService
    from rest_framework.exceptions import PermissionDenied
    plan = PlanService.create_plan(accion, [{'descripcion': 'Original', 'responsable': resp, 'fecha_limite': '2026-12-31'}], admin)
    actividad = plan.actividades.first()

    with pytest.raises(PermissionDenied):
        PlanService.update_actividad(actividad, {'responsable': admin}, resp)


# ---------------------------------------------------------------------------
# Task 2.2 — State transitions + is_plan_complete
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_transition_actividad_valid():
    tenant = _register('sv5', 'SV Tenant 5', 'admin@sv5.com')
    admin = _get_admin(tenant)
    resp = _make_user(tenant, 'resp@sv5.com', 'responsable')
    issue = _make_issue(tenant, admin)
    accion = _make_accion(tenant, issue, resp, admin)

    connection.set_tenant(tenant)
    from apps.planes.services import PlanService
    plan = PlanService.create_plan(accion, [{'descripcion': 'A', 'responsable': resp, 'fecha_limite': '2026-12-31'}], admin)
    actividad = plan.actividades.first()

    updated = PlanService.transition_actividad(actividad, 'en_proceso', resp)
    assert updated.estado == 'en_proceso'


@pytest.mark.django_db(transaction=True)
def test_transition_actividad_wrong_owner_raises():
    tenant = _register('sv6', 'SV Tenant 6', 'admin@sv6.com')
    admin = _get_admin(tenant)
    resp = _make_user(tenant, 'resp@sv6.com', 'responsable')
    other = _make_user(tenant, 'other@sv6.com', 'responsable')
    issue = _make_issue(tenant, admin)
    accion = _make_accion(tenant, issue, resp, admin)

    connection.set_tenant(tenant)
    from apps.planes.services import PlanService
    from rest_framework.exceptions import PermissionDenied
    plan = PlanService.create_plan(accion, [{'descripcion': 'A', 'responsable': resp, 'fecha_limite': '2026-12-31'}], admin)
    actividad = plan.actividades.first()

    with pytest.raises(PermissionDenied):
        PlanService.transition_actividad(actividad, 'en_proceso', other)


@pytest.mark.django_db(transaction=True)
def test_is_plan_complete_true():
    tenant = _register('sv7', 'SV Tenant 7', 'admin@sv7.com')
    admin = _get_admin(tenant)
    resp = _make_user(tenant, 'resp@sv7.com', 'responsable')
    issue = _make_issue(tenant, admin)
    accion = _make_accion(tenant, issue, resp, admin)

    connection.set_tenant(tenant)
    from apps.planes.services import PlanService
    plan = PlanService.create_plan(accion, [{'descripcion': 'A', 'responsable': resp, 'fecha_limite': '2026-12-31'}], admin)
    actividad = plan.actividades.first()
    PlanService.transition_actividad(actividad, 'completada', admin)

    assert PlanService.is_plan_complete(accion.pk) is True


@pytest.mark.django_db(transaction=True)
def test_is_plan_complete_false_no_plan():
    tenant = _register('sv8', 'SV Tenant 8', 'admin@sv8.com')
    admin = _get_admin(tenant)
    resp = _make_user(tenant, 'resp@sv8.com', 'responsable')
    issue = _make_issue(tenant, admin)
    accion = _make_accion(tenant, issue, resp, admin)

    connection.set_tenant(tenant)
    from apps.planes.services import PlanService
    assert PlanService.is_plan_complete(accion.pk) is False


@pytest.mark.django_db(transaction=True)
def test_is_plan_complete_false_pending():
    tenant = _register('sv9', 'SV Tenant 9', 'admin@sv9.com')
    admin = _get_admin(tenant)
    resp = _make_user(tenant, 'resp@sv9.com', 'responsable')
    issue = _make_issue(tenant, admin)
    accion = _make_accion(tenant, issue, resp, admin)

    connection.set_tenant(tenant)
    from apps.planes.services import PlanService
    PlanService.create_plan(accion, [{'descripcion': 'A', 'responsable': resp, 'fecha_limite': '2026-12-31'}], admin)
    assert PlanService.is_plan_complete(accion.pk) is False


# ---------------------------------------------------------------------------
# Task 4.1 — AccionService blocks cerrado if plan incomplete
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_accion_no_se_puede_cerrar_sin_plan_completo():
    tenant = _register('sv10', 'SV Tenant 10', 'admin@sv10.com')
    admin = _get_admin(tenant)
    resp = _make_user(tenant, 'resp@sv10.com', 'responsable')
    sup = _make_user(tenant, 'sup@sv10.com', 'supervisor')
    issue = _make_issue(tenant, admin)
    accion = _make_accion(tenant, issue, resp, admin)

    connection.set_tenant(tenant)
    from apps.acciones.services import AccionService
    from apps.planes.services import PlanService
    from rest_framework.exceptions import ValidationError

    AccionService.transition_state(accion, 'en_proceso', resp)
    PlanService.create_plan(accion, [{'descripcion': 'A', 'responsable': resp, 'fecha_limite': '2026-12-31'}], admin)

    with pytest.raises(ValidationError):
        AccionService.transition_state(accion, 'cerrado', sup)


@pytest.mark.django_db(transaction=True)
def test_accion_se_puede_cerrar_con_plan_completo():
    tenant = _register('sv11', 'SV Tenant 11', 'admin@sv11.com')
    admin = _get_admin(tenant)
    resp = _make_user(tenant, 'resp@sv11.com', 'responsable')
    sup = _make_user(tenant, 'sup@sv11.com', 'supervisor')
    issue = _make_issue(tenant, admin)
    accion = _make_accion(tenant, issue, resp, admin)

    connection.set_tenant(tenant)
    from apps.acciones.services import AccionService
    from apps.planes.services import PlanService

    AccionService.transition_state(accion, 'en_proceso', resp)
    plan = PlanService.create_plan(accion, [{'descripcion': 'A', 'responsable': resp, 'fecha_limite': '2026-12-31'}], admin)
    actividad = plan.actividades.first()
    PlanService.transition_actividad(actividad, 'completada', admin)

    updated = AccionService.transition_state(accion, 'cerrado', sup)
    assert updated.estado == 'cerrado'


# ---------------------------------------------------------------------------
# Task 5.2 — Tenant isolation
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_plan_aislado_por_tenant():
    tenant_a = _register('iso1a', 'ISO Tenant A', 'admin@iso1a.com')
    tenant_b = _register('iso1b', 'ISO Tenant B', 'admin@iso1b.com')

    admin_a = _get_admin(tenant_a)
    resp_a = _make_user(tenant_a, 'resp@iso1a.com', 'responsable')
    issue_a = _make_issue(tenant_a, admin_a)
    accion_a = _make_accion(tenant_a, issue_a, resp_a, admin_a)

    connection.set_tenant(tenant_a)
    from apps.planes.services import PlanService
    PlanService.create_plan(accion_a, [{'descripcion': 'A', 'responsable': resp_a, 'fecha_limite': '2026-12-31'}], admin_a)

    connection.set_tenant(tenant_b)
    from apps.planes.models import PlanTrabajo
    assert not PlanTrabajo.objects.filter(accion=accion_a).exists()


@pytest.mark.django_db(transaction=True)
def test_queryset_responsable_solo_ve_sus_planes():
    tenant = _register('sv12', 'SV Tenant 12', 'admin@sv12.com')
    admin = _get_admin(tenant)
    resp1 = _make_user(tenant, 'resp1@sv12.com', 'responsable')
    resp2 = _make_user(tenant, 'resp2@sv12.com', 'responsable')

    issue = _make_issue(tenant, admin)
    accion1 = _make_accion(tenant, issue, resp1, admin)

    issue2 = _make_issue(tenant, admin)
    accion2 = _make_accion(tenant, issue2, resp2, admin)

    connection.set_tenant(tenant)
    from apps.planes.services import PlanService
    PlanService.create_plan(accion1, [{'descripcion': 'A', 'responsable': resp1, 'fecha_limite': '2026-12-31'}], admin)
    PlanService.create_plan(accion2, [{'descripcion': 'B', 'responsable': resp2, 'fecha_limite': '2026-12-31'}], admin)

    qs_resp1 = PlanService.queryset_for_user(resp1)
    assert qs_resp1.count() == 1
    assert qs_resp1.first().accion.responsable == resp1
