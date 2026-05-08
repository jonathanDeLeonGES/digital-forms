# Compatibility shim — django-tenants uses PUBLIC_SCHEMA_URLCONF and ROOT_URLCONF.
# This file is kept for tooling that expects a urls.py at the config root.
from config.urls_tenant import urlpatterns  # noqa: F401
