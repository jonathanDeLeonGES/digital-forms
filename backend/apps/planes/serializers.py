from rest_framework import serializers

from .models import Actividad, Evidencia, PlanTrabajo


class ActividadSerializer(serializers.ModelSerializer):
    responsable_nombre = serializers.CharField(source='responsable.nombre_completo', read_only=True)

    class Meta:
        model = Actividad
        fields = ['id', 'descripcion', 'responsable', 'responsable_nombre', 'fecha_limite', 'estado', 'created_at']
        read_only_fields = ['id', 'estado', 'created_at']


class ActividadWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Actividad
        fields = ['descripcion', 'responsable', 'fecha_limite']


class ActividadTransitionSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(choices=[c[0] for c in Actividad.ESTADOS])


class EvidenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evidencia
        fields = ['id', 'nombre_original', 'content_type', 'tamaño_bytes', 'uploaded_by', 'uploaded_at']
        read_only_fields = fields


class PlanTrabajoListSerializer(serializers.ModelSerializer):
    progreso = serializers.IntegerField(read_only=True)

    class Meta:
        model = PlanTrabajo
        fields = ['id', 'accion', 'progreso', 'created_at', 'updated_at']


class PlanTrabajoDetailSerializer(serializers.ModelSerializer):
    progreso = serializers.IntegerField(read_only=True)
    actividades = ActividadSerializer(many=True, read_only=True)

    class Meta:
        model = PlanTrabajo
        fields = ['id', 'accion', 'progreso', 'actividades', 'created_at', 'updated_at']


class ActividadInputSerializer(serializers.Serializer):
    descripcion = serializers.CharField()
    responsable = serializers.IntegerField()
    fecha_limite = serializers.DateField()


class PlanTrabajoWriteSerializer(serializers.Serializer):
    accion = serializers.IntegerField()
    actividades = ActividadInputSerializer(many=True, min_length=1)
