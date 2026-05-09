import logging

from django.db import connection

from .exceptions import EmailAlreadyExistsError, LicenseLimitExceededError, UserNotFoundError
from .models import CustomUser

logger = logging.getLogger(__name__)


class UserManagementService:

    def create_user(
        self,
        nombre_completo: str,
        email: str,
        password: str,
        role: str,
        tenant,
    ) -> CustomUser:
        self._check_license_limit(tenant)
        if CustomUser.objects.filter(email=email).exists():
            raise EmailAlreadyExistsError(f"El email '{email}' ya está en uso.")
        user = CustomUser(
            nombre_completo=nombre_completo,
            email=email,
            role=role,
        )
        user.set_password(password)
        user.save()
        return user

    def update_user(
        self,
        user_id: int,
        nombre_completo: str | None = None,
        email: str | None = None,
        role: str | None = None,
    ) -> CustomUser:
        try:
            user = CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            raise UserNotFoundError(f"Usuario {user_id} no encontrado.")
        if email is not None and CustomUser.objects.exclude(pk=user_id).filter(email=email).exists():
            raise EmailAlreadyExistsError(f"El email '{email}' ya está en uso.")
        if nombre_completo is not None:
            user.nombre_completo = nombre_completo
        if email is not None:
            user.email = email
        if role is not None:
            user.role = role
        user.save()
        return user

    def deactivate_user(self, user_id: int) -> CustomUser:
        try:
            user = CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            raise UserNotFoundError(f"Usuario {user_id} no encontrado.")
        user.is_active = False
        user.save()
        return user

    def _check_license_limit(self, tenant) -> None:
        """
        Reads Subscription from the public schema, then restores tenant schema.
        Raises LicenseLimitExceededError if Enterprise plan is at capacity.
        """
        connection.set_schema_to_public()
        try:
            from apps.tenants.models import Subscription
            try:
                sub = Subscription.objects.select_related('plan').get(tenant=tenant)
            except Subscription.DoesNotExist:
                return
            if sub.plan.nombre != 'enterprise':
                return
            if sub.num_licencias is None:
                return
            num_licencias = sub.num_licencias
        finally:
            # Always restore the tenant schema before returning
            connection.set_tenant(tenant)

        active_count = CustomUser.objects.filter(is_active=True).count()
        if active_count >= num_licencias:
            logger.warning(
                "License limit reached for tenant %s: %d/%d",
                tenant.schema_name, active_count, num_licencias,
            )
            raise LicenseLimitExceededError(
                "Se alcanzó el límite de licencias para este tenant."
            )
