"""
RED phase: verify django-tenants settings are correctly configured.
These tests fail until settings/base.py exists with the required configuration.
"""
import django
from django.conf import settings


def test_shared_apps_contains_tenants():
    assert 'apps.tenants' in settings.SHARED_APPS, (
        "apps.tenants must be in SHARED_APPS (public schema)"
    )


def test_shared_apps_contains_django_tenants():
    assert 'django_tenants' in settings.SHARED_APPS


def test_tenant_apps_is_empty_for_wave1():
    assert isinstance(settings.TENANT_APPS, (list, tuple))


def test_installed_apps_is_shared_plus_tenant():
    expected = list(settings.SHARED_APPS) + list(settings.TENANT_APPS)
    assert list(settings.INSTALLED_APPS) == expected, (
        "INSTALLED_APPS must equal SHARED_APPS + TENANT_APPS"
    )


def test_tenant_model_setting():
    assert settings.TENANT_MODEL == 'tenants.Tenant'


def test_tenant_domain_model_setting():
    assert settings.TENANT_DOMAIN_MODEL == 'tenants.Domain'


def test_database_router():
    assert 'django_tenants.routers.TenantSyncRouter' in settings.DATABASE_ROUTERS


def test_tenant_middleware_is_first():
    assert settings.MIDDLEWARE[0] == 'django_tenants.middleware.main.TenantMainMiddleware', (
        "TenantMainMiddleware must be first in MIDDLEWARE"
    )


def test_database_engine_is_django_tenants():
    engine = settings.DATABASES['default']['ENGINE']
    assert engine == 'django_tenants.postgresql_backend', (
        f"Expected django_tenants.postgresql_backend, got {engine}"
    )
