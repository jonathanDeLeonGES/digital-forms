import django_filters

from .models import Issue


class IssueFilter(django_filters.FilterSet):
    fecha_evento__gte = django_filters.DateFilter(field_name='fecha_evento', lookup_expr='gte')
    fecha_evento__lte = django_filters.DateFilter(field_name='fecha_evento', lookup_expr='lte')

    class Meta:
        model = Issue
        fields = {
            'tipo': ['exact'],
            'estado': ['exact'],
            'gravedad': ['exact'],
            'area': ['exact'],
        }
