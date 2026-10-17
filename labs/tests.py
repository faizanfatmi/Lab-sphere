from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from accounts.models import User, StudentProfile, TeacherProfile
from labs.models import Lab, LabSession, LabAttendance


class LabSessionAndAttendanceTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create Teacher
        self.teacher_user = User.objects.create_user(
            username='teacher_T100', password='password123', role=User.Role.TEACHER
        )
        self.teacher = TeacherProfile.objects.create(
            user=self.teacher_user, full_name='Prof. Alan Turing', teacher_id='T100'
        )

        # Create Student 1 (Batch 2025-29)
        self.student_user = User.objects.create_user(
            username='student_101', password='password123', role=User.Role.STUDENT
        )
        self.student = StudentProfile.objects.create(
            user=self.student_user, full_name='Alice Student', roll_number='101', batch='BATCH 2025-29'
        )

        # Create Student 2 (Different Batch: 2024-28)
        self.student_user2 = User.objects.create_user(
            username='student_102', password='password123', role=User.Role.STUDENT
        )
        self.student2 = StudentProfile.objects.create(
            user=self.student_user2, full_name='Bob OtherBatch', roll_number='102', batch='BATCH 2024-28'
        )

        # Create Lab
        self.lab = Lab.objects.create(
            name='Algorithms Laboratory', code='CS301L', created_by=self.teacher
        )

        # Create Active Session for BATCH 2025-29
        now = timezone.localtime()
        self.session = LabSession.objects.create(
            lab=self.lab,
            teacher=self.teacher,
            session_title='Graph Algorithms Lab',
            batch='BATCH 2025-29',
            date=now.date(),
            start_time=(now - timedelta(minutes=15)).time(),
            end_time=(now + timedelta(minutes=45)).time(),
            verification_code='123456',
            is_active=True
        )

    def test_student_checkin_success(self):
        self.client.force_login(self.student_user)
        response = self.client.post(reverse('student_checkin', args=[self.session.id]), {
            'verification_code': '123456'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(LabAttendance.objects.filter(session=self.session, student=self.student).exists())
        att = LabAttendance.objects.get(session=self.session, student=self.student)
        self.assertEqual(att.status, LabAttendance.Status.PRESENT)

    def test_duplicate_checkin_prevention(self):
        self.client.force_login(self.student_user)
        # First check-in
        self.client.post(reverse('student_checkin', args=[self.session.id]), {'verification_code': '123456'})
        self.assertEqual(LabAttendance.objects.filter(session=self.session, student=self.student).count(), 1)
        
        # Second check-in attempt
        response = self.client.post(reverse('student_checkin', args=[self.session.id]), {'verification_code': '123456'})
        self.assertEqual(response.status_code, 302)
        # Still exactly 1 record
        self.assertEqual(LabAttendance.objects.filter(session=self.session, student=self.student).count(), 1)

    def test_wrong_batch_checkin_fails(self):
        self.client.force_login(self.student_user2) # Student from BATCH 2024-28
        response = self.client.post(reverse('student_checkin', args=[self.session.id]), {
            'verification_code': '123456'
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(LabAttendance.objects.filter(session=self.session, student=self.student2).exists())

    def test_invalid_pin_fails(self):
        self.client.force_login(self.student_user)
        response = self.client.post(reverse('student_checkin', args=[self.session.id]), {
            'verification_code': 'WRONG_PIN'
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(LabAttendance.objects.filter(session=self.session, student=self.student).exists())

    def test_teacher_manual_attendance_override_with_audit(self):
        # Student was absent
        self.client.force_login(self.teacher_user)
        response = self.client.post(reverse('attendance_override', args=[self.session.id, self.student.id]), {
            'status': 'PRESENT',
            'override_reason': 'Student computer had a network issue, physically verified in room 204'
        })
        self.assertEqual(response.status_code, 302)
        att = LabAttendance.objects.get(session=self.session, student=self.student)
        self.assertEqual(att.status, 'PRESENT')
        self.assertTrue(att.manual_override)
        self.assertEqual(att.overridden_by, self.teacher)
        self.assertIn('physically verified', att.override_reason)

    def test_attendance_csv_export(self):
        self.client.force_login(self.teacher_user)
        response = self.client.get(reverse('attendance_export', args=[self.session.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename=', response['Content-Disposition'])
