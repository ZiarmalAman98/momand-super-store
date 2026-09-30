from rest_framework.permissions import BasePermission, SAFE_METHODS


class HasMISPermission(BasePermission):
    """Check Django's per-model permission assigned to staff groups."""

    def has_permission(self, request, view):
        permission = getattr(view, "required_permission", None)
        user = request.user
        return bool(user and user.is_authenticated and user.is_staff and permission and user.has_perm(permission))


class HasAnyMISPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        permissions = getattr(view, "required_permissions", ())
        return bool(user and user.is_authenticated and user.is_staff and any(user.has_perm(code) for code in permissions))


class StaffWriteCustomerReadOnly(BasePermission):
    """Expose catalogue data publicly; reserve write operations for staff."""

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or bool(
            request.user and request.user.is_staff
        )
