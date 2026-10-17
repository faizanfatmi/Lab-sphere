from django.contrib import admin
from .models import Lab, LabSession, LabAttendance


@admin.register(Lab)
class LabAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'department', 'created_by', 'created_at')
    search_fields = ('code', 'name', 'department')


@admin.register(LabSession)
class LabSessionAdmin(admin.ModelAdmin):
    list_display = ('session_title', 'lab', 'teacher', 'batch', 'date', 'start_time', 'end_time', 'is_active')
    list_filter = ('batch', 'date', 'is_active')
    search_fields = ('session_title', 'lab__code', 'batch')


@admin.register(LabAttendance)
class LabAttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'session', 'status', 'checked_in_at', 'manual_override', 'client_ip')
    list_filter = ('status', 'manual_override', 'session__batch')
    search_fields = ('student__full_name', 'student__roll_number', 'session__session_title')
