from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.conf import settings
from .forms import (
    StudentRegistrationForm, StudentLoginForm,
    TeacherRegistrationForm, TeacherLoginForm,
)
from .decorators import student_required, teacher_required


def landing_view(request):
    if request.user.is_authenticated:
        if request.user.is_student:
            return redirect('student_dashboard')
        elif request.user.is_teacher:
            return redirect('teacher_dashboard')
    return render(request, 'landing.html')


def student_register_view(request):
    if request.method != 'POST':
        return redirect('landing')
    
    form = StudentRegistrationForm(request.POST)
    if form.is_valid():
        user = form.save()
        messages.success(request, 'Registration successful! You can now log in.')
        return redirect('landing')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                label = form.fields[field].label or field.replace('_', ' ').title()
                messages.error(request, f'{error}')
        return redirect('landing')


def student_login_view(request):
    if request.method != 'POST':
        return redirect('landing')
    
    form = StudentLoginForm(request.POST)
    if form.is_valid():
        data = form.cleaned_data
        user = authenticate(
            request,
            roll_number=data['roll_number'],
            password=data['password'],
            name=data['name'],
            batch=data['batch'],
        )
        if user is not None:
            login(request, user, backend='accounts.backends.StudentAuthBackend')
            messages.success(request, f'Welcome back, {user.student_profile.full_name}!')
            return redirect('student_dashboard')
        else:
            messages.error(request, 'Invalid credentials. Please check your details and try again.')
            return redirect('landing')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{error}')
        return redirect('landing')


def teacher_register_view(request):
    if request.method != 'POST':
        return redirect('landing')
    
    form = TeacherRegistrationForm(request.POST)
    if form.is_valid():
        # Verify registration code server-side
        code = form.cleaned_data.get('registration_code', '')
        expected = getattr(settings, 'TEACHER_REGISTRATION_SECRET', None)
        if not expected or code != expected:
            messages.error(request, 'Invalid registration code. Teacher registration requires administrator approval.')
            return redirect('landing')
        
        user = form.save()
        messages.success(request, 'Teacher registration successful! You can now log in.')
        return redirect('landing')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{error}')
        return redirect('landing')


def teacher_login_view(request):
    if request.method != 'POST':
        return redirect('landing')
    
    form = TeacherLoginForm(request.POST)
    if form.is_valid():
        data = form.cleaned_data
        user = authenticate(
            request,
            teacher_id=data['teacher_id'],
            password=data['password'],
            name=data['name'],
        )
        if user is not None:
            login(request, user, backend='accounts.backends.TeacherAuthBackend')
            messages.success(request, f'Welcome back, {user.teacher_profile.full_name}!')
            return redirect('teacher_dashboard')
        else:
            messages.error(request, 'Invalid credentials. Please check your details and try again.')
            return redirect('landing')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{error}')
        return redirect('landing')


def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
    return redirect('landing')


@student_required
def student_dashboard_view(request):
    return render(request, 'accounts/student_dashboard.html', {
        'profile': request.user.student_profile,
    })


@teacher_required
def teacher_dashboard_view(request):
    return render(request, 'accounts/teacher_dashboard.html', {
        'profile': request.user.teacher_profile,
    })
