"""
Public schema URL configuration.
Routes served on the main domain (e.g. sgca.com):
  - /admin/        → Django Admin (system admin panel, Req 6.3)
  - /api/public/   → Tenant registration endpoint (task 3.2, Req 1.1)
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/public/', include('apps.tenants.urls')),
]
