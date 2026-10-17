from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.conf import settings
from django.db import models
from .models import User, StudentProfile, TeacherProfile, get_batch_choices
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
    return render(request, 'landing.html', {
        'batch_choices': get_batch_choices(),
    })



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
    from django.utils import timezone
    from labs.models import LabSession, LabAttendance
    from assessments.models import Assessment, StudentAssessmentAttempt, Submission
    
    student = request.user.student_profile
    now = timezone.now()
    local_now = timezone.localtime()

    # 1. Attendance Metrics
    total_sessions = LabSession.objects.filter(batch=student.batch).count()
    present_sessions = LabAttendance.objects.filter(
        student=student, status=LabAttendance.Status.PRESENT
    ).count()
    attendance_rate = round((present_sessions / total_sessions * 100), 1) if total_sessions > 0 else 100.0

    # 2. Check for currently active lab session
    active_sessions = LabSession.objects.filter(
        batch=student.batch,
        is_active=True,
        date=local_now.date(),
        start_time__lte=local_now.time(),
        end_time__gte=local_now.time()
    ).select_related('lab')

    active_session_data = []
    for sess in active_sessions:
        has_checked_in = LabAttendance.objects.filter(session=sess, student=student).exists()
        active_session_data.append({
            'session': sess,
            'has_checked_in': has_checked_in,
        })

    # 3. Assessments for student's batch
    batch_assessments = Assessment.objects.filter(
        assigned_batch=student.batch,
        is_published=True,
        is_archived=False
    ).prefetch_related('questions').order_by('start_time')

    attempts = {
        att.assessment_id: att for att in
        StudentAssessmentAttempt.objects.filter(student=student)
    }

    available_assessments = []
    upcoming_assessments = []
    past_assessments = []

    total_marks_earned = 0.0
    total_possible_marks = 0.0

    for asm in batch_assessments:
        att = attempts.get(asm.id)
        status_label = 'Not Started'
        score_obtained = 0.0
        
        if att:
            score_obtained = float(att.total_score_obtained)
            status_label = att.get_status_display()
        elif now > asm.end_time:
            status_label = 'Expired'
        
        total_m = float(asm.total_marks)
        total_possible_marks += total_m
        total_marks_earned += score_obtained

        asm_info = {
            'assessment': asm,
            'status': status_label,
            'score_obtained': score_obtained,
            'total_marks': total_m,
            'question_count': asm.question_count,
            'attempt': att,
            'is_open': asm.start_time <= now <= asm.end_time,
        }

        if asm.start_time <= now <= asm.end_time:
            available_assessments.append(asm_info)
        elif now < asm.start_time:
            upcoming_assessments.append(asm_info)
        else:
            past_assessments.append(asm_info)

    # 4. Recent Submissions
    recent_submissions = (
        Submission.objects
        .filter(student=student)
        .select_related('question__assessment')
        .order_by('-submitted_at')[:8]
    )

    # 5. Recent Attendance Records
    recent_attendances = (
        LabAttendance.objects
        .filter(student=student)
        .select_related('session__lab')
        .order_by('-checked_in_at')[:6]
    )

    return render(request, 'accounts/student_dashboard.html', {
        'profile': student,
        'attendance_rate': attendance_rate,
        'present_sessions': present_sessions,
        'total_sessions': total_sessions,
        'active_session_data': active_session_data,
        'available_assessments': available_assessments,
        'upcoming_assessments': upcoming_assessments,
        'past_assessments': past_assessments,
        'recent_submissions': recent_submissions,
        'recent_attendances': recent_attendances,
        'total_marks_earned': total_marks_earned,
        'total_possible_marks': total_possible_marks,
    })


@teacher_required
def teacher_dashboard_view(request):
    from django.db.models import Count, Avg, Sum
    from labs.models import LabSession, LabAttendance
    from assessments.models import Assessment, Submission, StudentAssessmentAttempt
    
    teacher = request.user.teacher_profile

    # 1. Overall Statistics
    teacher_assessments = Assessment.objects.filter(teacher=teacher)
    total_assessments = teacher_assessments.count()
    active_assessments = [a for a in teacher_assessments if a.is_currently_active]
    
    # Unique batches taught by this teacher (from assessments or sessions)
    batches = list(teacher_assessments.values_list('assigned_batch', flat=True).distinct())
    session_batches = list(LabSession.objects.filter(teacher=teacher).values_list('batch', flat=True).distinct())
    all_batches = sorted(list(set(batches + session_batches)))

    # Students list
    students_qs = StudentProfile.objects.all()
    if all_batches:
        students_qs = students_qs.filter(batch__in=all_batches)

    # Filter/Search
    query = request.GET.get('search', '').strip()
    batch_filter = request.GET.get('batch', '').strip()
    
    if query:
        students_qs = students_qs.filter(
            models.Q(full_name__icontains=query) | models.Q(roll_number__icontains=query)
        )
    if batch_filter:
        students_qs = students_qs.filter(batch=batch_filter)

    total_students = students_qs.count()

    # Preload student performance details
    student_records = []
    teacher_sessions_count = LabSession.objects.filter(teacher=teacher).count()
    
    for s in students_qs.order_by('batch', 'roll_number')[:50]:
        # Attendance
        s_sessions = LabSession.objects.filter(batch=s.batch, teacher=teacher).count()
        s_present = LabAttendance.objects.filter(
            student=s, session__teacher=teacher, status=LabAttendance.Status.PRESENT
        ).count()
        s_att_rate = round((s_present / s_sessions * 100), 1) if s_sessions > 0 else 100.0

        # Submissions & Marks
        s_attempts = StudentAssessmentAttempt.objects.filter(student=s, assessment__teacher=teacher)
        s_total_marks = sum(float(a.total_score_obtained) for a in s_attempts)
        s_completed_q = Submission.objects.filter(student=s, question__teacher=teacher, status='ACCEPTED').values('question').distinct().count()

        student_records.append({
            'student': s,
            'attendance_rate': s_att_rate,
            'completed_questions': s_completed_q,
            'total_marks': s_total_marks,
            'attempts_count': s_attempts.count(),
        })

    # Average score
    all_attempts = StudentAssessmentAttempt.objects.filter(assessment__teacher=teacher)
    avg_score = all_attempts.aggregate(avg=Avg('total_score_obtained'))['avg'] or 0.0

    # Overall Attendance Rate
    total_att_records = LabAttendance.objects.filter(session__teacher=teacher).count()
    present_att_records = LabAttendance.objects.filter(session__teacher=teacher, status=LabAttendance.Status.PRESENT).count()
    overall_attendance_rate = round((present_att_records / total_att_records * 100), 1) if total_att_records > 0 else 100.0

    # Recent assessments & lab sessions
    recent_assessments = teacher_assessments.order_by('-created_at')[:5]
    recent_sessions = LabSession.objects.filter(teacher=teacher).select_related('lab').order_by('-date', '-start_time')[:5]

    return render(request, 'accounts/teacher_dashboard.html', {
        'profile': teacher,
        'total_students': total_students,
        'active_assessments_count': len(active_assessments),
        'total_assessments': total_assessments,
        'average_score': round(avg_score, 1),
        'overall_attendance_rate': overall_attendance_rate,
        'student_records': student_records,
        'all_batches': all_batches,
        'selected_batch': batch_filter,
        'search_query': query,
        'recent_assessments': recent_assessments,
        'recent_sessions': recent_sessions,
    })
