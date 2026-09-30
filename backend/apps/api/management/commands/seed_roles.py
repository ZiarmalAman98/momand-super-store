from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db.models import Q


ROLES = {
    "Super Admin": "*",
    "Admin": "*",
    "Manager": ["mis.view_possale", "mis.add_possale", "mis.view_possalereturn", "mis.add_possalereturn", "mis.view_purchase", "mis.add_purchase", "mis.view_supplier", "mis.add_supplier", "mis.change_supplier", "mis.view_stockmovement", "mis.add_stockmovement", "mis.view_expense", "mis.add_expense", "catalogue.view_product"],
    "Cashier": ["mis.view_possale", "mis.add_possale", "catalogue.view_product"],
    "Inventory Manager": ["mis.view_supplier", "mis.view_stockmovement", "mis.add_stockmovement", "catalogue.view_product", "partner.view_stockrecord"],
    "Sales Manager": ["mis.view_possale", "mis.add_possale", "mis.view_possalereturn", "mis.add_possalereturn", "catalogue.view_product"],
    "Purchase Manager": ["mis.view_purchase", "mis.add_purchase", "mis.view_supplier", "mis.add_supplier", "mis.change_supplier", "mis.view_stockmovement", "mis.add_stockmovement", "catalogue.view_product", "partner.view_stockrecord"],
    "Accountant": ["mis.view_possale", "mis.view_possalereturn", "mis.view_purchase", "mis.view_expense", "mis.add_expense", "mis.view_stockmovement"],
    "Customer": [],
}


class Command(BaseCommand):
    help = "Create the Momand staff/customer groups and assign base model permissions."

    def handle(self, *args, **options):
        all_permissions = Permission.objects.all()
        created = []
        for role, permission_codes in ROLES.items():
            group, _ = Group.objects.get_or_create(name=role)
            if permission_codes == "*":
                if role == "Admin":
                    group.permissions.set(all_permissions.exclude(content_type__app_label="auth"))
                else:
                    group.permissions.set(all_permissions)
            else:
                if permission_codes:
                    requested = []
                    for code in permission_codes:
                        app_label, codename = code.split(".", 1) if "." in code else ("mis", code)
                        requested.append((app_label, codename))
                    filters = Q()
                    for app_label, codename in requested:
                        filters |= Q(content_type__app_label=app_label, codename=codename)
                    group.permissions.set(Permission.objects.filter(filters))
                else:
                    group.permissions.clear()
            created.append(role)
        self.stdout.write(self.style.SUCCESS("Configured groups: " + ", ".join(created)))
