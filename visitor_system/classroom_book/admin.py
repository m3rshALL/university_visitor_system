from django.contrib import admin
from .models import Classroom, ClassroomKey, KeyBooking


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('number', 'building', 'floor', 'capacity', 'is_active')
    search_fields = ('number', 'building')
    list_filter = ('building', 'floor', 'is_active')


@admin.register(ClassroomKey)
class ClassroomKeyAdmin(admin.ModelAdmin):
    list_display = ('key_number', 'classroom', 'is_available')
    search_fields = ('key_number', 'classroom__number')
    list_filter = ('is_available', 'classroom__building')
    autocomplete_fields = ('classroom',)


@admin.register(KeyBooking)
class KeyBookingAdmin(admin.ModelAdmin):
    list_display = ('classroom', 'teacher', 'start_time', 'end_time',
                     'status', 'is_returned')
    search_fields = ('classroom__number', 'teacher__username', 'teacher__email')
    list_filter = ('status', 'is_returned', 'is_cancelled', 'start_time')
    date_hierarchy = 'start_time'
    readonly_fields = ('qr_code_token',)
    autocomplete_fields = ('classroom', 'key', 'teacher')
