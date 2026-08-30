"""Tests unitarios del servicio AccionService (Task 7.1)."""
import pytest
from django.db import connection

from apps.tenants.models import Plan
from apps.tenants.services import TenantRegistrationService
from apps.issues.services import IssueService
from apps.acciones.models import Accion
from apps.acciones.services import AccionService
from apps.acciones.exceptions import InvalidTransitionError
from apps.acciones.signals import accion_estado_cambiado


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


def _make_accion(tenant, issue, responsable, created_by):
    connection.set_tenant(tenant)
    return AccionService.create_accion(
        issue=issue,
        tipo='correctiva',
        resultado_esperado='Resultado esperado de prueba',
        responsable=responsable,
        fecha_limite='2026-12-31',
        created_by=created_by,
    )


def _completar_plan(accion, responsable, admin):
    """Crea un plan de trabajo con una actividad completada.

    Desde la Wave 3 (planes de trabajo) cerrar una acción exige que su plan
    esté completo, por lo que los tests que cierran acciones deben preparar
    un plan completado.
    """
    from apps.planes.services import PlanService
    plan = PlanService.create_plan(
        accion,
        [{'descripcion': 'Actividad de prueba', 'responsable': responsable,
          'fecha_limite': '2027-12-31'}],
        admin,
    )
    for act in plan.actividades.all():
        PlanService.transition_actividad(act, 'completada', admin)
    return plan



# ---------------------------------------------------------------------------
# Task 7.1 — Unit tests del servicio
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_transiciones_validas_cover_all_states():
    estados = {s for s, _ in Accion.ESTADOS}
    assert set(Accion.TRANSICIONES_VALIDAS.keys()) == estados


@pytest.mark.django_db(transaction=True)
def test_create_accion_estado_inicial_abierto():
    tenant = _register('asvc1', 'SVC1', 'admin@asvc1.com')
    admin = _get_user(tenant, 'admin@asvc1.com')
    responsable = _make_user(tenant, 'resp@asvc1.com', 'responsable')
    issue = _make_issue(tenant, admin, estado='en_analisis')
    accion = _make_accion(tenant, issue, responsable, admin)
    assert accion.estado == 'abierto'
    assert accion.created_by_id == admin.pk


@pytest.mark.django_db(transaction=True)
def test_create_accion_responsable_fuera_tenant_raises():
    tenant = _register('asvc2', 'SVC2', 'admin@asvc2.com')
    tenant2 = _register('asvc2b', 'SVC2B', 'admin@asvc2b.com')
    admin = _get_user(tenant, 'admin@asvc2.com')
    admin2 = _get_user(tenant2, 'admin@asvc2b.com')
    issue = _make_issue(tenant, admin)

    connection.set_tenant(tenant)
    from rest_framework.exceptions import ValidationError
    with pytest.raises(ValidationError):
        AccionService.create_accion(
            issue=issue,
            tipo='correctiva',
            resultado_esperado='res',
            responsable=admin2,
            fecha_limite='2026-12-31',
            created_by=admin,
        )


@pytest.mark.django_db(transaction=True)
def test_queryset_for_user_admin_sees_all():
    tenant = _register('asvcq1', 'SVCQ1', 'admin@asvcq1.com')
    admin = _get_user(tenant, 'admin@asvcq1.com')
    resp1 = _make_user(tenant, 'r1@asvcq1.com', 'responsable')
    resp2 = _make_user(tenant, 'r2@asvcq1.com', 'responsable')
    issue = _make_issue(tenant, admin, estado='en_analisis')
    connection.set_tenant(tenant)
    _make_accion(tenant, issue, resp1, admin)
    _make_accion(tenant, issue, resp2, admin)
    connection.set_tenant(tenant)
    assert AccionService.queryset_for_user(admin).count() == 2


