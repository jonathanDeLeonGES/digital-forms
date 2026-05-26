"""
Tests unitarios para modelos de planes-trabajo (Task 1.1).
TDD RED phase: escribe tests antes de implementar los modelos.
Usan transaction=True porque crean schemas de tenant reales.
"""
import pytest
from django.db import connection

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


def _make_user(tenant, email, role):
    from apps.users.models import CustomUser
    connection.set_tenant(tenant)
    return CustomUser.objects.create_user(
        email=email, nombre_completo='User', role=role, password='pass!'
    )


def _make_issue(tenant, user):
    from apps.issues.services import IssueService
    connection.set_tenant(tenant)
    issue = IssueService.create_issue(
        tipo='incidente', titulo='Test Issue', descripcion='desc',
        fecha_evento='2026-01-01', area='Planta', gravedad='baja',
        reportado_por=user,
    )
    # Advance to en_analisis so an Accion can be created
    IssueService.transition_state(issue, 'en_analisis', user)
    return issue


def _make_accion(tenant, issue, responsable, created_by):
    from apps.acciones.services import AccionService
    connection.set_tenant(tenant)
    return AccionService.create_accion(
        issue=issue,
        tipo='correctiva',
        resultado_esperado='Resultado esperado de prueba',
        responsable=responsable,
        fecha_limite='2026-12-31',
        created_by=created_by,
    )


def _make_plan(tenant, accion):
    """Creates a PlanTrabajo for the given accion within the tenant context."""
    from apps.planes.models import PlanTrabajo
    connection.set_tenant(tenant)
    return PlanTrabajo.objects.create(accion=accion)


def _make_actividad(tenant, plan, responsable, estado='pendiente'):
    """Creates an Actividad for the given plan within the tenant context."""
    from apps.planes.models import Actividad
    connection.set_tenant(tenant)
    return Actividad.objects.create(
        plan=plan,
        descripcion='Actividad de prueba',
        responsable=responsable,
        fecha_limite='2026-12-31',
        estado=estado,
    )


# ---------------------------------------------------------------------------
# Tests de PlanTrabajo.progreso property
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_progreso_sin_actividades_es_cero():
    """PlanTrabajo sin actividades debe retornar progreso 0."""
    tenant = _register('pt1', 'PT Tenant 1', 'admin@pt1.com')
    admin = _get_user(tenant, 'admin@pt1.com')
    resp = _make_user(tenant, 'resp@pt1.com', 'responsable')
    issue = _make_issue(tenant, admin)
    connection.set_tenant(tenant)
    accion = _make_accion(tenant, issue, resp, admin)
    plan = _make_plan(tenant, accion)

    assert plan.progreso == 0


@pytest.mark.django_db(transaction=True)
def test_progreso_parcial_una_de_dos_completadas():
    """PlanTrabajo con 1 de 2 actividades completadas debe retornar progreso 50."""
    tenant = _register('pt2', 'PT Tenant 2', 'admin@pt2.com')
    admin = _get_user(tenant, 'admin@pt2.com')
    resp = _make_user(tenant, 'resp@pt2.com', 'responsable')
    issue = _make_issue(tenant, admin)
    connection.set_tenant(tenant)
    accion = _make_accion(tenant, issue, resp, admin)
    plan = _make_plan(tenant, accion)

    connection.set_tenant(tenant)
    _make_actividad(tenant, plan, resp, estado='completada')
    _make_actividad(tenant, plan, resp, estado='pendiente')

    plan.refresh_from_db()
    assert plan.progreso == 50


@pytest.mark.django_db(transaction=True)
def test_progreso_todas_completadas_es_cien():
    """PlanTrabajo con todas las actividades completadas debe retornar progreso 100."""
    tenant = _register('pt3', 'PT Tenant 3', 'admin@pt3.com')
    admin = _get_user(tenant, 'admin@pt3.com')
    resp = _make_user(tenant, 'resp@pt3.com', 'responsable')
    issue = _make_issue(tenant, admin)
    connection.set_tenant(tenant)
    accion = _make_accion(tenant, issue, resp, admin)
    plan = _make_plan(tenant, accion)

    connection.set_tenant(tenant)
    _make_actividad(tenant, plan, resp, estado='completada')
    _make_actividad(tenant, plan, resp, estado='completada')
    _make_actividad(tenant, plan, resp, estado='completada')

    plan.refresh_from_db()
    assert plan.progreso == 100


@pytest.mark.django_db(transaction=True)
def test_progreso_redondeo_correcto():
    """PlanTrabajo con 1 de 3 completadas: round(33.33) = 33."""
    tenant = _register('pt4', 'PT Tenant 4', 'admin@pt4.com')
    admin = _get_user(tenant, 'admin@pt4.com')
    resp = _make_user(tenant, 'resp@pt4.com', 'responsable')
    issue = _make_issue(tenant, admin)
    connection.set_tenant(tenant)
    accion = _make_accion(tenant, issue, resp, admin)
    plan = _make_plan(tenant, accion)

    connection.set_tenant(tenant)
    _make_actividad(tenant, plan, resp, estado='completada')
    _make_actividad(tenant, plan, resp, estado='pendiente')
    _make_actividad(tenant, plan, resp, estado='en_proceso')

    plan.refresh_from_db()
    assert plan.progreso == 33


