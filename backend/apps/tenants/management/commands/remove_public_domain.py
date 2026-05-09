"""
Management command: remove_public_domain

Removes a domain from the public tenant. Useful for cleaning up
development/staging domains before production deploys, or removing
aliases that are no longer needed.

Refuses to remove the last remaining domain to prevent locking out
the public tenant entirely.

Usage:
    python manage.py remove_public_domain localhost
    python manage.py remove_public_domain staging.sgca.com
"""
from django.core.management.base import BaseCommand, CommandError

from apps.tenants.models import Domain, Tenant


class Command(BaseCommand):
    help = "Remove a domain from the public tenant."

    def add_arguments(self, parser):
        parser.add_argument(
            "domain",
            help="Domain name to remove (e.g. localhost, staging.sgca.com).",
        )

    def handle(self, *args, **options):
        domain_name = options["domain"].strip().lower()

        try:
            tenant = Tenant.objects.get(schema_name="public")
        except Tenant.DoesNotExist:
            raise CommandError("Public tenant does not exist.")

        try:
            domain = Domain.objects.get(domain=domain_name, tenant=tenant)
        except Domain.DoesNotExist:
            raise CommandError(
                f"Domain '{domain_name}' is not registered for the public tenant."
            )

        remaining = Domain.objects.filter(tenant=tenant).count()
        if remaining <= 1:
            raise CommandError(
                f"Cannot remove '{domain_name}' — it is the only domain for the public tenant. "
                "Add another domain first."
            )

        domain.delete()
        self.stdout.write(self.style.SUCCESS(f"Domain '{domain_name}' removed."))

        self.stdout.write(
            f"\nPublic tenant domains:\n"
            + "\n".join(
                f"  {'*' if d.is_primary else ' '} {d.domain}"
                for d in Domain.objects.filter(tenant=tenant).order_by("-is_primary", "domain")
            )
        )
