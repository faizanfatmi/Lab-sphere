from django.db import models
from django.utils import timezone
from accounts.models import StudentProfile, TeacherProfile


class Lab(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    department = models.CharField(max_length=150, default='Computer Science & Engineering')
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, related_name='created_labs')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        ordering = ['code']


class LabSession(models.Model):
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE, related_name='sessions')
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='conducted_sessions')
    session_title = models.CharField(max_length=200)
    batch = models.CharField(max_length=20, help_text="Batch e.g. BATCH 2025-29")
    date = models.DateField(default=timezone.now)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    verification_code = models.CharField(max_length=20, blank=True, help_text="Optional pin for lab check-in verification")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.lab.code} - {self.session_title} ({self.batch} on {self.date})"

    @property
    def is_currently_open(self):
        now = timezone.localtime()
        if not self.is_active:
            return False
        if self.date != now.date():
            return False
        current_time = now.time()
        return self.start_time <= current_time <= self.end_time

    class Meta:
        ordering = ['-date', '-start_time']


class LabAttendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = 'PRESENT', 'Present'
        ABSENT = 'ABSENT', 'Absent'
        LATE = 'LATE', 'Late'

    session = models.ForeignKey(LabSession, on_delete=models.CASCADE, related_name='attendance_records')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='lab_attendances')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PRESENT)
    checked_in_at = models.DateTimeField(default=timezone.now)
    client_ip = models.GenericIPAddressField(null=True, blank=True)
    device_info = models.CharField(max_length=255, blank=True)
    
    # Audit & Manual Override
    manual_override = models.BooleanField(default=False)
    override_reason = models.TextField(blank=True)
    overridden_by = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_overrides')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('session', 'student')
        ordering = ['-checked_in_at']
        verbose_name = 'Lab Attendance Record'
        verbose_name_plural = 'Lab Attendance Records'

    def __str__(self):
        return f"{self.student.full_name} ({self.student.roll_number}) - {self.session.session_title} - {self.status}"
