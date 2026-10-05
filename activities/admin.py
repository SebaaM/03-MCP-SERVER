"""Admin de Django para inspeccionar actividades e inscripciones."""

from django.contrib import admin

from activities.models import Activity, Registration


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("title", "capacity", "seats_taken", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title",)


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ("student_email", "activity", "created_at")
    search_fields = ("student_email", "activity__title")
