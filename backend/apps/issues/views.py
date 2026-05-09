from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdminTenant, RequireRole

from .filters import IssueFilter
from .models import DiagramaIshikawa, Issue
from .serializers import (
    IshikawaSerializer,
    IshikawaWriteSerializer,
    IssueDetailSerializer,
    IssueListSerializer,
    IssueWriteSerializer,
)
from .services import IssueService

_WRITE_ROLES = ('admin', 'supervisor', 'responsable')


class IssueViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filterset_class = IssueFilter

    def get_queryset(self):
        return IssueService.queryset_for_user(self.request.user).select_related('reportado_por')

    def get_serializer_class(self):
        if self.action in ('list',):
            return IssueListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return IssueWriteSerializer
        return IssueDetailSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        return ctx

    def create(self, request, *args, **kwargs):
        if request.user.role not in _WRITE_ROLES:
            raise PermissionDenied("No tienes permiso para crear issues.")
        serializer = IssueWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        issue = IssueService.create_issue(
            tipo=d['tipo'],
            titulo=d['titulo'],
            descripcion=d['descripcion'],
            fecha_evento=d['fecha_evento'],
            area=d['area'],
            gravedad=d['gravedad'],
            reportado_por=request.user,
        )
        return Response(
            IssueDetailSerializer(issue, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        issue = self.get_object()
        serializer = IssueWriteSerializer(issue, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        issue = IssueService.update_issue(issue, serializer.validated_data, request.user)
        return Response(IssueDetailSerializer(issue, context={'request': request}).data)

    def destroy(self, request, *args, **kwargs):
        if request.user.role not in ('admin', 'supervisor'):
            raise PermissionDenied("Solo admin o supervisor pueden eliminar issues.")
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'], url_path='transition')
    def transition(self, request, pk=None):
        issue = self.get_object()
        nuevo_estado = request.data.get('estado')
        comentario = request.data.get('comentario', '')
        if not nuevo_estado:
            return Response({'detail': 'El campo estado es requerido.'}, status=400)
        issue = IssueService.transition_state(issue, nuevo_estado, request.user, comentario)
        return Response(IssueDetailSerializer(issue, context={'request': request}).data)


class IshikawaView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_issue(self, pk):
        qs = IssueService.queryset_for_user(self.request.user)
        return qs.get(pk=pk)

    def get(self, request, pk):
        issue = self._get_issue(pk)
        try:
            ishikawa = issue.ishikawa
        except DiagramaIshikawa.DoesNotExist:
            return Response({'detail': 'Este issue no tiene Ishikawa.'}, status=404)
        return Response(IshikawaSerializer(ishikawa).data)

    def put(self, request, pk):
        if request.user.role not in _WRITE_ROLES:
            raise PermissionDenied("No tienes permiso para editar el Ishikawa.")
        issue = self._get_issue(pk)
        serializer = IshikawaWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ishikawa = IssueService.upsert_ishikawa(issue, serializer.validated_data)
        return Response(IshikawaSerializer(ishikawa).data)
