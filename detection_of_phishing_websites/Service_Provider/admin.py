from django.contrib import admin
from .models import AdminSession

@admin.register(AdminSession)
class AdminSessionAdmin(admin.ModelAdmin):
    list_display = ['login_at']
