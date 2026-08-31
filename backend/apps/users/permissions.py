from rest_framework.permissions import BasePermission


def RequireRole(*roles: str):
    """
    Factory that returns a permission class restricted to the given roles.
    Usage: permission_classes = [IsAuthenticated, RequireRole('admin', 'supervisor')]
    """
    class _RequireRole(BasePermission):
        def has_permission(self, request, view) -> bool:
            return bool(
                request.user
                and request.user.is_authenticated
                and request.user.role in roles
            )
    return _RequireRole


class IsAdminTenant(BasePermission):
    """Shortcut: only the 'admin' role."""
    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'admin'
        )
