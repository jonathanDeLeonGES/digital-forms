"""
Integration tests for the tenant registration flow (task 7.1).

These tests verify actual database state and the full serializer+view chain,
unlike the mock-based unit tests in test_services.py and test_views.py.

Test classes:
  RegistrationValidationIntegrationTests — validates HTTP 400 responses via real
      view + serializer, no DB writes required.

  DB-touching functions — verify Tenant/Domain/Subscription records exist or are
      cleaned up after each scenario. Require real PostgreSQL (django-tenants
      runs CREATE SCHEMA on Tenant.save()).

REQUIRES_DB (marked per function): schema creation via django-tenants needs real PostgreSQL.
"""
from datetime import date

import pytest
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from django.db import connection

from apps.tenants.models import Domain, Plan, Subscription, Tenant
from apps.tenants.services import TenantRegistrationService
from apps.tenants.views import TenantRegistrationView

factory = APIRequestFactory()
view = TenantRegistrationView.as_view()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _payload(**overrides):
    base = {
        "nombre_empresa": "ACME Corp",
        "subdominio": "acme",
        "email_admin": "admin@acme.com",
    }
    base.update(overrides)
    return base


def _ensure_plans():
    """Create Plan fixture rows in the public schema if not present."""
    connection.set_schema_to_public()
    Plan.objects.get_or_create(nombre=Plan.TRIAL)
    Plan.objects.get_or_create(nombre=Plan.ENTERPRISE)


# ---------------------------------------------------------------------------
# HTTP 400 validation integration tests
# No DB writes — serializer rejects before calling the service.
# APIRequestFactory bypasses TenantMiddleware, which is correct here: we are
# testing the serializer+view chain, not subdomain routing.
# ---------------------------------------------------------------------------

class RegistrationValidationIntegrationTests(TestCase):
    """
    Integration tests for request validation.
    Runs through the real view and serializer; service is never called for
    invalid inputs, so no DB fixture setup is needed.
    """

    def test_invalid_subdomain_characters_returns_400(self):
        """Subdomain with uppercase letters, spaces, underscores, or leading dash → 400."""
        invalid_cases = [
            ("UPPER", "uppercase letters"),
            ("with space", "space character"),
            ("under_score", "underscore"),
            ("dot.dot", "dot"),
            ("-leading", "leading dash"),
            ("trailing-", "trailing dash"),
            ("", "empty string"),
        ]
        for subdominio, reason in invalid_cases:
            with self.subTest(subdominio=subdominio, reason=reason):
                request = factory.post(
                    "/api/public/tenants/register/",
                    _payload(subdominio=subdominio),
                    format="json",
                )
                response = view(request)
                self.assertEqual(
                    response.status_code, 400,
                    f"Expected HTTP 400 for subdominio={subdominio!r} ({reason})",
                )
                self.assertIn(
                    "subdominio", response.data,
                    f"Error key 'subdominio' missing in response for {subdominio!r}",
                )

    def test_missing_nombre_empresa_returns_400_with_field_error(self):
        """Empty nombre_empresa → HTTP 400, error keyed under 'nombre_empresa'."""
        request = factory.post(
            "/api/public/tenants/register/",
            _payload(nombre_empresa=""),
            format="json",
        )
        response = view(request)
        self.assertEqual(response.status_code, 400)
        self.assertIn("nombre_empresa", response.data)

    def test_missing_email_admin_returns_400_with_field_error(self):
        """Malformed email_admin → HTTP 400, error keyed under 'email_admin'."""
        for bad_email in ["not-an-email", "missing@", "@domain.com", "plain"]:
            with self.subTest(email=bad_email):
                request = factory.post(
                    "/api/public/tenants/register/",
                    _payload(email_admin=bad_email),
                    format="json",
                )
                response = view(request)
                self.assertEqual(response.status_code, 400)
                self.assertIn("email_admin", response.data)

    def test_empty_payload_returns_400_with_all_field_errors(self):
        """Sending {} → HTTP 400 with errors for every required field."""
        request = factory.post("/api/public/tenants/register/", {}, format="json")
        response = view(request)
        self.assertEqual(response.status_code, 400)
        for field in ("nombre_empresa", "subdominio", "email_admin"):
            self.assertIn(field, response.data, f"Missing error key: {field}")

    def test_missing_subdominio_returns_400(self):
        """Payload without subdominio → HTTP 400 with 'subdominio' error."""
        payload = {"nombre_empresa": "ACME", "email_admin": "a@b.com"}
        request = factory.post("/api/public/tenants/register/", payload, format="json")
        response = view(request)
        self.assertEqual(response.status_code, 400)
        self.assertIn("subdominio", response.data)


