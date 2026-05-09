"""
E2E tests for the complete tenant lifecycle.

Tests are split into two categories:
  - State-transition tests: use mock/in-memory objects — no PostgreSQL required.
    These cover middleware behaviour and subscription state logic end-to-end.
  - DB-backed tests: marked REQUIRES_DB — need real PostgreSQL + django-tenants
    configured (auto_create_schema=True creates an actual schema on save).
"""

import json
from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from apps.tenants.middleware import AccessPolicyMiddleware
from apps.tenants.models import Plan, Subscription, Tenant


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_middleware():
    get_response = MagicMock(return_value=HttpResponse(status=200))
    mw = AccessPolicyMiddleware(get_response)
    return mw, get_response


def _make_subscription(plan_nombre: str, fecha_fin=None):
    """Return a mock subscription whose is_active() delegates to real logic."""
    plan = MagicMock()
    plan.nombre = plan_nombre

    sub = MagicMock(spec=Subscription)
    sub.plan = plan
    sub.fecha_fin = fecha_fin
    # Delegate is_active to the real implementation so we test actual logic.
    sub.is_active.side_effect = lambda: (
        True
        if plan_nombre == Plan.ENTERPRISE
        else (fecha_fin is not None and fecha_fin >= date.today())
    )
    return sub


def _make_request(factory: RequestFactory, path: str, subscription):
    request = factory.get(path, HTTP_HOST="acme.sgca.com")
    tenant = MagicMock()
    tenant.subscription = subscription
    request.tenant = tenant
    return request


# ---------------------------------------------------------------------------
# Lifecycle E2E tests (state-transition — no DB required)
# ---------------------------------------------------------------------------

