import uuid
from datetime import datetime, timezone

import boto3
from botocore.config import Config
from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from .exceptions import InvalidEstadoError, LastActividadError
from .models import Actividad, Evidencia, PlanTrabajo

TRANSICIONES_VALIDAS = {
    'pendiente': ['en_proceso', 'completada'],
    'en_proceso': ['pendiente', 'completada'],
    'completada': ['pendiente', 'en_proceso'],
}


class PlanService:

    # ------------------------------------------------------------------
    # Task 2.1 — CRUD
    # ------------------------------------------------------------------

    @staticmethod
    def create_plan(accion, actividades_data: list, created_by) -> PlanTrabajo:
        if accion.estado == 'verificado':
            raise ValidationError({'detail': 'No se puede crear un plan para una acción verificada.'})
        if hasattr(accion, 'plan_trabajo'):
            raise ValidationError({'detail': 'Esta acción ya tiene un plan de trabajo.'})

        with transaction.atomic():
            plan = PlanTrabajo.objects.create(accion=accion)
            for data in actividades_data:
                PlanService._create_actividad_obj(plan, data, created_by)
        return plan

    @staticmethod
    def add_actividad(plan: PlanTrabajo, descripcion: str, responsable, fecha_limite, requesting_user) -> Actividad:
        if plan.accion.estado == 'verificado':
            raise ValidationError({'detail': 'No se puede modificar el plan de una acción verificada.'})
        PlanService._validate_responsable_belongs_to_tenant(responsable)
        return Actividad.objects.create(
            plan=plan,
            descripcion=descripcion,
            responsable=responsable,
            fecha_limite=fecha_limite,
            estado='pendiente',
        )

    @staticmethod
    def update_actividad(actividad: Actividad, data: dict, requesting_user) -> Actividad:
        role = requesting_user.role
        if role in ('admin', 'supervisor'):
            allowed_fields = {'descripcion', 'responsable', 'fecha_limite'}
        elif role == 'responsable' and actividad.responsable_id == requesting_user.pk:
            allowed_fields = {'descripcion'}
        else:
            raise PermissionDenied('No tienes permiso para editar esta actividad.')

        for field, value in data.items():
            if field not in allowed_fields:
                raise PermissionDenied(f"No puedes modificar el campo '{field}'.")
            setattr(actividad, field, value)
        actividad.save()
        return actividad

    @staticmethod
    def delete_actividad(actividad: Actividad, requesting_user) -> None:
        if actividad.plan.actividades.count() <= 1:
            raise LastActividadError()

        evidencias = list(actividad.evidencias.all())
        for evidencia in evidencias:
            try:
                FileStorageService.delete(evidencia)
            except Exception:
                pass

        actividad.delete()

    # ------------------------------------------------------------------
    # Task 2.2 — State transitions + is_plan_complete + queryset
    # ------------------------------------------------------------------

    @staticmethod
    def transition_actividad(actividad: Actividad, nuevo_estado: str, requesting_user) -> Actividad:
        validos = TRANSICIONES_VALIDAS.get(actividad.estado, [])
        if nuevo_estado not in validos:
            raise InvalidEstadoError(actividad.estado, nuevo_estado)

        role = requesting_user.role
        if role not in ('admin', 'supervisor'):
            if actividad.responsable_id != requesting_user.pk:
                raise PermissionDenied('Solo el responsable asignado puede cambiar el estado de esta actividad.')

        actividad.estado = nuevo_estado
        actividad.save(update_fields=['estado', 'updated_at'])
        return actividad

    @staticmethod
    def is_plan_complete(accion_id: int) -> bool:
        try:
            plan = PlanTrabajo.objects.get(accion_id=accion_id)
        except PlanTrabajo.DoesNotExist:
            return False
        if not plan.actividades.exists():
            return False
        return not plan.actividades.exclude(estado='completada').exists()

    @staticmethod
    def queryset_for_user(user):
        qs = PlanTrabajo.objects.all()
        if user.role == 'responsable':
            qs = qs.filter(accion__responsable=user)
        return qs

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _create_actividad_obj(plan: PlanTrabajo, data: dict, created_by) -> Actividad:
        responsable = data.get('responsable') or created_by
        PlanService._validate_responsable_belongs_to_tenant(responsable)
        return Actividad.objects.create(
            plan=plan,
            descripcion=data['descripcion'],
            responsable=responsable,
            fecha_limite=data['fecha_limite'],
            estado='pendiente',
        )

    @staticmethod
    def _validate_responsable_belongs_to_tenant(responsable) -> None:
        from apps.users.models import CustomUser
        if not CustomUser.objects.filter(pk=responsable.pk).exists():
            raise ValidationError({'responsable_id': 'El usuario no pertenece a este tenant.'})


