from rest_framework import serializers

from .models import Accion, HistorialEstado


class UserBasicSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre_completo = serializers.CharField()


class IssueBasicSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    titulo = serializers.CharField()


class HistorialEstadoSerializer(serializers.ModelSerializer):
    usuario = UserBasicSerializer(read_only=True)

    class Meta:
        model = HistorialEstado
        fields = ['id', 'estado_anterior', 'estado_nuevo', 'usuario', 'timestamp', 'comentario']
        read_only_fields = fields


class AccionListSerializer(serializers.ModelSerializer):
    responsable = UserBasicSerializer(read_only=True)
    issue = IssueBasicSerializer(read_only=True)
    resultado_esperado_resumen = serializers.SerializerMethodField()
    responsable_temporal = serializers.SerializerMethodField()
    responsable_temporal_hasta = serializers.DateField(read_only=True, allow_null=True)

    class Meta:
        model = Accion
        fields = [
            'id', 'tipo', 'resultado_esperado_resumen', 'responsable',
            'responsable_temporal', 'responsable_temporal_hasta',
            'estado', 'fecha_limite', 'issue', 'created_at',
        ]

    def get_resultado_esperado_resumen(self, obj):
        return obj.resultado_esperado[:150]

    def get_responsable_temporal(self, obj):
        if not obj.responsable_temporal_id:
            return None
        return {
            'id': obj.responsable_temporal.id,
            'nombre_completo': obj.responsable_temporal.nombre_completo,
        }


class AccionDetailSerializer(serializers.ModelSerializer):
    responsable = UserBasicSerializer(read_only=True)
    issue = IssueBasicSerializer(read_only=True)
    created_by = UserBasicSerializer(read_only=True)
    historial_estados = serializers.SerializerMethodField()
    responsable_temporal = serializers.SerializerMethodField()
    responsable_temporal_hasta = serializers.DateField(read_only=True, allow_null=True)

    class Meta:
        model = Accion
        fields = [
            'id', 'tipo', 'resultado_esperado', 'responsable',
            'responsable_temporal', 'responsable_temporal_hasta',
            'estado', 'fecha_limite', 'issue', 'created_by',
            'created_at', 'updated_at', 'historial_estados',
        ]

    def get_responsable_temporal(self, obj):
        if not obj.responsable_temporal_id:
            return None
        return {
            'id': obj.responsable_temporal.id,
            'nombre_completo': obj.responsable_temporal.nombre_completo,
        }

    def get_historial_estados(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.role in ('admin', 'supervisor'):
            return HistorialEstadoSerializer(obj.historial_estados.all(), many=True).data
        return []


class AccionWriteSerializer(serializers.Serializer):
    issue_id = serializers.IntegerField()
    tipo = serializers.ChoiceField(choices=Accion.TIPOS)
    resultado_esperado = serializers.CharField()
    responsable_id = serializers.IntegerField()
    fecha_limite = serializers.DateField()

    def validate_issue_id(self, value):
        from apps.issues.models import Issue
        if not Issue.objects.filter(pk=value).exists():
            raise serializers.ValidationError('El issue no existe en este tenant.')
        return value

    def validate_responsable_id(self, value):
        from apps.users.models import CustomUser
        if not CustomUser.objects.filter(pk=value).exists():
            raise serializers.ValidationError('El usuario no existe en este tenant.')
        return value


class TransitionSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(choices=Accion.ESTADOS)
    comentario = serializers.CharField(required=False, default='', allow_blank=True)


class AssignResponsableTemporalSerializer(serializers.Serializer):
    responsable_temporal_id = serializers.IntegerField()
    responsable_temporal_hasta = serializers.DateField()

    def validate_responsable_temporal_id(self, value):
        from apps.users.models import CustomUser
        if not CustomUser.objects.filter(pk=value).exists():
            raise serializers.ValidationError('El usuario no existe en este tenant.')
        return value
