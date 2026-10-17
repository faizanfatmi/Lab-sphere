from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import StudentProfile, TeacherProfile, validate_batch_format
from .forms import StudentRegistrationForm, TeacherRegistrationForm

User = get_user_model()


class BatchValidationTests(TestCase):
    def test_valid_batch(self):
        self.assertTrue(validate_batch_format('BATCH 2025-29'))
        self.assertTrue(validate_batch_format('BATCH 2023-27'))
        self.assertTrue(validate_batch_format('  BATCH 2025-29  '))

    def test_invalid_batch_format(self):
        self.assertFalse(validate_batch_format('2025-29'))
        self.assertFalse(validate_batch_format('BATCH 2025-30'))
        self.assertFalse(validate_batch_format('BATCH 2025'))
        self.assertFalse(validate_batch_format('batch 2025-29'))
        self.assertFalse(validate_batch_format(''))


class UserModelTests(TestCase):
    def test_create_student_user(self):
        user = User.objects.create_user(
            username='student_12345',
            password='testpass123',
            role=User.Role.STUDENT,
        )
        self.assertTrue(user.is_student)
        self.assertFalse(user.is_teacher)
        self.assertTrue(user.check_password('testpass123'))
        # Password should be hashed
        self.assertNotEqual(user.password, 'testpass123')

    def test_create_teacher_user(self):
        user = User.objects.create_user(
            username='teacher_T001',
            password='testpass123',
            role=User.Role.TEACHER,
        )
        self.assertTrue(user.is_teacher)
        self.assertFalse(user.is_student)


class StudentRegistrationTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_successful_registration(self):
        response = self.client.post(reverse('student_register'), {
            'full_name': 'John Doe',
            'roll_number': '12345',
            'batch': 'BATCH 2025-29',
            'password': 'securepass123',
            'confirm_password': 'securepass123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(StudentProfile.objects.filter(roll_number='12345').exists())
        user = StudentProfile.objects.get(roll_number='12345').user
        self.assertNotEqual(user.password, 'securepass123')

    def test_duplicate_roll_number(self):
        self.client.post(reverse('student_register'), {
            'full_name': 'John Doe',
            'roll_number': '12345',
            'batch': 'BATCH 2025-29',
            'password': 'securepass123',
            'confirm_password': 'securepass123',
        })
        response = self.client.post(reverse('student_register'), {
            'full_name': 'Jane Doe',
            'roll_number': '12345',
            'batch': 'BATCH 2025-29',
            'password': 'securepass123',
            'confirm_password': 'securepass123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(StudentProfile.objects.filter(roll_number='12345').count(), 1)

    def test_invalid_batch(self):
        response = self.client.post(reverse('student_register'), {
            'full_name': 'John Doe',
            'roll_number': '99999',
            'batch': 'INVALID',
            'password': 'securepass123',
            'confirm_password': 'securepass123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(StudentProfile.objects.filter(roll_number='99999').exists())

    def test_password_mismatch(self):
        response = self.client.post(reverse('student_register'), {
            'full_name': 'John Doe',
            'roll_number': '11111',
            'batch': 'BATCH 2025-29',
            'password': 'securepass123',
            'confirm_password': 'differentpass',
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(StudentProfile.objects.filter(roll_number='11111').exists())


class StudentLoginTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.post(reverse('student_register'), {
            'full_name': 'John Doe',
            'roll_number': '12345',
            'batch': 'BATCH 2025-29',
            'password': 'securepass123',
            'confirm_password': 'securepass123',
        })

    def test_successful_login(self):
        response = self.client.post(reverse('student_login'), {
            'name': 'John Doe',
            'batch': 'BATCH 2025-29',
            'roll_number': '12345',
            'password': 'securepass123',
        })
        self.assertRedirects(response, reverse('student_dashboard'))

    def test_wrong_password(self):
        response = self.client.post(reverse('student_login'), {
            'name': 'John Doe',
            'batch': 'BATCH 2025-29',
            'roll_number': '12345',
            'password': 'wrongpass',
        })
        self.assertRedirects(response, reverse('landing'))

    def test_wrong_name(self):
        response = self.client.post(reverse('student_login'), {
            'name': 'Wrong Name',
            'batch': 'BATCH 2025-29',
            'roll_number': '12345',
            'password': 'securepass123',
        })
        self.assertRedirects(response, reverse('landing'))


class TeacherRegistrationTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_successful_registration(self):
        from django.conf import settings
        response = self.client.post(reverse('teacher_register'), {
            'teacher_id': 'T001',
            'full_name': 'Dr. Smith',
            'password': 'securepass123',
            'confirm_password': 'securepass123',
            'registration_code': settings.TEACHER_REGISTRATION_SECRET,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(TeacherProfile.objects.filter(teacher_id='T001').exists())

    def test_wrong_registration_code(self):
        response = self.client.post(reverse('teacher_register'), {
            'teacher_id': 'T002',
            'full_name': 'Dr. Jones',
            'password': 'securepass123',
            'confirm_password': 'securepass123',
            'registration_code': 'WRONG_CODE',
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(TeacherProfile.objects.filter(teacher_id='T002').exists())

    def test_duplicate_teacher_id(self):
        from django.conf import settings
        self.client.post(reverse('teacher_register'), {
            'teacher_id': 'T001',
            'full_name': 'Dr. Smith',
            'password': 'securepass123',
            'confirm_password': 'securepass123',
            'registration_code': settings.TEACHER_REGISTRATION_SECRET,
        })
        response = self.client.post(reverse('teacher_register'), {
            'teacher_id': 'T001',
            'full_name': 'Dr. Other',
            'password': 'securepass123',
            'confirm_password': 'securepass123',
            'registration_code': settings.TEACHER_REGISTRATION_SECRET,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(TeacherProfile.objects.filter(teacher_id='T001').count(), 1)


class TeacherLoginTests(TestCase):
    def setUp(self):
        self.client = Client()
        from django.conf import settings
        self.client.post(reverse('teacher_register'), {
            'teacher_id': 'T001',
            'full_name': 'Dr. Smith',
            'password': 'securepass123',
            'confirm_password': 'securepass123',
            'registration_code': settings.TEACHER_REGISTRATION_SECRET,
        })

    def test_successful_login(self):
        response = self.client.post(reverse('teacher_login'), {
            'name': 'Dr. Smith',
            'teacher_id': 'T001',
            'password': 'securepass123',
        })
        self.assertRedirects(response, reverse('teacher_dashboard'))

    def test_wrong_password(self):
        response = self.client.post(reverse('teacher_login'), {
            'name': 'Dr. Smith',
            'teacher_id': 'T001',
            'password': 'wrongpass',
        })
        self.assertRedirects(response, reverse('landing'))


class RoleAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.post(reverse('student_register'), {
            'full_name': 'Student User',
            'roll_number': '55555',
            'batch': 'BATCH 2025-29',
            'password': 'securepass123',
            'confirm_password': 'securepass123',
        })
        from django.conf import settings
        self.client.post(reverse('teacher_register'), {
            'teacher_id': 'T999',
            'full_name': 'Teacher User',
            'password': 'securepass123',
            'confirm_password': 'securepass123',
            'registration_code': settings.TEACHER_REGISTRATION_SECRET,
        })

    def test_student_cannot_access_teacher_dashboard(self):
        self.client.post(reverse('student_login'), {
            'name': 'Student User',
            'batch': 'BATCH 2025-29',
            'roll_number': '55555',
            'password': 'securepass123',
        })
        response = self.client.get(reverse('teacher_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_teacher_cannot_access_student_dashboard(self):
        self.client.post(reverse('teacher_login'), {
            'name': 'Teacher User',
            'teacher_id': 'T999',
            'password': 'securepass123',
        })
        response = self.client.get(reverse('student_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_unauthenticated_cannot_access_dashboards(self):
        response = self.client.get(reverse('student_dashboard'))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse('teacher_dashboard'))
        self.assertEqual(response.status_code, 302)


class LogoutTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.post(reverse('student_register'), {
            'full_name': 'Logout Test',
            'roll_number': '77777',
            'batch': 'BATCH 2025-29',
            'password': 'securepass123',
            'confirm_password': 'securepass123',
        })

    def test_logout(self):
        self.client.post(reverse('student_login'), {
            'name': 'Logout Test',
            'batch': 'BATCH 2025-29',
            'roll_number': '77777',
            'password': 'securepass123',
        })
        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, reverse('landing'))
        # After logout, should not be able to access dashboard
        response = self.client.get(reverse('student_dashboard'))
        self.assertEqual(response.status_code, 302)


class CSRFTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def test_student_register_requires_csrf(self):
        response = self.client.post(reverse('student_register'), {
            'full_name': 'CSRF Test',
            'roll_number': '99999',
            'batch': 'BATCH 2025-29',
            'password': 'securepass123',
            'confirm_password': 'securepass123',
        })
        self.assertEqual(response.status_code, 403)

    def test_student_login_requires_csrf(self):
        response = self.client.post(reverse('student_login'), {
            'name': 'Test',
            'batch': 'BATCH 2025-29',
            'roll_number': '99999',
            'password': 'test',
        })
        self.assertEqual(response.status_code, 403)
