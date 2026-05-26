from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.issues.models import Issue
from apps.users.models import CustomUser
from apps.users.permissions import RequireRole

from .filters import AccionFilter
from .models import Accion
from .serializers import (
    AccionDetailSerializer,
    AccionListSerializer,
    AccionWriteSerializer,
    AssignResponsableTemporalSerializer,
    HistorialEstadoSerializer,
    TransitionSerializer,
)
from .services import AccionService

_CREATE_ROLES = ('admin', 'supervisor')


class AccionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filterset_class = AccionFilter
    ordering_fields = ['fecha_limite', 'created_at', 'estado']
    ordering = ['-created_at']

    def get_queryset(self):
        return AccionService.queryset_for_user(self.request.user).select_related(
            'responsable', 'responsable_temporal', 'issue', 'created_by'
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return AccionListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return AccionWriteSerializer
        return AccionDetailSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        return ctx

    def create(self, request, *args, **kwargs):
        if request.user.role not in _CREATE_ROLES:
            return Response(
                {'detail': 'Solo admin o supervisor pueden crear acciones.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = AccionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        issue = Issue.objects.get(pk=d['issue_id'])
        responsable = CustomUser.objects.get(pk=d['responsable_id'])

        accion = AccionService.create_accion(
            issue=issue,
            tipo=d['tipo'],
            resultado_esperado=d['resultado_esperado'],
            responsable=responsable,
            fecha_limite=d['fecha_limite'],
            created_by=request.user,
        )
        return Response(
            AccionDetailSerializer(accion, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        accion = self.get_object()
        serializer = AccionWriteSerializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        update_data = {}
        if 'tipo' in d:
            update_data['tipo'] = d['tipo']
        if 'resultado_esperado' in d:
            update_data['resultado_esperado'] = d['resultado_esperado']
        if 'fecha_limite' in d:
            update_data['fecha_limite'] = d['fecha_limite']
        if 'responsable_id' in d:
            update_data['responsable'] = CustomUser.objects.get(pk=d['responsable_id'])
        if 'issue_id' in d:
            update_data['issue'] = Issue.objects.get(pk=d['issue_id'])

        accion = AccionService.update_accion(accion, update_data, request.user)
        return Response(AccionDetailSerializer(accion, context={'request': request}).data)

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=True, methods=['post'], url_path='transition')
    def transition(self, request, pk=None):
        accion = self.get_object()
        serializer = TransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        accion = AccionService.transition_state(
            accion, d['estado'], request.user, d.get('comentario', '')
        )
        return Response(AccionDetailSerializer(accion, context={'request': request}).data)

    @action(
        detail=True,
        methods=['get'],
        url_path='historial',
        permission_classes=[IsAuthenticated, RequireRole('admin', 'supervisor')],
    )
    def historial(self, request, pk=None):
        accion = self.get_object()
        data = HistorialEstadoSerializer(accion.historial_estados.all(), many=True).data
        return Response(data)

    @action(detail=True, methods=['post', 'delete'], url_path='responsable-temporal')
    def responsable_temporal(self, request, pk=None):
        accion = self.get_object()
        if request.user.role != 'admin':
            return Response(
                {'detail': 'Solo el admin puede gestionar el responsable temporal.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if request.method == 'DELETE':
            accion = AccionService.remove_responsable_temporal(accion, request.user)
            return Response(AccionDetailSerializer(accion, context={'request': request}).data)

        serializer = AssignResponsableTemporalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        responsable_temp = CustomUser.objects.get(pk=d['responsable_temporal_id'])
        accion = AccionService.assign_responsable_temporal(
            accion, responsable_temp, d['responsable_temporal_hasta'], request.user
        )
        return Response(AccionDetailSerializer(accion, context={'request': request}).data)
