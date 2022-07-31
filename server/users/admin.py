from django.contrib import admin
from django.contrib.auth.models import Group, Permission

from users.models import User, UserType


class UserAdmin(admin.ModelAdmin):
    """
    A class used for django admin representation of Users model

    Methods
    -------
    save_model(request, obj, form, change)
        assigning carpet owners to CarpetOwner group (creating this group if not added before) for access control
    """

    list_display = ("first_name", "last_name", "id", "user_type")
    list_display_links = ("id", "last_name", "first_name")
    search_fields = ("first_name", "last_name")

    def save_model(self, request, obj, form, change) -> None:
        if obj.user_type == UserType.carpet_cleaning_owner:
            obj.is_staff = True
            group = Group.objects.filter(name="CarpetOwners")
            if len(group) == 0:
                group = UserAdmin.createCarpetOwnersGroup()
            else:
                group = group.first()

        return super().save_model(request, obj, form, change)

    @staticmethod
    def createCarpetOwnersGroup():
        permissions = Permission.objects.filter(
            content_type__model__contains="order")
        group = Group.objects.create(name="CarpetOwners")
        group.permissions.set(permissions)
        return group


admin.site.register(User, UserAdmin)