# ---------------------------------------------------------------------------
# Task 2.3 — FileStorageService
# ---------------------------------------------------------------------------

MAGIC_BYTES = {
    b'\x25\x50\x44\x46': 'application/pdf',
    b'\xff\xd8\xff': 'image/jpeg',
    b'\x89\x50\x4e\x47': 'image/png',
}


def _detect_content_type_from_magic(file_obj) -> str | None:
    header = file_obj.read(8)
    file_obj.seek(0)
    for magic, ct in MAGIC_BYTES.items():
        if header.startswith(magic):
            return ct
    if len(header) >= 8 and header[4:8] in (b'ftyp', b'moov', b'mdat'):
        return 'video/mp4'
    return None


class FileStorageService:

    @staticmethod
    def upload(file, tenant_slug: str, accion_id: int, actividad_id: int, uploaded_by, actividad) -> Evidencia:
        if file.size > Evidencia.MAX_SIZE_BYTES:
            raise ValidationError({'archivo': f'El archivo supera el límite de 50 MB.'})

        detected_ct = _detect_content_type_from_magic(file)
        declared_ct = getattr(file, 'content_type', None)
        content_type = detected_ct or declared_ct

        if content_type not in Evidencia.TIPOS_PERMITIDOS:
            raise ValidationError({'archivo': f'Tipo de archivo no permitido. Tipos aceptados: PDF, JPG, PNG, MP4.'})

        unique_name = f"{uuid.uuid4()}_{file.name}"
        s3_path = f"{tenant_slug}/evidencias/{accion_id}/{actividad_id}/{unique_name}"

        client = FileStorageService._get_client()
        file.seek(0)
        client.upload_fileobj(
            file,
            settings.AWS_STORAGE_BUCKET_NAME,
            s3_path,
            ExtraArgs={'ContentType': content_type},
        )

        return Evidencia.objects.create(
            actividad=actividad,
            s3_path=s3_path,
            nombre_original=file.name,
            content_type=content_type,
            tamaño_bytes=file.size,
            uploaded_by=uploaded_by,
        )

    @staticmethod
    def delete(evidencia: Evidencia) -> None:
        client = FileStorageService._get_client()
        client.delete_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=evidencia.s3_path,
        )
        evidencia.delete()

    @staticmethod
    def get_signed_url(evidencia: Evidencia, expires: int = 3600) -> dict:
        client = FileStorageService._get_client()
        url = client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': evidencia.s3_path,
            },
            ExpiresIn=expires,
        )
        expires_at = datetime.now(tz=timezone.utc).isoformat()
        return {'url': url, 'expires_at': expires_at}

    @staticmethod
    def _get_client():
        kwargs = {
            'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
            'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
            'region_name': settings.AWS_S3_REGION_NAME,
            'config': Config(signature_version='s3v4'),
        }
        endpoint = getattr(settings, 'AWS_S3_ENDPOINT_URL', '')
        if endpoint:
            kwargs['endpoint_url'] = endpoint
        return boto3.client('s3', **kwargs)
