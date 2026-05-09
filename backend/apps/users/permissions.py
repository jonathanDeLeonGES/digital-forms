from rest_framework.permissions import BasePermission


class RequireRole(BasePermission):
    """
    Usage in Wave 2+:
        permission_classes = [IsAuthenticated, RequireRole('admin', 'supervisor')]
    """
    def __init__(self, *roles: str):
        self.roles = roles

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in self.roles
        )


class IsAdminTenant(BasePermission):
    """Shortcut: only the 'admin' role."""
    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'admin'
        )