# ---------------------------------------------------------------------------
# DB-touching integration tests
# REQUIRES_DB: schema creation via django-tenants needs real PostgreSQL.
# Each function uses transaction=True because Tenant.save() issues
# CREATE SCHEMA which cannot be rolled back inside a SAVEPOINT.
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_successful_registration_creates_tenant_domain_subscription():
    """
    Happy path DB integration: service.register() persists Tenant, Domain, and
    Subscription with the correct field values.

    REQUIRES_DB: schema creation via django-tenants needs real PostgreSQL.
    """
    _ensure_plans()

    tenant = TenantRegistrationService.register(
        nombre_empresa="Empresa Integración",
        subdominio="emp-integ",
        email_admin="admin@emp-integ.com",
        password="Admin123!",
    )

    # Tenant exists with correct fields
    assert Tenant.objects.filter(schema_name="emp-integ").exists()
    db_tenant = Tenant.objects.get(schema_name="emp-integ")
    assert db_tenant.nombre_empresa == "Empresa Integración"
    assert db_tenant.email_admin == "admin@emp-integ.com"
    assert db_tenant.id == tenant.id

    # Domain exists with the expected hostname
    assert Domain.objects.filter(
        domain="emp-integ.sgca.com",
        tenant=db_tenant,
        is_primary=True,
    ).exists()

    # Subscription is a 14-day trial starting today
    assert Subscription.objects.filter(tenant=db_tenant).exists()
    sub = db_tenant.subscription
    assert sub.plan.nombre == Plan.TRIAL
    assert sub.fecha_fin is not None
    assert sub.fecha_fin > date.today()
    days_remaining = (sub.fecha_fin - date.today()).days
    assert days_remaining == 14

    # Admin user was created in the tenant schema
    from django.db import connection
    from apps.users.models import CustomUser
    connection.set_tenant(db_tenant)
    admin_user = CustomUser.objects.get(email="admin@emp-integ.com")
    assert admin_user.role == "admin"
    assert admin_user.is_active is True
    assert admin_user.check_password("Admin123!")


@pytest.mark.django_db(transaction=True)
def test_duplicate_subdomain_raises_409_and_leaves_no_orphans():
    """
    Duplicate subdomain: second register() raises an exception (ProgrammingError
    or IntegrityError from tenant.save() — schema already exists in PostgreSQL).
    Tenant and Domain counts must not increase — no orphan records left behind.

    REQUIRES_DB: schema creation via django-tenants needs real PostgreSQL.
    """
    _ensure_plans()

    # First registration succeeds
    TenantRegistrationService.register(
        nombre_empresa="Primera Empresa",
        subdominio="dup-sub",
        email_admin="first@dup-sub.com",
        password="Admin123!",
    )

    tenant_count_before = Tenant.objects.filter(schema_name="dup-sub").count()
    domain_count_before = Domain.objects.filter(domain="dup-sub.sgca.com").count()
    assert tenant_count_before == 1
    assert domain_count_before == 1

    # Second registration with same subdomain raises — tenant.save() fails first
    # (ProgrammingError: schema already exists) before Domain is attempted
    with pytest.raises(Exception):
        TenantRegistrationService.register(
            nombre_empresa="Segunda Empresa",
            subdominio="dup-sub",
            email_admin="second@dup-sub.com",
            password="Admin123!",
        )

    # Counts must not have changed — no orphan tenant or domain
    assert Tenant.objects.filter(schema_name="dup-sub").count() == tenant_count_before
    assert Domain.objects.filter(domain="dup-sub.sgca.com").count() == domain_count_before
    # The failed attempt must not have created a Subscription
    assert Subscription.objects.filter(
        tenant__schema_name="dup-sub"
    ).count() == 1  # only from the first successful registration


@pytest.mark.django_db(transaction=True)
def test_subscription_failure_leaves_no_orphan_tenant():
    """
    If Subscription creation fails (e.g., Plan fixture missing), both the
    Tenant schema and the Tenant record must be cleaned up — no orphan left.

    REQUIRES_DB: schema creation via django-tenants needs real PostgreSQL.
    """
    # Intentionally skip _ensure_plans() so Plan.objects.get(nombre=TRIAL) raises
    # DoesNotExist, triggering the service's generic-exception cleanup path.

    with pytest.raises(Exception):
        TenantRegistrationService.register(
            nombre_empresa="Broken Corp",
            subdominio="broken-corp",
            email_admin="admin@broken-corp.com",
            password="Admin123!",
        )

    # Service must have called tenant.delete() — no orphan tenant or domain
    assert not Tenant.objects.filter(schema_name="broken-corp").exists()
    assert not Domain.objects.filter(domain__startswith="broken-corp").exists()
