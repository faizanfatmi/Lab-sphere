from django import forms
from django.utils import timezone
from .models import Assessment, Question, TestCase, Submission
from accounts.models import validate_batch_format, get_batch_choices


class AssessmentForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = [
            'title', 'lab', 'assigned_batch', 'duration_minutes',
            'start_time', 'end_time', 'pass_marks', 'is_published', 'description'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Midterm Coding Assessment'}),
            'lab': forms.Select(attrs={'class': 'form-input'}),
            'assigned_batch': forms.Select(attrs={'class': 'form-input'}, choices=get_batch_choices()),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-input', 'min': 5, 'max': 360}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'pass_marks': forms.NumberInput(attrs={'class': 'form-input', 'min': 0}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Optional guidelines'}),
        }

    def clean_assigned_batch(self):
        batch = self.cleaned_data['assigned_batch'].strip().upper()
        if not validate_batch_format(batch):
            raise forms.ValidationError('Batch must follow BATCH YYYY-YY format (e.g. BATCH 2025-29).')
        return batch

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_time')
        end = cleaned.get('end_time')
        if start and end and start >= end:
            self.add_error('end_time', 'End time must be strictly after start time.')
        return cleaned


MARKS_CHOICES = [
    (2, '2 Marks'),
    (5, '5 Marks'),
    (10, '10 Marks'),
    (15, '15 Marks'),
    (20, '20 Marks'),
    (25, '25 Marks'),
    (50, '50 Marks'),
    (100, '100 Marks'),
]


class QuestionForm(forms.ModelForm):
    max_marks = forms.ChoiceField(
        choices=MARKS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-input'}),
        initial=10,
        label="Marks"
    )

    class Meta:
        model = Question
        fields = [
            'title', 'difficulty', 'max_marks', 'order',
            'problem_statement', 'input_format', 'output_format',
            'constraints', 'sample_explanation', 'allowed_languages',
            'time_limit_seconds', 'memory_limit_mb',
            'c_starter_code', 'cpp_starter_code', 'java_starter_code', 'python_starter_code'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Invert a Binary Tree'}),
            'difficulty': forms.Select(attrs={'class': 'form-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-input', 'min': '1'}),
            'problem_statement': forms.Textarea(attrs={'class': 'form-input', 'rows': 6, 'placeholder': 'Detailed problem description...'}),
            'input_format': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'e.g. First line contains N...'}),
            'output_format': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Print the answer...'}),
            'constraints': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': '1 <= N <= 10^5'}),
            'sample_explanation': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Explanation for sample testcase...'}),
            'allowed_languages': forms.TextInput(attrs={'class': 'form-input', 'value': 'c,cpp,java,python'}),
            'time_limit_seconds': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.1', 'min': '0.5', 'max': '10.0'}),
            'memory_limit_mb': forms.NumberInput(attrs={'class': 'form-input', 'min': '64', 'max': '512'}),
            'c_starter_code': forms.Textarea(attrs={'class': 'form-input font-mono', 'rows': 5}),
            'cpp_starter_code': forms.Textarea(attrs={'class': 'form-input font-mono', 'rows': 5}),
            'java_starter_code': forms.Textarea(attrs={'class': 'form-input font-mono', 'rows': 5}),
            'python_starter_code': forms.Textarea(attrs={'class': 'form-input font-mono', 'rows': 5}),
        }

    def clean_max_marks(self):
        val = self.cleaned_data.get('max_marks')
        try:
            return float(val)
        except (ValueError, TypeError):
            return 10.0

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('problem_statement') and cleaned.get('title'):
            cleaned['problem_statement'] = cleaned.get('title')
        if not cleaned.get('input_format'):
            cleaned['input_format'] = "Standard input format"
        if not cleaned.get('output_format'):
            cleaned['output_format'] = "Standard output format"
        return cleaned


class TestCaseForm(forms.ModelForm):
    class Meta:
        model = TestCase
        fields = ['input_data', 'expected_output', 'is_sample', 'weight_percentage', 'order']
        widgets = {
            'input_data': forms.Textarea(attrs={'class': 'form-input font-mono', 'rows': 3, 'placeholder': 'Standard input data'}),
            'expected_output': forms.Textarea(attrs={'class': 'form-input font-mono', 'rows': 3, 'placeholder': 'Expected standard output'}),
            'is_sample': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'weight_percentage': forms.NumberInput(attrs={'class': 'form-input', 'step': '1', 'min': '0', 'max': '100'}),
            'order': forms.NumberInput(attrs={'class': 'form-input', 'min': '1'}),
        }


class SubmissionOverrideForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['manual_override_marks', 'override_reason']
        widgets = {
            'manual_override_marks': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.5', 'min': '0'}),
            'override_reason': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Mandatory audit reason for score override'}),
        }

    def clean_override_reason(self):
        reason = self.cleaned_data.get('override_reason', '').strip()
        if not reason:
            raise forms.ValidationError('An audit reason must be supplied for manual score override.')
        return reason
