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


class Plan(models.Model):
    TRIAL = 'trial'
    ENTERPRISE = 'enterprise'
    NOMBRE_CHOICES = [(TRIAL, 'Trial'), (ENTERPRISE, 'Enterprise')]

    nombre = models.CharField(max_length=20, choices=NOMBRE_CHOICES, unique=True)

    class Meta:
        app_label = 'tenants'

    def __str__(self):
        return self.nombre


class Subscription(models.Model):
    tenant = models.OneToOneField(
        Tenant, on_delete=models.CASCADE, related_name='subscription'
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    fecha_inicio = models.DateField(auto_now_add=True)
    fecha_fin = models.DateField(null=True, blank=True)
    num_licencias = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        app_label = 'tenants'

    def is_active(self) -> bool:
        if self.plan.nombre == Plan.ENTERPRISE:
            return True
        from datetime import date
        return self.fecha_fin is not None and self.fecha_fin >= date.today()
