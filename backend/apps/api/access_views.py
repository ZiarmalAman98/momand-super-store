from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


PERMISSIONS = [
    ("mis.view_possale", "POS: view sales / print receipts"),
    ("mis.add_possale", "POS: create sales"),
    ("mis.change_possale", "POS: edit/manage sales"),
    ("mis.delete_possale", "POS: delete sales"),
    ("mis.view_possalereturn", "POS: view returns"),
    ("mis.add_possalereturn", "POS: process returns"),
    ("mis.view_cashiershift", "POS: view cashier shift"),
    ("mis.change_cashiershift", "POS: close cashier shift"),
    ("mis.view_stockmovement", "Inventory: view stock"),
    ("mis.add_stockmovement", "Inventory: adjust stock"),
    ("mis.view_purchase", "Purchases: view"),
    ("mis.add_purchase", "Purchases: receive"),
    ("mis.view_supplier", "Suppliers: view"),
    ("mis.add_supplier", "Suppliers: add"),
    ("mis.change_supplier", "Suppliers: edit"),
    ("mis.delete_supplier", "Suppliers: delete"),
    ("mis.view_expense", "Expenses: view"),
    ("mis.add_expense", "Expenses: add"),
    ("mis.change_expense", "Expenses: edit"),
    ("mis.delete_expense", "Expenses: delete"),
    ("mis.view_paymenttransaction", "Payments: view"),
    ("catalogue.view_product", "Products: view"),
    ("catalogue.add_product", "Products: add"),
    ("catalogue.change_product", "Products: edit"),
    ("catalogue.delete_product", "Products: delete"),
    ("auth.view_user", "Users: view"),
    ("auth.add_user", "Users: create"),
    ("auth.change_user", "Users: edit/disable"),
]

MENU_RULES = {
    "admin_panel": ("mis.view_stockmovement", "mis.view_purchase", "mis.view_supplier", "mis.view_expense", "auth.view_user"),
    "dashboard": ("mis.view_possale", "mis.view_purchase", "mis.view_expense", "mis.view_stockmovement"),
    "pos": ("mis.add_possale", "mis.view_possale"),
    "inventory": ("mis.view_stockmovement",),
    "purchases": ("mis.view_purchase",),
    "suppliers": ("mis.view_supplier",),
    "expenses": ("mis.view_expense",),
    "sales": ("mis.view_possale",),
    "reports": ("mis.view_possale", "mis.view_purchase", "mis.view_expense"),
    "customers": ("auth.view_user",),
    "payments": ("mis.view_paymenttransaction",),
    "users": ("auth.view_user", "auth.add_user", "auth.change_user"),
}


def can_manage_users(user):
    return user.is_authenticated and user.is_staff and (
        user.is_superuser or user.has_perm("auth.view_user")
    )


def permission_codes(user):
    if user.is_superuser:
        return {code for code, _ in PERMISSIONS} | {"auth.view_user", "auth.add_user", "auth.change_user"}
    return set(user.get_all_permissions())


class AccessView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        perms = permission_codes(request.user)
        return Response({
            "permissions": sorted(perms),
            "menus": {
                key: any(code in perms for code in codes)
                for key, codes in MENU_RULES.items()
            },
        })


class UserManagementView(APIView):
    permission_classes = (IsAuthenticated,)

    def _check(self, request, action="view"):
        if not can_manage_users(request.user):
            return Response({"detail": "You do not have permission to manage users."}, status=403)
        required = f"auth.{action}_user"
        if not request.user.is_superuser and not request.user.has_perm(required):
            return Response({"detail": f"Missing permission: {required}"}, status=403)
        return None

    def get(self, request):
        denied = self._check(request, "view")
        if denied:
            return denied
        User = get_user_model()
        rows = []
        for user in User.objects.prefetch_related("groups", "user_permissions").order_by("email"):
            rows.append({
                "id": user.pk,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": user.is_active,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "groups": list(user.groups.values_list("name", flat=True)),
                "permissions": sorted(user.get_all_permissions()),
            })
        return Response({"results": rows, "available_permissions": [
            {"code": code, "label": label} for code, label in PERMISSIONS
        ]})

    @transaction.atomic
    def post(self, request):
        denied = self._check(request, "add")
        if denied:
            return denied
        User = get_user_model()
        email = str(request.data.get("email", "")).strip().lower()
        password = str(request.data.get("password", ""))
        if not email or "@" not in email:
            return Response({"email": "A valid email is required."}, status=400)
        if len(password) < 8:
            return Response({"password": "Password must contain at least 8 characters."}, status=400)
        if User.objects.filter(email__iexact=email).exists():
            return Response({"email": "A user with this email already exists."}, status=400)

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=str(request.data.get("first_name", "")).strip()[:150],
            last_name=str(request.data.get("last_name", "")).strip()[:150],
        )
        user.is_staff = True
        user.is_active = bool(request.data.get("is_active", True))
        user.save(update_fields=["is_staff", "is_active"])
        codes = {code for code, _ in PERMISSIONS}
        selected = [code for code in request.data.get("permissions", []) if code in codes]
        if not request.user.is_superuser:
            allowed = set(request.user.get_all_permissions())
            selected = [code for code in selected if code in allowed]
        perms = Permission.objects.filter(content_type__app_label__in=("mis", "catalogue", "auth"), content_type__model__isnull=False, codename__in=[c.split(".", 1)[1] for c in selected])
        perms = [p for p in perms if f"{p.content_type.app_label}.{p.codename}" in selected]
        user.user_permissions.set(perms)
        return Response({"id": user.pk, "email": user.email}, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def patch(self, request, pk):
        denied = self._check(request, "change")
        if denied:
            return denied
        User = get_user_model()
        user = User.objects.filter(pk=pk).first()
        if not user:
            return Response({"detail": "User not found."}, status=404)
        if user.is_superuser and not request.user.is_superuser:
            return Response({"detail": "Only the owner can change a superuser."}, status=403)
        if "is_active" in request.data:
            user.is_active = bool(request.data["is_active"])
        if "first_name" in request.data:
            user.first_name = str(request.data["first_name"]).strip()[:150]
        if "last_name" in request.data:
            user.last_name = str(request.data["last_name"]).strip()[:150]
        if request.data.get("password"):
            password = str(request.data["password"])
            if len(password) < 8:
                return Response({"password": "Password must contain at least 8 characters."}, status=400)
            user.set_password(password)
        user.save()
        if "permissions" in request.data and not user.is_superuser:
            codes = {code for code, _ in PERMISSIONS}
            selected = [code for code in request.data.get("permissions", []) if code in codes]
            if not request.user.is_superuser:
                allowed = set(request.user.get_all_permissions())
                selected = [code for code in selected if code in allowed]
            perms = Permission.objects.filter(content_type__app_label__in=("mis", "catalogue", "auth"), codename__in=[c.split(".", 1)[1] for c in selected])
            perms = [p for p in perms if f"{p.content_type.app_label}.{p.codename}" in selected]
            user.user_permissions.set(perms)
        return Response({"id": user.pk, "email": user.email, "is_active": user.is_active})
