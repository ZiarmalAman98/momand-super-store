from django.core.exceptions import PermissionDenied


class RestrictDjangoAdminMiddleware:
    """Keep the legacy Django admin out of limited staff accounts."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/admin/") and request.user.is_authenticated:
            user = request.user
            has_admin_role = user.groups.filter(name__in=("Admin", "Super Admin")).exists()
            if user.is_staff and not (user.is_superuser or has_admin_role):
                raise PermissionDenied
        return self.get_response(request)
