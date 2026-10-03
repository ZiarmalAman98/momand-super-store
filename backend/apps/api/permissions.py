from rest_framework.permissions import BasePermission, SAFE_METHODS


ROLE_ADDITIONAL_PERMISSIONS = {
    "Manager": {"order.view_order", "mis.view_paymenttransaction", "mis.change_paymenttransaction"},
    "Accountant": {"order.view_order", "mis.view_paymenttransaction", "mis.change_paymenttransaction"},
}


def effective_staff_permissions(user):
    """Return assigned permissions plus the fixed baseline of a Cashier role."""
    permissions = set(user.get_all_permissions())
    group_names = set(user.groups.values_list("name", flat=True))
    for group_name, additions in ROLE_ADDITIONAL_PERMISSIONS.items():
        if group_name in group_names:
            permissions.update(additions)
    if "Cashier" in group_names:
        permissions.update({"catalogue.view_product", "mis.add_possale", "mis.view_possale"})
    return sorted(permissions)


class HasMISPermission(BasePermission):
    """Check Django's per-model permission assigned to staff groups."""

    def has_permission(self, request, view):
        permission = getattr(view, "required_permission", None)
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_staff
            and permission
            and (permission in effective_staff_permissions(user) or user.groups.filter(name__in=("Admin", "Super Admin")).exists())
        )


class HasAnyMISPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        permissions = getattr(view, "required_permissions", ())
        return bool(
            user
            and user.is_authenticated
            and user.is_staff
            and any(user.has_perm(code) for code in permissions)
        )


class StaffWriteCustomerReadOnly(BasePermission):
    """Public catalogue reads; catalogue writes require explicit Django perms."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        if not user or not user.is_authenticated or not user.is_staff:
            return False
        action_permissions = {
            "POST": "catalogue.add_product",
            "PUT": "catalogue.change_product",
            "PATCH": "catalogue.change_product",
            "DELETE": "catalogue.delete_product",
        }
        permission = action_permissions.get(request.method)
        return bool(permission and user.has_perm(permission))
