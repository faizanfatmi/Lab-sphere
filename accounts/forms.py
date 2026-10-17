from django import forms
from .models import User, StudentProfile, TeacherProfile, validate_batch_format, get_batch_choices


class StudentRegistrationForm(forms.Form):
    full_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'placeholder': 'Full Name', 'autocomplete': 'name'})
    )
    roll_number = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'placeholder': 'University Roll Number', 'autocomplete': 'off'})
    )
    batch = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-input'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['batch'].choices = get_batch_choices()
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={'placeholder': 'Password (min 8 characters)', 'autocomplete': 'new-password'})
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password', 'autocomplete': 'new-password'})
    )

    def clean_full_name(self):
        return self.cleaned_data['full_name'].strip()

    def clean_roll_number(self):
        roll = self.cleaned_data['roll_number'].strip()
        if StudentProfile.objects.filter(roll_number=roll).exists():
            raise forms.ValidationError('This roll number is already registered.')
        return roll

    def clean_batch(self):
        batch = self.cleaned_data['batch'].strip().upper()
        if not validate_batch_format(batch):
            raise forms.ValidationError(
                'Invalid batch format. Use: BATCH YYYY-YY (e.g. BATCH 2025-29), '
                'where the end is start year + 4.'
            )
        return batch

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get('password')
        cpw = cleaned.get('confirm_password')
        if pw and cpw and pw != cpw:
            self.add_error('confirm_password', 'Passwords do not match.')
        return cleaned

    def save(self):
        data = self.cleaned_data
        user = User.objects.create_user(
            username=f"student_{data['roll_number']}",
            password=data['password'],
            role=User.Role.STUDENT,
        )
        StudentProfile.objects.create(
            user=user,
            full_name=data['full_name'],
            roll_number=data['roll_number'],
            batch=data['batch'],
        )
        return user


class StudentLoginForm(forms.Form):
    name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'placeholder': 'Full Name', 'autocomplete': 'name'})
    )
    batch = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-input'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['batch'].choices = get_batch_choices()
    roll_number = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'placeholder': 'University Roll Number', 'autocomplete': 'off'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'autocomplete': 'current-password'})
    )

    def clean_name(self):
        return self.cleaned_data['name'].strip()

    def clean_batch(self):
        return self.cleaned_data['batch'].strip().upper()

    def clean_roll_number(self):
        return self.cleaned_data['roll_number'].strip()


class TeacherRegistrationForm(forms.Form):
    teacher_id = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'placeholder': 'Teacher ID', 'autocomplete': 'off'})
    )
    full_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'placeholder': 'Full Name', 'autocomplete': 'name'})
    )
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={'placeholder': 'Password (min 8 characters)', 'autocomplete': 'new-password'})
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password', 'autocomplete': 'new-password'})
    )
    registration_code = forms.CharField(
        max_length=100,
        widget=forms.PasswordInput(attrs={'placeholder': 'Registration Code', 'autocomplete': 'off'})
    )

    def clean_teacher_id(self):
        tid = self.cleaned_data['teacher_id'].strip()
        if TeacherProfile.objects.filter(teacher_id=tid).exists():
            raise forms.ValidationError('This Teacher ID is already registered.')
        return tid

    def clean_full_name(self):
        return self.cleaned_data['full_name'].strip()

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get('password')
        cpw = cleaned.get('confirm_password')
        if pw and cpw and pw != cpw:
            self.add_error('confirm_password', 'Passwords do not match.')
        return cleaned

    def save(self):
        data = self.cleaned_data
        user = User.objects.create_user(
            username=f"teacher_{data['teacher_id']}",
            password=data['password'],
            role=User.Role.TEACHER,
        )
        TeacherProfile.objects.create(
            user=user,
            full_name=data['full_name'],
            teacher_id=data['teacher_id'],
        )
        return user


class TeacherLoginForm(forms.Form):
    name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'placeholder': 'Full Name', 'autocomplete': 'name'})
    )
    teacher_id = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'placeholder': 'Teacher ID', 'autocomplete': 'off'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'autocomplete': 'current-password'})
    )

    def clean_name(self):
        return self.cleaned_data['name'].strip()

    def clean_teacher_id(self):
        return self.cleaned_data['teacher_id'].strip()
