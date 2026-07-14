"""Настройка админ-панели для приложения users."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Follow

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'email', 
        'username', 
        'first_name', 
        'last_name', 
        'is_staff'
    )
    search_fields = ('email', 'username')
    list_filter = ('email', 'username')

@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('user', 'author')
    search_fields = ('user__username', 'author__username')