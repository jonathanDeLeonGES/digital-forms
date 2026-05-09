from datetime import date, timedelta

from django.db import IntegrityError, transaction

from .exceptions import SubdomainAlreadyExistsError
from .models import Domain, Plan, Subscription, Tenant


class TenantRegistrationService:
    TRIAL_DAYS = 14

    @classmethod
    def register(cls, nombre_empresa: str, subdominio: str, email_admin: str) -> Tenant:
        """
        Creates Tenant (+ PostgreSQL schema), Domain, and trial Subscription atomically.
        Cleans up (tenant.delete() drops schema) on any failure — no orphans left.
        Raises SubdomainAlreadyExistsError if the subdomain is already taken.
        """
        tenant = Tenant(
            schema_name=subdominio,
            nombre_empresa=nombre_empresa,
            email_admin=email_admin,
        )
        # transaction.atomic() crea un savepoint: si el INSERT falla por
        # schema_name duplicado, sólo el savepoint se revierte y la transacción
        # externa queda válida (importante en tests con TestCase).
        try:
            with transaction.atomic():
                tenant.save()  # auto_create_schema=True → PostgreSQL schema created here
        except IntegrityError:
            raise SubdomainAlreadyExistsError(
                f"El subdominio '{subdominio}' ya está registrado."
            )

        try:
            domain = Domain(
                domain=f"{subdominio}.sgca.com",
                tenant=tenant,
                is_primary=True,
            )
            try:
                domain.save()
            except IntegrityError:
                tenant.delete()  # auto_drop_schema=True → schema removed
                raise SubdomainAlreadyExistsError(
                    f"El subdominio '{subdominio}' ya está registrado."
                )

            trial_plan = Plan.objects.get(nombre=Plan.TRIAL)
            Subscription.objects.create(
                tenant=tenant,
                plan=trial_plan,
                fecha_fin=date.today() + timedelta(days=cls.TRIAL_DAYS),
            )
        except SubdomainAlreadyExistsError:
            raise
        except Exception:
            tenant.delete()
            raise

        return tenant
