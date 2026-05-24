"""
Tenant schema URL configuration.
Routes served on tenant subdomains (e.g. acme.sgca.com).
"""
from django.urls import include, path

urlpatterns = [
    path('', include('apps.users.urls')),
    path('', include('apps.issues.urls')),
    path('', include('apps.acciones.urls')),
    path('', include('apps.planes.urls')),
]
