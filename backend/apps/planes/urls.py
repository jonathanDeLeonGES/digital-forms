from django.urls import path

from .views import ActividadViewSet, EvidenciaViewSet, PlanViewSet

plan_list = PlanViewSet.as_view({'get': 'list', 'post': 'create'})
plan_detail = PlanViewSet.as_view({'get': 'retrieve', 'put': 'update'})

actividad_create = ActividadViewSet.as_view({'post': 'create'})
actividad_detail = ActividadViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'})
actividad_transition = ActividadViewSet.as_view({'post': 'transition'})
actividad_evidencias = ActividadViewSet.as_view({'get': 'evidencias'})
actividad_upload = ActividadViewSet.as_view({'post': 'upload_evidencia'})

evidencia_detail = EvidenciaViewSet.as_view({'delete': 'destroy'})
evidencia_signed_url = EvidenciaViewSet.as_view({'get': 'signed_url'})

urlpatterns = [
    path('api/planes/', plan_list, name='plan-list'),
    path('api/planes/<int:pk>/', plan_detail, name='plan-detail'),
    path('api/actividades/', actividad_create, name='actividad-create'),
    path('api/actividades/<int:pk>/', actividad_detail, name='actividad-detail'),
    path('api/actividades/<int:pk>/transition/', actividad_transition, name='actividad-transition'),
    path('api/actividades/<int:pk>/evidencias/', actividad_evidencias, name='actividad-evidencias'),
    path('api/actividades/<int:pk>/evidencias/upload/', actividad_upload, name='actividad-upload'),
    path('api/evidencias/<int:pk>/', evidencia_detail, name='evidencia-detail'),
    path('api/evidencias/<int:pk>/signed-url/', evidencia_signed_url, name='evidencia-signed-url'),
]
