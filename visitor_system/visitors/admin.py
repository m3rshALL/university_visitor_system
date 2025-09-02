from django.contrib import admin
from .models import (
    Guest, Visit, StudentVisit, EmployeeProfile, 
    GuestInvitation, GroupInvitation, GroupGuest, AuditLog
)
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model

# --- Inline ---
class EmployeeProfileInline(admin.StackedInline):
    model = EmployeeProfile
    can_delete = False
    verbose_name_plural = 'Профиль сотрудника (Телефон/Департамент)'
    fk_name = 'user'
    fields = ('phone_number', 'department')
    # Добавляем autocomplete для департамента, если их много
    autocomplete_fields = ['department']

# --- UserAdmin ---
class UserAdmin(BaseUserAdmin):
    inlines = (EmployeeProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_department')
    list_select_related = ('employee_profile__department',) # Оптимизация для списка
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', 'employee_profile__department')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'employee_profile__department__name') # Поиск по департаменту

    @admin.display(description='Департамент', ordering='employee_profile__department')
    def get_department(self, obj):
        if hasattr(obj, 'employee_profile') and obj.employee_profile and obj.employee_profile.department:
            return obj.employee_profile.department.name
        return '-'

    # Нужно переопределить метод, чтобы вернуть queryset с select_related для list_select_related
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('employee_profile__department')

@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'iin', 'phone_number', 'email')
    search_fields = ('full_name', 'iin', 'phone_number', 'email')

@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('id', 'guest', 'employee', 'department', 'status', 'entry_time', 'expected_entry_time', 'exit_time', 'registered_by')
    list_filter = ('status', 'department', 'employee', ('entry_time', admin.DateFieldListFilter), ('expected_entry_time', admin.DateFieldListFilter))
    search_fields = ('guest__full_name', 'guest__iin', 'employee__username', 'department__name', 'purpose')
    list_select_related = ('guest', 'employee', 'department', 'registered_by')
    autocomplete_fields = ('guest', 'employee', 'department', 'registered_by')
    readonly_fields = ('entry_time', 'exit_time') # Время ставится через check-in/out
    date_hierarchy = 'entry_time'

@admin.register(StudentVisit)
class StudentVisitAdmin(admin.ModelAdmin):
    list_display = ('id', 'guest', 'department', 'status', 'entry_time', 'exit_time', 'registered_by', 'student_id_number', 'student_group')
    list_filter = ('status', 'department', ('entry_time', admin.DateFieldListFilter))
    search_fields = ('guest__full_name', 'guest__iin', 'department__name', 'purpose', 'student_id_number', 'student_group')
    list_select_related = ('guest', 'department', 'registered_by')
    autocomplete_fields = ('guest', 'department', 'registered_by')
    readonly_fields = ('entry_time', 'exit_time')
    date_hierarchy = 'entry_time'

@admin.register(GuestInvitation)
class GuestInvitationAdmin(admin.ModelAdmin):
    list_display = ('guest_full_name', 'employee', 'created_at', 'is_filled', 'is_registered', 'visit_time')
    search_fields = ('guest_full_name', 'guest_email', 'employee__username')
    list_filter = ('is_filled', 'is_registered', 'created_at')

@admin.register(GroupInvitation)
class GroupInvitationAdmin(admin.ModelAdmin):
    list_display = ('id', 'employee', 'department', 'purpose', 'visit_time', 'created_at', 'is_filled', 'is_registered')
    search_fields = ('employee__username', 'purpose')
    list_filter = ('is_filled', 'is_registered', 'created_at', 'department')

@admin.register(GroupGuest)
class GroupGuestAdmin(admin.ModelAdmin):
    list_display = ('id', 'group_invitation', 'full_name', 'email', 'phone_number', 'iin', 'is_filled', 'created_at')
    search_fields = ('full_name', 'email', 'iin', 'group_invitation__id')
    list_filter = ('is_filled', 'created_at', 'group_invitation')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'action', 'model', 'object_id', 'actor', 'ip_address')
    list_filter = ('action', 'model', 'created_at')
    search_fields = ('actor__username', 'object_id', 'ip_address')
    readonly_fields = ('created_at', 'action', 'model', 'object_id', 'actor', 
                      'ip_address', 'user_agent', 'path', 'method', 'changes', 'extra')
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        return False  # Запрещаем создание аудит логов через админку
    
    def has_change_permission(self, request, obj=None):
        return False  # Запрещаем редактирование аудит логов
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Только суперпользователь может удалять



# Перерегистрация User
User = get_user_model()
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# Отдельная регистрация EmployeeProfile (опционально, т.к. есть inline)
# admin.site.register(EmployeeProfile)
