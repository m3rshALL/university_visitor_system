from django.contrib import admin
from .models import Department

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'director')
    list_select_related = ('director',)  # Оптимизация для получения директора
    search_fields = ('name', 'director__username', 'director__first_name', 'director__last_name')
    autocomplete_fields = ('director',)