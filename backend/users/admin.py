from django.contrib import admin
from django.contrib.auth.models import User

from .models import Follow


class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "first_name", "last_name")
    list_filter = ("username", "email")


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("user", "author")
    empty_value_display = "Нет записей"


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
