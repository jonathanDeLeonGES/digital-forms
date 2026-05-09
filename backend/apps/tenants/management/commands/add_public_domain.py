"""
Management command: add_public_domain

Registers a domain name for the public tenant so that
TenantMainMiddleware can route requests on that hostname to the public
schema (tenant registration, admin panel, etc.).

Idempotent — safe to run multiple times and in CI/CD pipelines.

Usage:
    python manage.py add_public_domain sgca.com
    python manage.py add_public_domain sgca.com --primary
    python manage.py add_public_domain www.sgca.com  # secondary alias
"""
from django.core.management.base import BaseCommand, CommandError

from apps.tenants.models import Domain, Tenant


class Command(BaseCommand):
    help = "Add a domain for the public tenant (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "domain",
            help="Domain name to register (e.g. sgca.com, staging.sgca.com).",
        )
        parser.add_argument(
            "--primary",
            action="store_true",
            default=False,
            help="Mark this domain as the primary domain for the public tenant.",
        )

    def handle(self, *args, **options):
        domain_name = options["domain"].strip().lower()
        is_primary = options["primary"]

        if not domain_name:
            raise CommandError("Domain name cannot be empty.")

        # Ensure the public tenant exists (created by migration 0002, but
        # guard here so the command works even on a fresh DB with no migrations).
        tenant, tenant_created = Tenant.objects.get_or_create(
            schema_name="public",
            defaults={
                "nombre_empresa": "SGCA Platform",
                "email_admin": "system@sgca.com",
            },
        )
        if tenant_created:
            self.stdout.write(self.style.WARNING("Public tenant did not exist — created it."))

        domain, domain_created = Domain.objects.get_or_create(
            domain=domain_name,
            defaults={"tenant": tenant, "is_primary": is_primary},
        )

        if domain_created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Domain '{domain_name}' added for the public tenant"
                    + (" (primary)" if is_primary else "") + "."
                )
            )
        else:
            if domain.tenant != tenant:
                raise CommandError(
                    f"Domain '{domain_name}' already exists but belongs to tenant "
                    f"'{domain.tenant.schema_name}', not the public tenant."
                )
            self.stdout.write(
                self.style.WARNING(f"Domain '{domain_name}' already registered — nothing changed.")
            )

        if is_primary and not domain_created:
            # Update is_primary if explicitly requested and domain already existed
            if not domain.is_primary:
                domain.is_primary = True
                domain.save(update_fields=["is_primary"])
                self.stdout.write(self.style.SUCCESS(f"Domain '{domain_name}' marked as primary."))

        self.stdout.write(
            f"\nPublic tenant domains:\n"
            + "\n".join(
                f"  {'*' if d.is_primary else ' '} {d.domain}"
                for d in Domain.objects.filter(tenant=tenant).order_by("-is_primary", "domain")
            )
        )
