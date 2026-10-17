from django.contrib.auth.backends import BaseBackend
from .models import User, StudentProfile, TeacherProfile


class StudentAuthBackend(BaseBackend):
    """Authenticate students using roll_number as primary identifier."""
    
    def authenticate(self, request, roll_number=None, password=None, name=None, batch=None, **kwargs):
        if not roll_number or not password:
            return None
        try:
            profile = StudentProfile.objects.select_related('user').get(roll_number=roll_number)
            user = profile.user
            if not user.is_active or user.role != User.Role.STUDENT:
                return None
            if not user.check_password(password):
                return None
            # Verify name and batch match
            if name and profile.full_name.strip().lower() != name.strip().lower():
                return None
            if batch and profile.batch.strip().upper() != batch.strip().upper():
                return None
            return user
        except StudentProfile.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class TeacherAuthBackend(BaseBackend):
    """Authenticate teachers using teacher_id as primary identifier."""
    
    def authenticate(self, request, teacher_id=None, password=None, name=None, **kwargs):
        if not teacher_id or not password:
            return None
        try:
            profile = TeacherProfile.objects.select_related('user').get(teacher_id=teacher_id)
            user = profile.user
            if not user.is_active or user.role != User.Role.TEACHER:
                return None
            if not user.check_password(password):
                return None
            # Verify name matches
            if name and profile.full_name.strip().lower() != name.strip().lower():
                return None
            return user
        except TeacherProfile.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
