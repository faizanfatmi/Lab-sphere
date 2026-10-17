"""
Script to create test teacher and student accounts for LabSphere.
Run: python manage.py shell < create_test_accounts.py
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'labsphere.settings')
django.setup()

from accounts.models import User, StudentProfile, TeacherProfile

# ===== Test Teacher Account =====
TEACHER_ID = "TEACH001"
TEACHER_NAME = "Prof. Arjun Sharma"
TEACHER_PASSWORD = "teacher@123"
TEACHER_USERNAME = f"teacher_{TEACHER_ID}"

if not User.objects.filter(username=TEACHER_USERNAME).exists():
    teacher_user = User.objects.create_user(
        username=TEACHER_USERNAME,
        password=TEACHER_PASSWORD,
        role=User.Role.TEACHER,
    )
    TeacherProfile.objects.create(
        user=teacher_user,
        full_name=TEACHER_NAME,
        teacher_id=TEACHER_ID,
    )
    print(f"[OK] Teacher account created: {TEACHER_NAME} ({TEACHER_ID})")
else:
    print(f"[SKIP] Teacher '{TEACHER_USERNAME}' already exists.")

# ===== Test Student Account =====
STUDENT_NAME = "Faizan Fatmi"
STUDENT_ROLL = "2025CSE001"
STUDENT_BATCH = "BATCH 2025-29"
STUDENT_PASSWORD = "student@123"
STUDENT_USERNAME = f"student_{STUDENT_ROLL}"

if not User.objects.filter(username=STUDENT_USERNAME).exists():
    student_user = User.objects.create_user(
        username=STUDENT_USERNAME,
        password=STUDENT_PASSWORD,
        role=User.Role.STUDENT,
    )
    StudentProfile.objects.create(
        user=student_user,
        full_name=STUDENT_NAME,
        roll_number=STUDENT_ROLL,
        batch=STUDENT_BATCH,
    )
    print(f"[OK] Student account created: {STUDENT_NAME} ({STUDENT_ROLL})")
else:
    print(f"[SKIP] Student '{STUDENT_USERNAME}' already exists.")

print("\nDone! Test accounts are ready.")
