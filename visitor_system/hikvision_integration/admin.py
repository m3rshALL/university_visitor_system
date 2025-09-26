from django.contrib import admin
from .models import HikDevice, HikFaceLibrary, HikPersonBinding, HikAccessTask, HikEventLog


@admin.register(HikDevice)
class HikDeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "host", "port", "is_primary", "enabled")
    list_filter = ("enabled", "is_primary")
    search_fields = ("name", "host")


@admin.register(HikFaceLibrary)
class HikFaceLibraryAdmin(admin.ModelAdmin):
    list_display = ("device", "library_id", "name")
    search_fields = ("library_id", "name")


@admin.register(HikPersonBinding)
class HikPersonBindingAdmin(admin.ModelAdmin):
    list_display = ("guest_id", "device", "person_id", "status", "updated_at")
    list_filter = ("status", "device")
    search_fields = ("guest_id", "person_id")


@admin.register(HikAccessTask)
class HikAccessTaskAdmin(admin.ModelAdmin):
    list_display = ("id", "kind", "status", "attempts", "guest_id", "visit_id", "updated_at")
    list_filter = ("kind", "status")
    search_fields = ("id", "guest_id", "visit_id")
    readonly_fields = ("created_at", "updated_at")


@admin.register(HikEventLog)
class HikEventLogAdmin(admin.ModelAdmin):
    list_display = ("device", "event_type", "occurred_at", "resolved_visit_id")
    list_filter = ("event_type", "device")
    search_fields = ("resolved_visit_id",)



