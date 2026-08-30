import django_filters

from .models import Accion


class AccionFilter(django_filters.FilterSet):
    fecha_limite__gte = django_filters.DateFilter(field_name='fecha_limite', lookup_expr='gte')
    fecha_limite__lte = django_filters.DateFilter(field_name='fecha_limite', lookup_expr='lte')
    created_at__gte = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_at__lte = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Accion
        fields = ['estado', 'tipo', 'responsable']
