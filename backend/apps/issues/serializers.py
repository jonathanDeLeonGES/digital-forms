from rest_framework import serializers

from .models import CausaRaiz, DiagramaIshikawa, HistorialTransicionIssue, Issue, SubCausa


class UserBasicSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre_completo = serializers.CharField()


class SubCausaSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCausa
        fields = ['id', 'descripcion']


class CausaRaizSerializer(serializers.ModelSerializer):
    subcausas = SubCausaSerializer(many=True, read_only=True)

    class Meta:
        model = CausaRaiz
        fields = ['id', 'categoria', 'descripcion', 'subcausas']


class IshikawaSerializer(serializers.ModelSerializer):
    categorias = serializers.SerializerMethodField()

    class Meta:
        model = DiagramaIshikawa
        fields = ['id', 'issue', 'categorias']

    def get_categorias(self, obj):
        cats = {key: [] for key, _ in CausaRaiz.CATEGORIAS}
        for causa in obj.causas.prefetch_related('subcausas').all():
            cats[causa.categoria].append(CausaRaizSerializer(causa).data)
        return cats


class HistorialTransicionSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source='usuario.nombre_completo', read_only=True)

    class Meta:
        model = HistorialTransicionIssue
        fields = ['id', 'estado_anterior', 'estado_nuevo', 'usuario_nombre', 'timestamp', 'comentario']


class IssueListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Issue
        fields = ['id', 'tipo', 'titulo', 'area', 'gravedad', 'estado', 'reportado_por', 'fecha_evento', 'created_at']


class IssueDetailSerializer(serializers.ModelSerializer):
    reportado_por = UserBasicSerializer(read_only=True)
    ishikawa = serializers.SerializerMethodField()
    historial_estados = serializers.SerializerMethodField()

    class Meta:
        model = Issue
        fields = [
            'id', 'tipo', 'titulo', 'descripcion', 'area', 'gravedad', 'estado',
            'reportado_por', 'fecha_evento', 'created_at', 'updated_at',
            'ishikawa', 'historial_estados',
        ]

    def get_ishikawa(self, obj):
        try:
            return IshikawaSerializer(obj.ishikawa).data
        except DiagramaIshikawa.DoesNotExist:
            return None

    def get_historial_estados(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.role in ('admin', 'supervisor'):
            return HistorialTransicionSerializer(obj.historial_estados.all(), many=True).data
        return []


class IssueWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Issue
        fields = ['tipo', 'titulo', 'descripcion', 'fecha_evento', 'area', 'gravedad']


# --- Ishikawa write ---

class SubCausaWriteSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    descripcion = serializers.CharField()


class CausaRaizWriteSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    categoria = serializers.ChoiceField(choices=CausaRaiz.CATEGORIAS)
    descripcion = serializers.CharField()
    subcausas = SubCausaWriteSerializer(many=True, default=list)


class IshikawaWriteSerializer(serializers.Serializer):
    causas = CausaRaizWriteSerializer(many=True)

    def to_internal_value(self, data):
        validated = super().to_internal_value(data)
        # Group by categoria for IssueService.upsert_ishikawa()
        causas_por_categoria = {}
        for causa in validated['causas']:
            cat = causa['categoria']
            causas_por_categoria.setdefault(cat, []).append(causa)
        return causas_por_categoria
