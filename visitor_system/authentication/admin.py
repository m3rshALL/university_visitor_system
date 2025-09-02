from django.contrib import admin
from .models import Role
from guardian.admin import GuardedModelAdmin

@admin.register(Role)
class RoleAdmin(GuardedModelAdmin):
    list_display = ('name', 'group')
    search_fields = ('name',)
