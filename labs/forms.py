from django import forms
from django.utils import timezone
from .models import Lab, LabSession, LabAttendance
from accounts.models import validate_batch_format, get_batch_choices


class LabForm(forms.ModelForm):
    class Meta:
        model = Lab
        fields = ['name', 'code', 'department', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Data Structures Lab'}),
            'code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. CS201L'}),
            'department': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Department'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Optional description'}),
        }


class LabSessionForm(forms.ModelForm):
    class Meta:
        model = LabSession
        fields = ['lab', 'session_title', 'batch', 'date', 'start_time', 'end_time', 'verification_code', 'is_active']
        widgets = {
            'lab': forms.Select(attrs={'class': 'form-input'}),
            'session_title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Lab 4: Binary Trees & Graphs'}),
            'batch': forms.Select(attrs={'class': 'form-input'}, choices=get_batch_choices()),
            'date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
            'verification_code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Optional 6-digit PIN'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def clean_batch(self):
        batch = self.cleaned_data['batch'].strip().upper()
        if not validate_batch_format(batch):
            raise forms.ValidationError('Batch must follow BATCH YYYY-YY format (e.g. BATCH 2025-29).')
        return batch

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_time')
        end = cleaned.get('end_time')
        if start and end and start >= end:
            self.add_error('end_time', 'Session end time must be after start time.')
        return cleaned


class AttendanceOverrideForm(forms.ModelForm):
    class Meta:
        model = LabAttendance
        fields = ['status', 'override_reason']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-input'}),
            'override_reason': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Mandatory audit reason for manual correction'}),
        }

    def clean_override_reason(self):
        reason = self.cleaned_data.get('override_reason', '').strip()
        if not reason:
            raise forms.ValidationError('A reason must be provided for audit logging when overriding attendance.')
        return reason
