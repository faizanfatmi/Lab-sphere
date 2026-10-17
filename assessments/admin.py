from django.contrib import admin
from .models import (
    Assessment, Question, TestCase, StudentAssessmentAttempt,
    CodeDraft, Submission, AssessmentSecurityEvent
)


class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 1


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'assigned_batch', 'teacher', 'duration_minutes', 'start_time', 'end_time', 'is_published', 'is_archived')
    list_filter = ('assigned_batch', 'is_published', 'is_archived')
    search_fields = ('title', 'assigned_batch')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('title', 'assessment', 'difficulty', 'max_marks', 'order', 'allowed_languages')
    list_filter = ('difficulty', 'assessment')
    search_fields = ('title', 'problem_statement')
    inlines = [TestCaseInline]


@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ('question', 'is_sample', 'weight_percentage', 'order')
    list_filter = ('is_sample', 'question__assessment')


@admin.register(StudentAssessmentAttempt)
class StudentAssessmentAttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'assessment', 'status', 'total_score_obtained', 'started_at', 'submitted_at')
    list_filter = ('status', 'assessment')
    search_fields = ('student__roll_number', 'student__full_name', 'assessment__title')


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'question', 'language', 'status', 'marks_awarded', 'manual_override_marks', 'submitted_at')
    list_filter = ('status', 'language')
    search_fields = ('student__roll_number', 'student__full_name', 'question__title')


@admin.register(AssessmentSecurityEvent)
class AssessmentSecurityEventAdmin(admin.ModelAdmin):
    list_display = ('student', 'assessment', 'event_type', 'timestamp', 'details')
    list_filter = ('event_type', 'assessment')
    search_fields = ('student__roll_number', 'details')
