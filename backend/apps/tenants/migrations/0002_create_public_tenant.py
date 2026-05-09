"""
Data migration: bootstrap the public tenant, localhost domain, and Plan fixtures.

The public tenant (schema_name='public') must exist in the database so that
TenantMainMiddleware can resolve requests on the main domain to the public
schema — where the tenant-registration endpoint lives.

django-tenants skips CREATE SCHEMA for 'public' because the schema already
exists in PostgreSQL (CREATE SCHEMA IF NOT EXISTS is a no-op there).
"""
from django.db import migrations


def create_public_tenant_and_plans(apps, schema_editor):
    from apps.tenants.models import Domain, Plan, Tenant

    # Seed the plan catalog used by TenantRegistrationService
    Plan.objects.get_or_create(nombre='trial')
    Plan.objects.get_or_create(nombre='enterprise')

    # Public tenant — maps the main domain to the public schema
    tenant, _ = Tenant.objects.get_or_create(
        schema_name='public',
        defaults={
            'nombre_empresa': 'SGCA Platform',
            'email_admin': 'system@sgca.com',
        },
    )

    # Development: requests from localhost reach the public schema
    Domain.objects.get_or_create(
        domain='localhost',
        defaults={'tenant': tenant, 'is_primary': True},
    )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_public_tenant_and_plans, noop),
    ]