@pytest.mark.django_db(transaction=True)
def test_queryset_for_user_responsable_sees_only_own():
    tenant = _register('asvcq2', 'SVCQ2', 'admin@asvcq2.com')
    admin = _get_user(tenant, 'admin@asvcq2.com')
    resp1 = _make_user(tenant, 'r1@asvcq2.com', 'responsable')
    resp2 = _make_user(tenant, 'r2@asvcq2.com', 'responsable')
    issue = _make_issue(tenant, admin, estado='en_analisis')
    connection.set_tenant(tenant)
    _make_accion(tenant, issue, resp1, admin)
    _make_accion(tenant, issue, resp2, admin)
    connection.set_tenant(tenant)
    assert AccionService.queryset_for_user(resp1).count() == 1
    assert AccionService.queryset_for_user(resp2).count() == 1


@pytest.mark.django_db(transaction=True)
def test_queryset_for_user_supervisor_sees_all():
    tenant = _register('asvcq3', 'SVCQ3', 'admin@asvcq3.com')
    admin = _get_user(tenant, 'admin@asvcq3.com')
    sup = _make_user(tenant, 'sup@asvcq3.com', 'supervisor')
    resp = _make_user(tenant, 'r@asvcq3.com', 'responsable')
    issue = _make_issue(tenant, admin, estado='en_analisis')
    connection.set_tenant(tenant)
    _make_accion(tenant, issue, resp, admin)
    _make_accion(tenant, issue, resp, admin)
    connection.set_tenant(tenant)
    assert AccionService.queryset_for_user(sup).count() == 2


@pytest.mark.django_db(transaction=True)
def test_validate_transition_admin_bypasses_all():
    tenant = _register('asvct1', 'SVCT1', 'admin@asvct1.com')
    admin = _get_user(tenant, 'admin@asvct1.com')
    resp = _make_user(tenant, 'r@asvct1.com', 'responsable')
    issue = _make_issue(tenant, admin, estado='en_analisis')
    connection.set_tenant(tenant)
    accion = _make_accion(tenant, issue, resp, admin)
    connection.set_tenant(tenant)
    # Admin can do abierto → en_proceso
    AccionService.transition_state(accion, 'en_proceso', admin)
    assert accion.estado == 'en_proceso'


@pytest.mark.django_db(transaction=True)
def test_validate_transition_responsable_can_start_own():
    tenant = _register('asvct2', 'SVCT2', 'admin@asvct2.com')
    admin = _get_user(tenant, 'admin@asvct2.com')
    resp = _make_user(tenant, 'r@asvct2.com', 'responsable')
    issue = _make_issue(tenant, admin, estado='en_analisis')
    connection.set_tenant(tenant)
    accion = _make_accion(tenant, issue, resp, admin)
    connection.set_tenant(tenant)
    AccionService.transition_state(accion, 'en_proceso', resp)
    assert accion.estado == 'en_proceso'


@pytest.mark.django_db(transaction=True)
def test_validate_transition_other_responsable_cannot_start():
    from rest_framework.exceptions import PermissionDenied
    tenant = _register('asvct3', 'SVCT3', 'admin@asvct3.com')
    admin = _get_user(tenant, 'admin@asvct3.com')
    resp1 = _make_user(tenant, 'r1@asvct3.com', 'responsable')
    resp2 = _make_user(tenant, 'r2@asvct3.com', 'responsable')
    issue = _make_issue(tenant, admin, estado='en_analisis')
    connection.set_tenant(tenant)
    accion = _make_accion(tenant, issue, resp1, admin)
    connection.set_tenant(tenant)
    with pytest.raises(PermissionDenied):
        AccionService.transition_state(accion, 'en_proceso', resp2)


@pytest.mark.django_db(transaction=True)
def test_validate_transition_supervisor_can_close():
    tenant = _register('asvct4', 'SVCT4', 'admin@asvct4.com')
    admin = _get_user(tenant, 'admin@asvct4.com')
    resp = _make_user(tenant, 'r@asvct4.com', 'responsable')
    sup = _make_user(tenant, 'sup@asvct4.com', 'supervisor')
    issue = _make_issue(tenant, admin, estado='en_analisis')
    connection.set_tenant(tenant)
    accion = _make_accion(tenant, issue, resp, admin)
    connection.set_tenant(tenant)
    AccionService.transition_state(accion, 'en_proceso', resp)
    _completar_plan(accion, resp, admin)
    AccionService.transition_state(accion, 'cerrado', sup)
    assert accion.estado == 'cerrado'


