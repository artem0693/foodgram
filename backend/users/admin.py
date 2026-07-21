"""Настройка админ-панели для приложения users."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Follow, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Настройка отображения пользователей в админ-панели."""

    list_display = ("email", "username", "first_name", "last_name", "is_staff")
    search_fields = ("email", "username")
    list_filter = ("email", "username")


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    """Настройка отображения подписок в админ-панели."""

    list_display = ("user", "author")
    search_fields = ("user__username", "author__username")
