from django.db import models
from django_tenants.models import TenantMixin, DomainMixin

from apps.tenants.validators import validate_subdomain_format


class Tenant(TenantMixin):
    nombre_empresa = models.CharField(max_length=200)
    email_admin = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    auto_create_schema = True
    auto_drop_schema = True

    class Meta:
        app_label = 'tenants'

    def clean(self):
        super().clean()
        if self.schema_name:
            validate_subdomain_format(self.schema_name)


class Domain(DomainMixin):
    class Meta:
        app_label = 'tenants'
