from django.db import models
from django.utils import timezone
from accounts.models import StudentProfile, TeacherProfile
from labs.models import Lab


class Assessment(models.Model):
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='created_assessments')
    lab = models.ForeignKey(Lab, on_delete=models.SET_NULL, null=True, blank=True, related_name='assessments')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assigned_batch = models.CharField(max_length=20, help_text="e.g. BATCH 2025-29")
    duration_minutes = models.PositiveIntegerField(default=60)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField()
    pass_marks = models.PositiveIntegerField(default=40)
    is_published = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.title} ({self.assigned_batch})"

    @property
    def total_marks(self):
        result = self.questions.aggregate(total=models.Sum('max_marks'))['total']
        return result or 0

    @property
    def question_count(self):
        return self.questions.count()

    @property
    def is_currently_active(self):
        now = timezone.now()
        return self.is_published and not self.is_archived and (self.start_time <= now <= self.end_time)

    @property
    def is_upcoming(self):
        return self.is_published and not self.is_archived and (timezone.now() < self.start_time)

    @property
    def is_expired(self):
        return self.is_published and (timezone.now() > self.end_time)


class Question(models.Model):
    class Difficulty(models.TextChoices):
        EASY = 'EASY', 'Easy'
        MEDIUM = 'MEDIUM', 'Medium'
        HARD = 'HARD', 'Hard'

    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='questions')
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='created_questions')
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True)
    difficulty = models.CharField(max_length=10, choices=Difficulty.choices, default=Difficulty.MEDIUM)
    max_marks = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    order = models.PositiveIntegerField(default=1)
    
    problem_statement = models.TextField(blank=True, default="", help_text="Detailed problem description (Markdown supported)")
    input_format = models.TextField(blank=True, default="Standard input format", help_text="Input format specification")
    output_format = models.TextField(blank=True, default="Standard output format", help_text="Output format specification")
    constraints = models.TextField(blank=True, help_text="Constraints on variables")
    sample_explanation = models.TextField(blank=True, help_text="Explanation for sample test cases")
    
    allowed_languages = models.CharField(max_length=100, default='c,cpp,java,python')
    time_limit_seconds = models.DecimalField(max_digits=4, decimal_places=1, default=2.0)
    memory_limit_mb = models.PositiveIntegerField(default=256)
    
    # Starter templates
    c_starter_code = models.TextField(
        blank=True,
        default="// C Solution\n#include <stdio.h>\n\nint main() {\n    // Write your code here\n    \n    return 0;\n}"
    )
    cpp_starter_code = models.TextField(
        blank=True,
        default="// C++ Solution\n#include <iostream>\nusing namespace std;\n\nint main() {\n    // Write your code here\n    \n    return 0;\n}"
    )
    java_starter_code = models.TextField(
        blank=True,
        default="// Java Solution\nimport java.util.Scanner;\n\npublic class Solution {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        // Write your code here\n        \n    }\n}"
    )
    python_starter_code = models.TextField(
        blank=True,
        default="# Python Solution\ndef main():\n    # Write your code here\n    pass\n\nif __name__ == '__main__':\n    main()"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.order}. {self.title} ({self.max_marks} marks)"

    @property
    def sample_test_cases(self):
        return self.test_cases.filter(is_sample=True)

    @property
    def private_test_cases(self):
        return self.test_cases.filter(is_sample=False)


class TestCase(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='test_cases')
    input_data = models.TextField()
    expected_output = models.TextField()
    is_sample = models.BooleanField(default=False, help_text="Visible to students as sample in problem statement")
    weight_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        kind = "Sample" if self.is_sample else "Private"
        return f"{kind} Test Case #{self.order} for Question {self.question_id}"


class StudentAssessmentAttempt(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = 'NOT_STARTED', 'Not Started'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        EVALUATED = 'EVALUATED', 'Evaluated'
        EXPIRED = 'EXPIRED', 'Expired'

    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='student_attempts')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='assessment_attempts')
    started_at = models.DateTimeField(default=timezone.now)
    submitted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.IN_PROGRESS)
    total_score_obtained = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)

    class Meta:
        unique_together = ('assessment', 'student')
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.student.roll_number} - {self.assessment.title} ({self.status})"

    def recalculate_total_score(self):
        # Latest or best score per question in this assessment
        total = 0.0
        for question in self.assessment.questions.all():
            best_sub = (
                Submission.objects
                .filter(attempt=self, question=question)
                .order_by('-marks_awarded')
                .first()
            )
            if best_sub:
                effective_marks = best_sub.manual_override_marks if best_sub.manual_override_marks is not None else best_sub.marks_awarded
                total += float(effective_marks)
        self.total_score_obtained = total
        self.save(update_fields=['total_score_obtained'])
        return total


class CodeDraft(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='code_drafts')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='drafts')
    language = models.CharField(max_length=20)
    code = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'question', 'language')

    def __str__(self):
        return f"{self.student.roll_number} - {self.question.title} ({self.language})"


class Submission(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Evaluation'
        RUNNING = 'RUNNING', 'Running'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        WRONG_ANSWER = 'WRONG_ANSWER', 'Wrong Answer'
        TIME_LIMIT_EXCEEDED = 'TIME_LIMIT_EXCEEDED', 'Time Limit Exceeded'
        MEMORY_LIMIT_EXCEEDED = 'MEMORY_LIMIT_EXCEEDED', 'Memory Limit Exceeded'
        COMPILATION_ERROR = 'COMPILATION_ERROR', 'Compilation Error'
        RUNTIME_ERROR = 'RUNTIME_ERROR', 'Runtime Error'
        EVALUATION_FAILED = 'EVALUATION_FAILED', 'Evaluation Failed'

    attempt = models.ForeignKey(StudentAssessmentAttempt, on_delete=models.CASCADE, related_name='submissions', null=True, blank=True)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='submissions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='submissions')
    language = models.CharField(max_length=20)
    source_code = models.TextField()
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)
    
    marks_awarded = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    manual_override_marks = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    override_reason = models.TextField(blank=True)
    overridden_by = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='submission_overrides')
    
    test_cases_passed = models.PositiveIntegerField(default=0)
    total_test_cases = models.PositiveIntegerField(default=0)
    execution_time_ms = models.PositiveIntegerField(default=0)
    memory_kb = models.PositiveIntegerField(default=0)
    compiler_output = models.TextField(blank=True)
    evaluation_details = models.JSONField(default=dict, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"Sub #{self.id} by {self.student.roll_number} on Q{self.question_id} - {self.status}"

    @property
    def effective_marks(self):
        if self.manual_override_marks is not None:
            return self.manual_override_marks
        return self.marks_awarded


class AssessmentSecurityEvent(models.Model):
    class EventType(models.TextChoices):
        FULLSCREEN_EXIT = 'FULLSCREEN_EXIT', 'Exited Full Screen Mode'
        TAB_SWITCH = 'TAB_SWITCH', 'Switched Browser Tab'
        WINDOW_BLUR = 'WINDOW_BLUR', 'Window Lost Focus'
        DEVTOOLS_OPEN = 'DEVTOOLS_OPEN', 'Opened Developer Tools'
        PASTE_DETECTED = 'PASTE_DETECTED', 'Clipboard Paste Detected'

    attempt = models.ForeignKey(StudentAssessmentAttempt, on_delete=models.CASCADE, related_name='security_events', null=True, blank=True)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='assessment_security_events')
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='security_events')
    event_type = models.CharField(max_length=50, choices=EventType.choices)
    timestamp = models.DateTimeField(default=timezone.now)
    details = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.student.roll_number} - {self.get_event_type_display()} at {self.timestamp}"
