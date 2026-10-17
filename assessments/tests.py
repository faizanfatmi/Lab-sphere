import json
from unittest.mock import patch
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from accounts.models import User, StudentProfile, TeacherProfile
from assessments.models import (
    Assessment, Question, TestCase as ProblemTestCase,
    StudentAssessmentAttempt, CodeDraft, Submission, AssessmentSecurityEvent
)
from assessments.services.execution import MockExecutor


@override_settings(EXECUTION_SERVICE_MODE='mock')
class AssessmentSystemTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Teacher
        self.teacher_user = User.objects.create_user(
            username='teacher_T200', password='password123', role=User.Role.TEACHER
        )
        self.teacher = TeacherProfile.objects.create(
            user=self.teacher_user, full_name='Dr. Grace Hopper', teacher_id='T200'
        )

        # Student 1 (BATCH 2025-29)
        self.student_user = User.objects.create_user(
            username='student_201', password='password123', role=User.Role.STUDENT
        )
        self.student = StudentProfile.objects.create(
            user=self.student_user, full_name='Ada Lovelace', roll_number='201', batch='BATCH 2025-29'
        )

        # Student 2 (Different Batch: BATCH 2024-28)
        self.student_user_other = User.objects.create_user(
            username='student_202', password='password123', role=User.Role.STUDENT
        )
        self.student_other = StudentProfile.objects.create(
            user=self.student_user_other, full_name='Charles Babbage', roll_number='202', batch='BATCH 2024-28'
        )

        # Active Assessment for BATCH 2025-29
        now = timezone.now()
        self.assessment = Assessment.objects.create(
            teacher=self.teacher,
            title='Midterm Coding Test',
            assigned_batch='BATCH 2025-29',
            duration_minutes=60,
            start_time=now - timedelta(minutes=10),
            end_time=now + timedelta(minutes=50),
            pass_marks=40,
            is_published=True
        )

        # Coding Question (10 marks)
        self.question = Question.objects.create(
            assessment=self.assessment,
            teacher=self.teacher,
            title='Sum of Two Numbers',
            problem_statement='Read two integers from stdin and print their sum.',
            input_format='Two integers on a single line',
            output_format='A single integer',
            max_marks=10.00,
            order=1
        )

        # Test Cases: 1 Sample (visible), 1 Private (hidden)
        self.tc_sample = ProblemTestCase.objects.create(
            question=self.question,
            input_data='2 3',
            expected_output='5',
            is_sample=True,
            order=1
        )
        self.tc_private = ProblemTestCase.objects.create(
            question=self.question,
            input_data='10 20',
            expected_output='30',
            is_sample=False,
            order=2
        )

    def test_student_batch_access_control(self):
        # Eligible student gets access
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('coding_assessment', args=[self.assessment.id]))
        self.assertEqual(response.status_code, 200)

        # Other batch student gets denied and redirected
        self.client.force_login(self.student_user_other)
        response = self.client.get(reverse('coding_assessment', args=[self.assessment.id]))
        self.assertEqual(response.status_code, 302)

    def test_private_test_cases_hidden_from_student_view(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('coding_assessment', args=[self.assessment.id]))
        self.assertEqual(response.status_code, 200)
        
        sample_cases = response.context['sample_test_cases']
        self.assertEqual(sample_cases.count(), 1)
        self.assertEqual(sample_cases.first().input_data, '2 3')
        # Private testcase '10 20' is NOT in sample_test_cases context!
        for tc in sample_cases:
            self.assertTrue(tc.is_sample)

    def test_run_code_does_not_award_marks(self):
        self.client.force_login(self.student_user)
        payload = {
            'question_id': self.question.id,
            'language': 'python',
            'source_code': 'print(5)',
        }
        with patch('assessments.views.get_executor', return_value=MockExecutor(should_pass=True, mock_stdout='5')):
            response = self.client.post(
                reverse('api_run_code'),
                data=json.dumps(payload),
                content_type='application/json'
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ACCEPTED')
        # Ensure no submission was created and no marks awarded
        self.assertEqual(Submission.objects.count(), 0)

    def test_submit_code_evaluates_and_awards_marks(self):
        self.client.force_login(self.student_user)
        # Create attempt
        attempt = StudentAssessmentAttempt.objects.create(
            assessment=self.assessment, student=self.student
        )

        payload = {
            'question_id': self.question.id,
            'attempt_id': attempt.id,
            'language': 'python',
            'source_code': 'a, b = map(int, input().split())\nprint(a + b)',
        }

        # Mock executor returning output matching test cases
        class DynamicSumMockExecutor(MockExecutor):
            def execute(self, language, source_code, stdin, **kwargs):
                parts = stdin.strip().split()
                ans = str(int(parts[0]) + int(parts[1]))
                return super().execute(language, source_code, stdin, mock_stdout=ans, should_pass=True)

        with patch('assessments.views.get_executor', return_value=DynamicSumMockExecutor(should_pass=True)):
            response = self.client.post(
                reverse('api_submit_code'),
                data=json.dumps(payload),
                content_type='application/json'
            )

            self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['status'], 'ACCEPTED')
        self.assertEqual(data['passed_count'], 2)
        self.assertEqual(data['total_count'], 2)
        self.assertEqual(data['marks_awarded'], 10.0)

        # Check Submission and Attempt persisted in database
        sub = Submission.objects.get(id=data['submission_id'])
        self.assertEqual(sub.status, 'ACCEPTED')
        self.assertEqual(sub.marks_awarded, 10.0)
        attempt.refresh_from_db()
        self.assertEqual(float(attempt.total_score_obtained), 10.0)

    def test_compilation_error_handling(self):
        self.client.force_login(self.student_user)
        attempt = StudentAssessmentAttempt.objects.create(
            assessment=self.assessment, student=self.student
        )
        payload = {
            'question_id': self.question.id,
            'attempt_id': attempt.id,
            'language': 'cpp',
            'source_code': 'int main() { SYNTAX_ERROR }',
        }
        with patch('assessments.views.get_executor', return_value=MockExecutor()):
            response = self.client.post(
                reverse('api_submit_code'),
                data=json.dumps(payload),
                content_type='application/json'
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'COMPILATION_ERROR')
        self.assertEqual(data['marks_awarded'], 0.0)

    def test_autosave_and_retrieve_draft(self):
        self.client.force_login(self.student_user)
        save_payload = {
            'question_id': self.question.id,
            'language': 'python',
            'source_code': 'def solve(): return 42'
        }
        response = self.client.post(
            reverse('api_save_draft'),
            data=json.dumps(save_payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(CodeDraft.objects.filter(student=self.student, question=self.question, language='python').exists())

        # Retrieve draft
        get_response = self.client.get(reverse('api_get_draft'), {
            'question_id': self.question.id,
            'language': 'python'
        })
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json()['code'], 'def solve(): return 42')

    def test_security_event_logging(self):
        self.client.force_login(self.student_user)
        payload = {
            'assessment_id': self.assessment.id,
            'event_type': 'TAB_SWITCH',
            'details': 'Student switched to Google Chrome external window'
        }
        response = self.client.post(
            reverse('api_log_security_event'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(AssessmentSecurityEvent.objects.filter(
            student=self.student,
            assessment=self.assessment,
            event_type='TAB_SWITCH'
        ).exists())

    def test_teacher_score_override_with_audit(self):
        attempt = StudentAssessmentAttempt.objects.create(
            assessment=self.assessment, student=self.student
        )
        submission = Submission.objects.create(
            attempt=attempt,
            student=self.student,
            question=self.question,
            language='python',
            source_code='print(1)',
            status='WRONG_ANSWER',
            marks_awarded=0.00
        )

        self.client.force_login(self.teacher_user)
        response = self.client.post(reverse('submission_override', args=[submission.id]), {
            'manual_override_marks': '8.5',
            'override_reason': 'Partial approach logic is correct; minor output format off by 1'
        })
        self.assertEqual(response.status_code, 302)

        submission.refresh_from_db()
        self.assertEqual(float(submission.manual_override_marks), 8.5)
        self.assertEqual(submission.overridden_by, self.teacher)
        self.assertIn('Partial approach', submission.override_reason)

        # Attempt score recalculated
        attempt.refresh_from_db()
        self.assertEqual(float(attempt.total_score_obtained), 8.5)
