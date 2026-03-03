from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'get_full_name', 'perfil', 'empresa', 'is_active')
    list_filter = ('perfil', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Perfil BK ERP', {'fields': ('perfil', 'empresa', 'telefone')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Perfil BK ERP', {'fields': ('perfil', 'empresa', 'telefone', 'first_name', 'last_name', 'email')}),
    )