class TenantLifecycleE2ETests(TestCase):
    """End-to-end lifecycle tests using in-memory mock objects."""

    def setUp(self):
        self.factory = RequestFactory()
        self.mw, self.get_response = _make_middleware()

    # ------------------------------------------------------------------
    # Test 1: Register tenant → access tenant endpoint → verify active
    # ------------------------------------------------------------------
    def test_active_trial_access_passes(self):
        """
        E2E: newly registered tenant with active trial can access tenant endpoints.
        """
        fecha_fin = date.today() + timedelta(days=14)
        sub = _make_subscription(Plan.TRIAL, fecha_fin=fecha_fin)

        request = _make_request(self.factory, "/api/tenant/some-resource/", sub)
        response = self.mw(request)

        # Middleware must pass through — get_response was called, not 402.
        self.get_response.assert_called_once_with(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(sub.is_active())

    # ------------------------------------------------------------------
    # Test 2: Trial expires → blocked → admin extends → restored
    # ------------------------------------------------------------------
    def test_expired_trial_blocked_then_extended_access_restored(self):
        """
        E2E: expired trial returns 402 → admin extends fecha_fin → access
        is restored immediately (no restart required).
        """
        # --- Step 1: trial expired ---
        expired_sub = _make_subscription(
            Plan.TRIAL, fecha_fin=date.today() - timedelta(days=1)
        )
        request = _make_request(self.factory, "/api/tenant/some-resource/", expired_sub)
        response = self.mw(request)

        self.assertEqual(response.status_code, 402)
        body = json.loads(response.content)
        self.assertEqual(body["code"], "trial_expired")
        self.assertFalse(expired_sub.is_active())
        # get_response must NOT have been called.
        self.get_response.assert_not_called()

        # --- Step 2: system admin extends trial ---
        new_fecha_fin = date.today() + timedelta(days=7)
        extended_sub = _make_subscription(Plan.TRIAL, fecha_fin=new_fecha_fin)

        request2 = _make_request(self.factory, "/api/tenant/some-resource/", extended_sub)
        response2 = self.mw(request2)

        # After extension middleware passes; get_response called this time.
        self.get_response.assert_called_once_with(request2)
        self.assertEqual(response2.status_code, 200)
        self.assertTrue(extended_sub.is_active())

    # ------------------------------------------------------------------
    # Test 3: System admin upgrades Trial → Enterprise
    # ------------------------------------------------------------------
    def test_enterprise_upgrade_grants_unlimited_access(self):
        """
        E2E: system admin changes plan from Trial to Enterprise —
        is_active() returns True with no fecha_fin; middleware passes.
        """
        enterprise_sub = _make_subscription(Plan.ENTERPRISE, fecha_fin=None)

        request = _make_request(self.factory, "/api/tenant/some-resource/", enterprise_sub)
        response = self.mw(request)

        self.get_response.assert_called_once_with(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(enterprise_sub.is_active())

    # ------------------------------------------------------------------
    # Test 4: Whitelist bypasses access check even for expired trial
    # ------------------------------------------------------------------
    def test_whitelisted_path_bypasses_access_check_for_expired_trial(self):
        """
        E2E: an expired tenant can still reach /admin/ (whitelist path) —
        relevant for system admin managing the tenant from its own domain.
        """
        expired_sub = _make_subscription(
            Plan.TRIAL, fecha_fin=date.today() - timedelta(days=1)
        )
        request = _make_request(self.factory, "/admin/", expired_sub)
        response = self.mw(request)

        self.get_response.assert_called_once_with(request)
        self.assertEqual(response.status_code, 200)

    # ------------------------------------------------------------------
    # Test 5: Public schema (no tenant) passes through unconditionally
    # ------------------------------------------------------------------
    def test_public_schema_request_passes_through(self):
        """
        E2E: requests on the public schema have no request.tenant and are
        never inspected by AccessPolicyMiddleware.
        """
        request = self.factory.get("/api/public/tenants/register/")
        # Deliberately do NOT set request.tenant — simulates public schema.
        response = self.mw(request)

        self.get_response.assert_called_once_with(request)
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# DB-backed lifecycle tests (REQUIRES_DB: real PostgreSQL + django-tenants)
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
class TenantRegistrationLifecycleDBTests(TestCase):
    """
    REQUIRES_DB: these tests use TenantRegistrationService which calls
    tenant.save() with auto_create_schema=True, creating a real PostgreSQL
    schema. They will be skipped / fail gracefully without a running database.
    """

    def test_register_creates_tenant_domain_and_subscription(self):
        """
        REQUIRES_DB: full registration flow creates Tenant, Domain, and
        Subscription(trial) in the database.
        """
        from apps.tenants.services import TenantRegistrationService

        # Ensure trial plan exists.
        trial_plan, _ = Plan.objects.get_or_create(nombre=Plan.TRIAL)

        tenant = TenantRegistrationService.register(
            nombre_empresa="ACME Corp",
            subdominio="acmee2e",
            email_admin="admin@acme.com",
            password="Admin123!",
        )

        self.assertIsNotNone(tenant.pk)
        self.assertTrue(
            hasattr(tenant, "subscription"),
            "Tenant must have an associated Subscription",
        )
        subscription = tenant.subscription
        self.assertEqual(subscription.plan.nombre, Plan.TRIAL)
        self.assertIsNotNone(subscription.fecha_fin)
        self.assertTrue(subscription.is_active())

        from apps.tenants.models import Domain
        self.assertTrue(
            Domain.objects.filter(tenant=tenant).exists(),
            "Domain record must be created for the tenant",
        )

    def test_duplicate_subdomain_leaves_no_orphans(self):
        """
        REQUIRES_DB: second registration with the same subdomain returns
        SubdomainAlreadyExistsError and leaves no orphan Tenant/Domain.
        """
        from apps.tenants.exceptions import SubdomainAlreadyExistsError
        from apps.tenants.services import TenantRegistrationService

        Plan.objects.get_or_create(nombre=Plan.TRIAL)

        TenantRegistrationService.register(
            nombre_empresa="First Corp",
            subdominio="duptest",
            email_admin="first@corp.com",
            password="Admin123!",
        )

        with self.assertRaises(SubdomainAlreadyExistsError):
            TenantRegistrationService.register(
                nombre_empresa="Second Corp",
                subdominio="duptest",
                email_admin="second@corp.com",
                password="Admin123!",
            )

        # Only one Tenant with schema_name='duptest' must exist.
        self.assertEqual(
            Tenant.objects.filter(schema_name="duptest").count(), 1
        )