# ---------------------------------------------------------------------------
# Tests de invariantes del modelo PlanTrabajo
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_plan_trabajo_uno_a_uno_con_accion():
    """Debe existir exactamente un PlanTrabajo por Accion (OneToOneField)."""
    from apps.planes.models import PlanTrabajo
    from django.db import IntegrityError

    tenant = _register('pt5', 'PT Tenant 5', 'admin@pt5.com')
    admin = _get_user(tenant, 'admin@pt5.com')
    resp = _make_user(tenant, 'resp@pt5.com', 'responsable')
    issue = _make_issue(tenant, admin)
    connection.set_tenant(tenant)
    accion = _make_accion(tenant, issue, resp, admin)
    _make_plan(tenant, accion)

    connection.set_tenant(tenant)
    with pytest.raises(IntegrityError):
        PlanTrabajo.objects.create(accion=accion)


# ---------------------------------------------------------------------------
# Tests de invariantes del modelo Actividad
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_actividad_estado_default_pendiente():
    """Actividad recién creada debe tener estado 'pendiente' por defecto."""
    tenant = _register('pt6', 'PT Tenant 6', 'admin@pt6.com')
    admin = _get_user(tenant, 'admin@pt6.com')
    resp = _make_user(tenant, 'resp@pt6.com', 'responsable')
    issue = _make_issue(tenant, admin)
    connection.set_tenant(tenant)
    accion = _make_accion(tenant, issue, resp, admin)
    plan = _make_plan(tenant, accion)

    connection.set_tenant(tenant)
    actividad = _make_actividad(tenant, plan, resp)
    assert actividad.estado == 'pendiente'


@pytest.mark.django_db(transaction=True)
def test_actividad_choices_validos():
    """Los choices de estado de Actividad deben ser los definidos en el spec."""
    from apps.planes.models import Actividad
    estados = {choice[0] for choice in Actividad.ESTADOS}
    assert estados == {'pendiente', 'en_proceso', 'completada'}


@pytest.mark.django_db(transaction=True)
def test_actividad_cascade_delete_with_plan():
    """Al eliminar PlanTrabajo, sus Actividades deben eliminarse en cascada."""
    from apps.planes.models import Actividad

    tenant = _register('pt7', 'PT Tenant 7', 'admin@pt7.com')
    admin = _get_user(tenant, 'admin@pt7.com')
    resp = _make_user(tenant, 'resp@pt7.com', 'responsable')
    issue = _make_issue(tenant, admin)
    connection.set_tenant(tenant)
    accion = _make_accion(tenant, issue, resp, admin)
    plan = _make_plan(tenant, accion)

    connection.set_tenant(tenant)
    act = _make_actividad(tenant, plan, resp)
    act_pk = act.pk

    connection.set_tenant(tenant)
    plan.delete()
    assert not Actividad.objects.filter(pk=act_pk).exists()


# ---------------------------------------------------------------------------
# Tests de invariantes del modelo Evidencia
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_evidencia_tipos_permitidos_definidos():
    """Evidencia debe tener la constante TIPOS_PERMITIDOS con los tipos correctos."""
    from apps.planes.models import Evidencia
    assert 'application/pdf' in Evidencia.TIPOS_PERMITIDOS
    assert 'image/jpeg' in Evidencia.TIPOS_PERMITIDOS
    assert 'image/png' in Evidencia.TIPOS_PERMITIDOS
    assert 'video/mp4' in Evidencia.TIPOS_PERMITIDOS


@pytest.mark.django_db(transaction=True)
def test_evidencia_max_size_bytes():
    """Evidencia debe tener MAX_SIZE_BYTES de 50 MB."""
    from apps.planes.models import Evidencia
    assert Evidencia.MAX_SIZE_BYTES == 50 * 1024 * 1024


@pytest.mark.django_db(transaction=True)
def test_evidencia_cascade_delete_with_actividad():
    """Al eliminar Actividad, sus Evidencias deben eliminarse en cascada."""
    from apps.planes.models import Actividad, Evidencia

    tenant = _register('pt8', 'PT Tenant 8', 'admin@pt8.com')
    admin = _get_user(tenant, 'admin@pt8.com')
    resp = _make_user(tenant, 'resp@pt8.com', 'responsable')
    issue = _make_issue(tenant, admin)
    connection.set_tenant(tenant)
    accion = _make_accion(tenant, issue, resp, admin)
    plan = _make_plan(tenant, accion)

    connection.set_tenant(tenant)
    act = _make_actividad(tenant, plan, resp)

    connection.set_tenant(tenant)
    evidencia = Evidencia.objects.create(
        actividad=act,
        s3_path='tenant1/evidencias/1/1/uuid_file.pdf',
        nombre_original='file.pdf',
        content_type='application/pdf',
        tamaño_bytes=1024,
        uploaded_by=resp,
    )
    ev_pk = evidencia.pk

    connection.set_tenant(tenant)
    act.delete()
    assert not Evidencia.objects.filter(pk=ev_pk).exists()
