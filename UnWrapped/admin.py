from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.urls import path
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'name', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'name')
    ordering = ('-date_joined',)

# Unregister the default UserAdmin and register your custom one
admin.site.register(CustomUser, CustomUserAdmin)

urlpatterns = [
    path('admin/', admin.site.urls),
]