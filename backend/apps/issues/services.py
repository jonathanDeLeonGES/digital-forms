from datetime import date

from rest_framework.exceptions import PermissionDenied

from .exceptions import InvalidTransitionError
from .models import (
    CausaRaiz,
    DiagramaIshikawa,
    HistorialTransicionIssue,
    Issue,
    SubCausa,
)

_ADMIN_SUPERVISOR = ('admin', 'supervisor')


class IssueService:

    @staticmethod
    def create_issue(
        tipo: str,
        titulo: str,
        descripcion: str,
        fecha_evento: date,
        area: str,
        gravedad: str,
        reportado_por,
    ) -> Issue:
        return Issue.objects.create(
            tipo=tipo,
            titulo=titulo,
            descripcion=descripcion,
            fecha_evento=fecha_evento,
            area=area,
            gravedad=gravedad,
            estado='abierto',
            reportado_por=reportado_por,
        )

    @staticmethod
    def update_issue(issue: Issue, data: dict, requesting_user) -> Issue:
        if requesting_user.role not in _ADMIN_SUPERVISOR:
            if issue.reportado_por_id != requesting_user.pk:
                raise PermissionDenied("No tienes permiso para editar este issue.")
        for field, value in data.items():
            setattr(issue, field, value)
        issue.save()
        return issue

    @staticmethod
    def queryset_for_user(user):
        qs = Issue.objects.all()
        if user.role == 'responsable':
            qs = qs.filter(reportado_por=user)
        return qs

    @staticmethod
    def transition_state(
        issue: Issue,
        nuevo_estado: str,
        requesting_user,
        comentario: str = '',
    ) -> Issue:
        validos = Issue.TRANSICIONES_VALIDAS.get(issue.estado, [])
        if nuevo_estado not in validos:
            raise InvalidTransitionError(issue.estado, nuevo_estado)

        # Solo admin/supervisor pueden transicionar hacia/desde estados avanzados
        estados_restringidos = {'acciones_generadas', 'cerrado'}
        if nuevo_estado in estados_restringidos or issue.estado in estados_restringidos:
            if requesting_user.role not in _ADMIN_SUPERVISOR:
                raise PermissionDenied("Solo admin o supervisor pueden realizar esta transición.")

        estado_anterior = issue.estado
        issue.estado = nuevo_estado
        issue.save(update_fields=['estado', 'updated_at'])

        HistorialTransicionIssue.objects.create(
            issue=issue,
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            usuario=requesting_user,
            comentario=comentario,
        )
        return issue

    @staticmethod
    def upsert_ishikawa(issue: Issue, causas_por_categoria: dict) -> DiagramaIshikawa:
        diagrama, _ = DiagramaIshikawa.objects.get_or_create(issue=issue)

        for categoria, causas_data in causas_por_categoria.items():
            causa_ids_recibidos = []
            for causa_data in causas_data:
                causa_id = causa_data.get('id')
                subcausas_data = causa_data.get('subcausas', [])

                if causa_id:
                    causa = CausaRaiz.objects.get(pk=causa_id, diagrama=diagrama)
                    causa.descripcion = causa_data['descripcion']
                    causa.save(update_fields=['descripcion'])
                else:
                    causa = CausaRaiz.objects.create(
                        diagrama=diagrama,
                        categoria=categoria,
                        descripcion=causa_data['descripcion'],
                    )
                causa_ids_recibidos.append(causa.pk)

                # Upsert subcausas
                sub_ids_recibidos = []
                for sub_data in subcausas_data:
                    sub_id = sub_data.get('id')
                    if sub_id:
                        sub = SubCausa.objects.get(pk=sub_id, causa=causa)
                        sub.descripcion = sub_data['descripcion']
                        sub.save(update_fields=['descripcion'])
                    else:
                        sub = SubCausa.objects.create(
                            causa=causa,
                            descripcion=sub_data['descripcion'],
                        )
                    sub_ids_recibidos.append(sub.pk)

                # Eliminar subcausas removidas del payload
                causa.subcausas.exclude(pk__in=sub_ids_recibidos).delete()

            # Eliminar causas de esta categoría removidas del payload
            diagrama.causas.filter(
                categoria=categoria
            ).exclude(pk__in=causa_ids_recibidos).delete()

        diagrama.refresh_from_db()
        return diagrama
