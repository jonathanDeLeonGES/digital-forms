from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AccionViewSet

router = DefaultRouter()
router.register(r'api/acciones', AccionViewSet, basename='accion')

urlpatterns = [
    path('', include(router.urls)),
]
