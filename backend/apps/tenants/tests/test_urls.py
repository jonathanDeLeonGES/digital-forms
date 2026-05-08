"""
Tests for URL routing configuration (task 1.2).
RED phase: these tests verify the URL routing structure. They pass once the
URL files are correctly populated.
"""
from django.conf import settings


def test_root_urlconf_points_to_tenant_urls():
    assert settings.ROOT_URLCONF == 'config.urls_tenant', (
        "ROOT_URLCONF must be 'config.urls_tenant' for tenant schema routing"
    )


def test_public_schema_urlconf_points_to_public_urls():
    assert settings.PUBLIC_SCHEMA_URLCONF == 'config.urls_public', (
        "PUBLIC_SCHEMA_URLCONF must be 'config.urls_public' for public schema routing"
    )


def test_urls_public_has_admin_route():
    from config import urls_public
    url_names = [getattr(p, 'pattern', None) for p in urls_public.urlpatterns]
    # Check that at least one pattern corresponds to 'admin/'
    patterns_str = [str(p.pattern) for p in urls_public.urlpatterns]
    assert any('admin' in p for p in patterns_str), (
        "urls_public.py must include the Django Admin route at 'admin/'"
    )


def test_urls_public_has_api_public_route():
    from config import urls_public
    patterns_str = [str(p.pattern) for p in urls_public.urlpatterns]
    assert any('api/public/' in p for p in patterns_str), (
        "urls_public.py must include 'api/public/' route for tenant registration"
    )


def test_urls_public_imports_without_error():
    try:
        from config import urls_public  # noqa: F401
    except ImportError as e:
        assert False, f"urls_public.py failed to import: {e}"


def test_urls_tenant_imports_without_error():
    try:
        from config import urls_tenant  # noqa: F401
    except ImportError as e:
        assert False, f"urls_tenant.py failed to import: {e}"


def test_urls_tenant_has_empty_urlpatterns():
    from config import urls_tenant
    assert isinstance(urls_tenant.urlpatterns, list), (
        "urls_tenant.urlpatterns must be a list (empty for Wave 1)"
    )


def test_tenants_urls_placeholder_exists():
    """apps.tenants.urls must exist as a placeholder for task 3.2."""
    try:
        from apps.tenants import urls  # noqa: F401
    except ImportError as e:
        assert False, f"apps/tenants/urls.py missing: {e}"
