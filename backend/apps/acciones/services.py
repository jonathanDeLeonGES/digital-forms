from datetime import date

from rest_framework.exceptions import PermissionDenied, ValidationError

from .exceptions import InvalidTransitionError
from .models import Accion, HistorialEstado
from .signals import accion_estado_cambiado


class AccionService:

    @staticmethod
    def create_accion(
        issue,
        tipo: str,
        resultado_esperado: str,
        responsable,
        fecha_limite: date,
        created_by,
    ) -> Accion:
        from apps.users.models import CustomUser
        if not CustomUser.objects.filter(pk=responsable.pk, email=responsable.email).exists():
            raise ValidationError({'responsable_id': 'El usuario no existe en este tenant.'})

        ESTADOS_VALIDOS = ('en_analisis', 'acciones_generadas')
        if issue.estado not in ESTADOS_VALIDOS:
            raise ValidationError({'issue_id': 'Solo se pueden crear acciones para issues en análisis o con acciones generadas.'})

        accion = Accion.objects.create(
            issue=issue,
            tipo=tipo,
            resultado_esperado=resultado_esperado,
            responsable=responsable,
            fecha_limite=fecha_limite,
            estado='abierto',
            created_by=created_by,
        )
        AccionService._trigger_issue_transition_if_needed(issue, created_by)
        return accion

    @staticmethod
    def update_accion(accion: Accion, data: dict, requesting_user) -> Accion:
        if requesting_user.role != 'admin':
            raise PermissionDenied('Solo el admin puede editar acciones.')
        if accion.estado == 'verificado':
            raise ValidationError({'detail': 'Las acciones verificadas no pueden ser modificadas.'})
        for field, value in data.items():
            setattr(accion, field, value)
        accion.save()
        return accion

    @staticmethod
    def queryset_for_user(user):
        qs = Accion.objects.all()
        if user.role == 'responsable':
            qs = qs.filter(responsable=user)
        return qs

    @staticmethod
    def transition_state(
        accion: Accion,
        nuevo_estado: str,
        requesting_user,
        comentario: str = '',
    ) -> Accion:
        AccionService._validate_transition(accion, nuevo_estado, requesting_user)

        estado_anterior = accion.estado
        accion.estado = nuevo_estado
        accion.save(update_fields=['estado', 'updated_at'])

        historial = HistorialEstado.objects.create(
            accion=accion,
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            usuario=requesting_user,
            comentario=comentario,
        )

        accion_estado_cambiado.send(
            sender=Accion,
            accion=accion,
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            usuario=requesting_user,
            timestamp=historial.timestamp,
        )
        return accion

    @staticmethod
    def _validate_transition(accion: Accion, nuevo_estado: str, requesting_user) -> None:
        validos = Accion.TRANSICIONES_VALIDAS.get(accion.estado, [])
        if nuevo_estado not in validos:
            raise InvalidTransitionError(accion.estado, nuevo_estado)

        if accion.estado == 'en_proceso' and nuevo_estado == 'cerrado':
            from apps.planes.services import PlanService
            if not PlanService.is_plan_complete(accion.pk):
                raise ValidationError({'detail': 'El plan de trabajo no está completo. Todas las actividades deben estar completadas antes de cerrar la acción.'})

        if requesting_user.role == 'admin':
            return

        key = (accion.estado, nuevo_estado)
        rol_requerido = Accion.ROLES_TRANSICION.get(key)

        if rol_requerido == 'responsable_asignado':
            if accion.responsable_id != requesting_user.pk:
                raise PermissionDenied(
                    'Solo el responsable asignado o admin pueden iniciar esta acción.'
                )
        elif rol_requerido == 'supervisor':
            if requesting_user.role != 'supervisor':
                raise PermissionDenied('Solo el supervisor puede cerrar una acción.')
        elif rol_requerido == 'verificador':
            if requesting_user.role != 'verificador':
                raise PermissionDenied('Solo el verificador puede verificar una acción.')

    @staticmethod
    def _trigger_issue_transition_if_needed(issue, created_by) -> None:
        first_accion = Accion.objects.filter(issue=issue).count() == 1
        if first_accion and issue.estado == 'en_analisis':
            from apps.issues.services import IssueService
            IssueService.transition_state(issue, 'acciones_generadas', created_by)
