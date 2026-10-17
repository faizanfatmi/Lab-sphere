import re
from datetime import datetime
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


def validate_batch_format(batch):
    """Validate batch follows format BATCH YYYY-YY (e.g. BATCH 2025-29)."""
    pattern = r'^BATCH\s+\d{4}-\d{2}$'
    if not re.match(pattern, batch.strip()):
        return False
    parts = batch.strip().split()
    year_parts = parts[1].split('-')
    start_year = int(year_parts[0])
    end_suffix = int(year_parts[1])
    # The end suffix should be the last 2 digits of (start_year + 4)
    expected_suffix = (start_year + 4) % 100
    return end_suffix == expected_suffix


def get_batch_choices():
    """
    Dynamically generate batch choices based on the current year.
    Each batch spans 4 years (e.g., BATCH 2025-29).
    Generates batches from 3 years ago up to the current year,
    so older students can still be found while new batches are available.
    """
    current_year = datetime.now().year
    choices = [('', '-- Select Batch --')]
    for start_year in range(current_year - 3, current_year + 1):
        end_suffix = (start_year + 4) % 100
        batch_label = f"BATCH {start_year}-{end_suffix:02d}"
        choices.append((batch_label, batch_label))
    return choices


class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('Username is required')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.TEACHER)
        return self.create_user(username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        STUDENT = 'STUDENT', 'Student'
        TEACHER = 'TEACHER', 'Teacher'

    username = models.CharField(max_length=150, unique=True)
    role = models.CharField(max_length=10, choices=Role.choices)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    full_name = models.CharField(max_length=200)
    roll_number = models.CharField(max_length=50, unique=True)
    batch = models.CharField(max_length=20)

    def __str__(self):
        return f'{self.full_name} ({self.roll_number})'

    class Meta:
        verbose_name = 'Student Profile'
        verbose_name_plural = 'Student Profiles'


class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    full_name = models.CharField(max_length=200)
    teacher_id = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f'{self.full_name} ({self.teacher_id})'

    class Meta:
        verbose_name = 'Teacher Profile'
        verbose_name_plural = 'Teacher Profiles'
