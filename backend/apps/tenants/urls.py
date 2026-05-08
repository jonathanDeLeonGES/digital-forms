from django.urls import path

from .views import TenantRegistrationView

urlpatterns = [
    path("tenants/register/", TenantRegistrationView.as_view(), name="tenant-register"),
]
