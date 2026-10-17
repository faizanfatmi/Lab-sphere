import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from accounts.decorators import teacher_required, student_required
from accounts.models import StudentProfile
from .models import Lab, LabSession, LabAttendance
from .forms import LabForm, LabSessionForm, AttendanceOverrideForm


@teacher_required
def session_list_view(request):
    teacher = request.user.teacher_profile
    sessions = LabSession.objects.filter(teacher=teacher).select_related('lab').order_by('-date', '-start_time')
    return render(request, 'labs/session_list.html', {
        'sessions': sessions,
        'profile': teacher,
    })


@teacher_required
def session_create_view(request):
    teacher = request.user.teacher_profile
    if request.method == 'POST':
        form = LabSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.teacher = teacher
            session.save()
            messages.success(request, f"Lab session '{session.session_title}' created successfully!")
            return redirect('session_detail', session_id=session.id)
    else:
        # Prepopulate or create default lab if none exists
        if not Lab.objects.exists():
            Lab.objects.create(
                name="Computer Science Laboratory",
                code="CS101L",
                department="Computer Science & Engineering",
                created_by=teacher
            )
        form = LabSessionForm()
    
    return render(request, 'labs/session_form.html', {
        'form': form,
        'title': 'Schedule New Lab Session',
        'profile': teacher,
    })


@teacher_required
def session_detail_view(request, session_id):
    teacher = request.user.teacher_profile
    session = get_object_or_404(LabSession.objects.select_related('lab'), id=session_id, teacher=teacher)
    
    # Students belonging to session's batch
    batch_students = StudentProfile.objects.filter(batch=session.batch).order_by('roll_number')
    attendances = {att.student_id: att for att in session.attendance_records.select_related('student')}
    
    student_records = []
    present_count = 0
    for student in batch_students:
        att = attendances.get(student.id)
        is_present = att is not None and att.status == LabAttendance.Status.PRESENT
        if is_present:
            present_count += 1
        student_records.append({
            'student': student,
            'attendance': att,
            'status': att.status if att else 'ABSENT',
            'checked_in_at': att.checked_in_at if att else None,
            'manual_override': att.manual_override if att else False,
            'override_reason': att.override_reason if att else '',
        })
    
    total_students = len(batch_students)
    absent_count = total_students - present_count
    attendance_rate = round((present_count / total_students * 100), 1) if total_students > 0 else 0

    return render(request, 'labs/session_detail.html', {
        'session': session,
        'student_records': student_records,
        'present_count': present_count,
        'absent_count': absent_count,
        'total_students': total_students,
        'attendance_rate': attendance_rate,
        'profile': teacher,
    })


@teacher_required
def attendance_override_view(request, session_id, student_id):
    teacher = request.user.teacher_profile
    session = get_object_or_404(LabSession, id=session_id, teacher=teacher)
    student = get_object_or_404(StudentProfile, id=student_id)

    attendance, created = LabAttendance.objects.get_or_create(
        session=session,
        student=student,
        defaults={'status': LabAttendance.Status.ABSENT}
    )

    if request.method == 'POST':
        form = AttendanceOverrideForm(request.POST, instance=attendance)
        if form.is_valid():
            rec = form.save(commit=False)
            rec.manual_override = True
            rec.overridden_by = teacher
            rec.save()
            messages.success(request, f"Attendance for {student.full_name} updated with audit reason.")
            return redirect('session_detail', session_id=session.id)
    else:
        form = AttendanceOverrideForm(instance=attendance)

    return render(request, 'labs/attendance_override_modal.html', {
        'form': form,
        'session': session,
        'student': student,
        'profile': teacher,
    })


@teacher_required
def attendance_export_csv_view(request, session_id):
    teacher = request.user.teacher_profile
    session = get_object_or_404(LabSession.objects.select_related('lab'), id=session_id, teacher=teacher)
    
    batch_students = StudentProfile.objects.filter(batch=session.batch).order_by('roll_number')
    attendances = {att.student_id: att for att in session.attendance_records.select_related('student')}

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="attendance_{session.lab.code}_{session.date}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Roll Number', 'Student Name', 'Batch', 'Lab Code', 'Session Title', 'Date', 'Status', 'Check-in Time', 'Manual Override', 'Audit Reason'])

    for s in batch_students:
        att = attendances.get(s.id)
        status = att.status if att else 'ABSENT'
        check_time = timezone.localtime(att.checked_in_at).strftime('%Y-%m-%d %H:%M:%S') if att and att.checked_in_at else 'N/A'
        override = "Yes" if att and att.manual_override else "No"
        reason = att.override_reason if att else ""
        writer.writerow([s.roll_number, s.full_name, s.batch, session.lab.code, session.session_title, session.date, status, check_time, override, reason])

    return response


@student_required
def student_checkin_view(request, session_id):
    student = request.user.student_profile
    session = get_object_or_404(LabSession.objects.select_related('lab'), id=session_id)

    # 1. Verify Batch
    if student.batch.strip().upper() != session.batch.strip().upper():
        messages.error(request, f"This lab session is assigned to {session.batch}. You belong to {student.batch}.")
        return redirect('student_dashboard')

    # 2. Verify Session Active & Time Window
    now = timezone.localtime()
    if not session.is_active or session.date != now.date() or not (session.start_time <= now.time() <= session.end_time):
        messages.error(request, "This lab session is currently not open for attendance check-in.")
        return redirect('student_dashboard')

    # 3. Check optional verification PIN code
    if session.verification_code:
        entered_code = request.POST.get('verification_code', '').strip()
        if entered_code != session.verification_code:
            messages.error(request, "Invalid laboratory session verification PIN.")
            return redirect('student_dashboard')

    # 4. Prevent duplicate check-in
    if LabAttendance.objects.filter(session=session, student=student).exists():
        messages.warning(request, "You have already recorded your attendance for this lab session.")
        return redirect('student_dashboard')

    # 5. Record attendance with server timestamp, client IP, and device user-agent
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()
    device_info = request.META.get('HTTP_USER_AGENT', '')[:250]

    with transaction.atomic():
        LabAttendance.objects.create(
            session=session,
            student=student,
            status=LabAttendance.Status.PRESENT,
            checked_in_at=timezone.now(),
            client_ip=client_ip,
            device_info=device_info,
        )

    messages.success(request, f"Attendance successfully recorded for {session.lab.code} - {session.session_title}!")
    return redirect('student_dashboard')
