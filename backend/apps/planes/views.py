from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.users.permissions import IsAdminTenant, RequireRole

from .models import Actividad, Evidencia, PlanTrabajo
from .serializers import (
    ActividadSerializer,
    ActividadTransitionSerializer,
    ActividadWriteSerializer,
    EvidenciaSerializer,
    PlanTrabajoDetailSerializer,
    PlanTrabajoListSerializer,
    PlanTrabajoWriteSerializer,
)
from .services import FileStorageService, PlanService


class PlanViewSet(ViewSet):
    permission_classes = [RequireRole('admin', 'supervisor', 'responsable', 'verificador')]

    def list(self, request):
        qs = PlanService.queryset_for_user(request.user).select_related('accion')
        serializer = PlanTrabajoListSerializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request):
        if request.user.role not in ('admin', 'supervisor'):
            return Response({'detail': 'Solo admin o supervisor pueden crear planes.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = PlanTrabajoWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from apps.acciones.models import Accion
        accion = get_object_or_404(Accion, pk=data['accion'])

        from apps.users.models import CustomUser
        actividades_data = []
        for act in data['actividades']:
            responsable = get_object_or_404(CustomUser, pk=act['responsable'])
            actividades_data.append({
                'descripcion': act['descripcion'],
                'responsable': responsable,
                'fecha_limite': act['fecha_limite'],
            })

        plan = PlanService.create_plan(accion, actividades_data, request.user)
        return Response(PlanTrabajoDetailSerializer(plan).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        qs = PlanService.queryset_for_user(request.user)
        plan = get_object_or_404(qs, pk=pk)
        return Response(PlanTrabajoDetailSerializer(plan).data)

    def update(self, request, pk=None):
        if request.user.role not in ('admin', 'supervisor'):
            return Response({'detail': 'Solo admin o supervisor pueden editar planes.'}, status=status.HTTP_403_FORBIDDEN)
        plan = get_object_or_404(PlanTrabajo, pk=pk)
        return Response(PlanTrabajoDetailSerializer(plan).data)


class ActividadViewSet(ViewSet):
    permission_classes = [RequireRole('admin', 'supervisor', 'responsable', 'verificador')]

    def create(self, request):
        if request.user.role not in ('admin', 'supervisor'):
            return Response({'detail': 'Solo admin o supervisor pueden agregar actividades.'}, status=status.HTTP_403_FORBIDDEN)

        plan_id = request.data.get('plan')
        plan = get_object_or_404(PlanTrabajo, pk=plan_id)

        serializer = ActividadWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        actividad = PlanService.add_actividad(
            plan=plan,
            descripcion=vd['descripcion'],
            responsable=vd['responsable'],
            fecha_limite=vd['fecha_limite'],
            requesting_user=request.user,
        )
        return Response(ActividadSerializer(actividad).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        actividad = get_object_or_404(Actividad, pk=pk)
        return Response(ActividadSerializer(actividad).data)

    def update(self, request, pk=None):
        actividad = get_object_or_404(Actividad, pk=pk)
        serializer = ActividadWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        actividad = PlanService.update_actividad(actividad, serializer.validated_data, request.user)
        return Response(ActividadSerializer(actividad).data)

    def destroy(self, request, pk=None):
        if request.user.role not in ('admin', 'supervisor'):
            return Response({'detail': 'Solo admin o supervisor pueden eliminar actividades.'}, status=status.HTTP_403_FORBIDDEN)
        actividad = get_object_or_404(Actividad, pk=pk)
        PlanService.delete_actividad(actividad, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='transition')
    def transition(self, request, pk=None):
        actividad = get_object_or_404(Actividad, pk=pk)
        serializer = ActividadTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actividad = PlanService.transition_actividad(
            actividad, serializer.validated_data['estado'], request.user
        )
        return Response(ActividadSerializer(actividad).data)

    @action(detail=True, methods=['get'], url_path='evidencias')
    def evidencias(self, request, pk=None):
        actividad = get_object_or_404(Actividad, pk=pk)
        qs = actividad.evidencias.all()
        return Response(EvidenciaSerializer(qs, many=True).data)

    @action(detail=True, methods=['post'], url_path='evidencias/upload',
            parser_classes=[MultiPartParser])
    def upload_evidencia(self, request, pk=None):
        actividad = get_object_or_404(Actividad, pk=pk)
        file = request.FILES.get('archivo')
        if not file:
            return Response({'detail': 'Se requiere el archivo.'}, status=status.HTTP_400_BAD_REQUEST)

        tenant = request.tenant
        tenant_slug = tenant.schema_name

        evidencia = FileStorageService.upload(
            file=file,
            tenant_slug=tenant_slug,
            accion_id=actividad.plan.accion_id,
            actividad_id=actividad.pk,
            uploaded_by=request.user,
            actividad=actividad,
        )
        return Response(EvidenciaSerializer(evidencia).data, status=status.HTTP_201_CREATED)


class EvidenciaViewSet(ViewSet):
    permission_classes = [RequireRole('admin', 'supervisor', 'responsable', 'verificador')]

    def destroy(self, request, pk=None):
        if request.user.role not in ('admin', 'supervisor'):
            return Response({'detail': 'Solo admin o supervisor pueden eliminar evidencias.'}, status=status.HTTP_403_FORBIDDEN)
        evidencia = get_object_or_404(Evidencia, pk=pk)
        FileStorageService.delete(evidencia)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], url_path='signed-url')
    def signed_url(self, request, pk=None):
        evidencia = get_object_or_404(Evidencia, pk=pk)
        result = FileStorageService.get_signed_url(evidencia)
        return Response(result)