@pytest.mark.django_db(transaction=True)
def test_validate_transition_verificador_can_verify():
    tenant = _register('asvct5', 'SVCT5', 'admin@asvct5.com')
    admin = _get_user(tenant, 'admin@asvct5.com')
    resp = _make_user(tenant, 'r@asvct5.com', 'responsable')
    sup = _make_user(tenant, 'sup@asvct5.com', 'supervisor')
    ver = _make_user(tenant, 'ver@asvct5.com', 'verificador')
    issue = _make_issue(tenant, admin, estado='en_analisis')
    connection.set_tenant(tenant)
    accion = _make_accion(tenant, issue, resp, admin)
    connection.set_tenant(tenant)
    AccionService.transition_state(accion, 'en_proceso', resp)
    _completar_plan(accion, resp, admin)
    AccionService.transition_state(accion, 'cerrado', sup)
    AccionService.transition_state(accion, 'verificado', ver)
    assert accion.estado == 'verificado'


@pytest.mark.django_db(transaction=True)
def test_validate_transition_invalid_raises():
    tenant = _register('asvct6', 'SVCT6', 'admin@asvct6.com')
    admin = _get_user(tenant, 'admin@asvct6.com')
    resp = _make_user(tenant, 'r@asvct6.com', 'responsable')
    issue = _make_issue(tenant, admin, estado='en_analisis')
    connection.set_tenant(tenant)
    accion = _make_accion(tenant, issue, resp, admin)
    connection.set_tenant(tenant)
    with pytest.raises(InvalidTransitionError):
        AccionService.transition_state(accion, 'verificado', admin)


@pytest.mark.django_db(transaction=True)
def test_transition_creates_historial():
    tenant = _register('asvct7', 'SVCT7', 'admin@asvct7.com')
    admin = _get_user(tenant, 'admin@asvct7.com')
    resp = _make_user(tenant, 'r@asvct7.com', 'responsable')
    issue = _make_issue(tenant, admin, estado='en_analisis')
    connection.set_tenant(tenant)
    accion = _make_accion(tenant, issue, resp, admin)
    connection.set_tenant(tenant)
    AccionService.transition_state(accion, 'en_proceso', resp, comentario='Empezando')
    connection.set_tenant(tenant)
    assert accion.historial_estados.count() == 1
    h = accion.historial_estados.first()
    assert h.estado_anterior == 'abierto'
    assert h.estado_nuevo == 'en_proceso'
    assert h.comentario == 'Empezando'


@pytest.mark.django_db(transaction=True)
def test_signal_emitted_on_transition():
    tenant = _register('asvcs1', 'SVCS1', 'admin@asvcs1.com')
    admin = _get_user(tenant, 'admin@asvcs1.com')
    resp = _make_user(tenant, 'r@asvcs1.com', 'responsable')
    issue = _make_issue(tenant, admin, estado='en_analisis')
    connection.set_tenant(tenant)
    accion = _make_accion(tenant, issue, resp, admin)
    connection.set_tenant(tenant)

    received = []

    def handler(sender, **kwargs):
        received.append(kwargs)

    accion_estado_cambiado.connect(handler)
    try:
        AccionService.transition_state(accion, 'en_proceso', resp)
        assert len(received) == 1
        assert received[0]['estado_anterior'] == 'abierto'
        assert received[0]['estado_nuevo'] == 'en_proceso'
        assert received[0]['usuario'] == resp
    finally:
        accion_estado_cambiado.disconnect(handler)


@pytest.mark.django_db(transaction=True)
def test_trigger_issue_transition_on_first_accion():
    tenant = _register('asvci1', 'SVCI1', 'admin@asvci1.com')
    admin = _get_user(tenant, 'admin@asvci1.com')
    resp = _make_user(tenant, 'r@asvci1.com', 'responsable')
    issue = _make_issue(tenant, admin, estado='en_analisis')
    connection.set_tenant(tenant)
    _make_accion(tenant, issue, resp, admin)
    issue.refresh_from_db()
    assert issue.estado == 'acciones_generadas'


@pytest.mark.django_db(transaction=True)
def test_create_accion_issue_estado_invalido_raises():
    from rest_framework.exceptions import ValidationError
    tenant = _register('asvcv1', 'SVCV1', 'admin@asvcv1.com')
    admin = _get_user(tenant, 'admin@asvcv1.com')
    resp = _make_user(tenant, 'r@asvcv1.com', 'responsable')
    issue = _make_issue(tenant, admin)  # estado='abierto'
    connection.set_tenant(tenant)
    with pytest.raises(ValidationError):
        AccionService.create_accion(
            issue=issue, tipo='correctiva', resultado_esperado='res',
            responsable=resp, fecha_limite='2026-12-31', created_by=admin,
        )


@pytest.mark.django_db(transaction=True)
def test_trigger_issue_no_transition_if_not_en_analisis():
    tenant = _register('asvci2', 'SVCI2', 'admin@asvci2.com')
    admin = _get_user(tenant, 'admin@asvci2.com')
    resp = _make_user(tenant, 'r@asvci2.com', 'responsable')
    # issue ya en acciones_generadas — crear acción no dispara otra transición
    issue = _make_issue(tenant, admin, estado='acciones_generadas')
    connection.set_tenant(tenant)
    _make_accion(tenant, issue, resp, admin)
    issue.refresh_from_db()
    assert issue.estado == 'acciones_generadas'


@pytest.mark.django_db(transaction=True)
def test_trigger_issue_no_transition_on_second_accion():
    tenant = _register('asvci3', 'SVCI3', 'admin@asvci3.com')
    admin = _get_user(tenant, 'admin@asvci3.com')
    resp = _make_user(tenant, 'r@asvci3.com', 'responsable')
    issue = _make_issue(tenant, admin, estado='en_analisis')
    connection.set_tenant(tenant)
    _make_accion(tenant, issue, resp, admin)
    issue.refresh_from_db()
    assert issue.estado == 'acciones_generadas'
    # segunda acción: issue ya no está en 'en_analisis'
    _make_accion(tenant, issue, resp, admin)
    issue.refresh_from_db()
    assert issue.estado == 'acciones_generadas'


@pytest.mark.django_db(transaction=True)
def test_update_accion_verificada_raises():
    from rest_framework.exceptions import ValidationError
    tenant = _register('asvcu1', 'SVCU1', 'admin@asvcu1.com')
    admin = _get_user(tenant, 'admin@asvcu1.com')
    resp = _make_user(tenant, 'r@asvcu1.com', 'responsable')
    sup = _make_user(tenant, 'sup@asvcu1.com', 'supervisor')
    ver = _make_user(tenant, 'ver@asvcu1.com', 'verificador')
    issue = _make_issue(tenant, admin, estado='en_analisis')
    connection.set_tenant(tenant)
    accion = _make_accion(tenant, issue, resp, admin)
    connection.set_tenant(tenant)
    AccionService.transition_state(accion, 'en_proceso', resp)
    _completar_plan(accion, resp, admin)
    AccionService.transition_state(accion, 'cerrado', sup)
    AccionService.transition_state(accion, 'verificado', ver)
    connection.set_tenant(tenant)
    with pytest.raises(ValidationError):
        AccionService.update_accion(accion, {'resultado_esperado': 'nuevo'}, admin)


@pytest.mark.django_db(transaction=True)
def test_update_accion_non_admin_raises():
    from rest_framework.exceptions import PermissionDenied
    tenant = _register('asvcu2', 'SVCU2', 'admin@asvcu2.com')
    admin = _get_user(tenant, 'admin@asvcu2.com')
    resp = _make_user(tenant, 'r@asvcu2.com', 'responsable')
    issue = _make_issue(tenant, admin, estado='en_analisis')
    connection.set_tenant(tenant)
    accion = _make_accion(tenant, issue, resp, admin)
    connection.set_tenant(tenant)
    with pytest.raises(PermissionDenied):
        AccionService.update_accion(accion, {'resultado_esperado': 'nuevo'}, resp)


# ---------------------------------------------------------------------------
# DF-58 — Regresión: límite inclusivo de la asignación temporal
# ---------------------------------------------------------------------------

def _make_accion_con_temporal(schema, hasta):
    """Crea tenant, acción y asigna responsable temporal con la fecha dada."""
    tenant = _register(schema, schema.upper(), f'admin@{schema}.com')
    admin = _get_user(tenant, f'admin@{schema}.com')
    titular = _make_user(tenant, f'titular@{schema}.com', 'responsable')
    temporal = _make_user(tenant, f'temporal@{schema}.com', 'responsable')
    issue = _make_issue(tenant, admin, estado='en_analisis')
    connection.set_tenant(tenant)
    accion = _make_accion(tenant, issue, titular, admin)
    connection.set_tenant(tenant)
    AccionService.assign_responsable_temporal(accion, temporal, hasta, admin)
    connection.set_tenant(tenant)
    return tenant, accion, temporal


@pytest.mark.django_db(transaction=True)
def test_df58_temporal_puede_iniciar_el_ultimo_dia():
    """DF-58: hasta == hoy (fecha local de negocio) debe permitir iniciar."""
    from django.utils import timezone
    hoy = timezone.localdate()
    tenant, accion, temporal = _make_accion_con_temporal('df58sa', hoy)
    AccionService.transition_state(accion, 'en_proceso', temporal)
    assert accion.estado == 'en_proceso'


@pytest.mark.django_db(transaction=True)
def test_df58_temporal_puede_iniciar_con_hasta_futuro():
    from datetime import timedelta
    from django.utils import timezone
    hasta = timezone.localdate() + timedelta(days=3)
    tenant, accion, temporal = _make_accion_con_temporal('df58sb', hasta)
    AccionService.transition_state(accion, 'en_proceso', temporal)
    assert accion.estado == 'en_proceso'


@pytest.mark.django_db(transaction=True)
def test_df58_temporal_expirado_ayer_no_puede_iniciar():
    from datetime import timedelta
    from django.utils import timezone
    from rest_framework.exceptions import PermissionDenied
    hasta = timezone.localdate() - timedelta(days=1)
    tenant, accion, temporal = _make_accion_con_temporal('df58sc', hasta)
    with pytest.raises(PermissionDenied):
        AccionService.transition_state(accion, 'en_proceso', temporal)
    assert accion.estado == 'abierto'


@pytest.mark.django_db(transaction=True)
def test_df58_ultimo_dia_valido_cruzando_medianoche_utc():
    """La validez usa la fecha local de negocio (TIME_ZONE), no la fecha UTC.

    A las 20:30 de Guatemala (02:30 UTC del día siguiente), una asignación con
    hasta == fecha local de hoy debe seguir siendo válida, aunque en UTC ya
    haya cambiado el día. Regresión del uso de date.today() (zona del SO).
    """
    from datetime import date, datetime, timezone as dt_timezone
    from unittest import mock
    from django.utils import timezone

    # 2026-03-10 02:30 UTC == 2026-03-09 20:30 America/Guatemala (UTC-6)
    instante_utc = datetime(2026, 3, 10, 2, 30, tzinfo=dt_timezone.utc)
    hasta_local = date(2026, 3, 9)
    tenant, accion, temporal = _make_accion_con_temporal('df58sd', hasta_local)
    assert timezone.get_current_timezone_name() == 'America/Guatemala'
    with mock.patch('django.utils.timezone.now', return_value=instante_utc):
        assert timezone.localdate() == hasta_local
        AccionService.transition_state(accion, 'en_proceso', temporal)
    assert accion.estado == 'en_proceso'


@pytest.mark.django_db(transaction=True)
def test_df58_temporal_sin_hasta_no_puede_iniciar():
    """Un temporal sin fecha 'hasta' definida no otorga permiso de inicio."""
    from rest_framework.exceptions import PermissionDenied
    tenant, accion, temporal = _make_accion_con_temporal('df58se', None)
    with pytest.raises(PermissionDenied):
        AccionService.transition_state(accion, 'en_proceso', temporal)
    assert accion.estado == 'abierto'
