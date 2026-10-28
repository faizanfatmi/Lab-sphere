import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden, Http404
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.db import transaction
from django.db.models import Sum, Avg, Count, Q

from accounts.decorators import teacher_required, student_required
from accounts.models import StudentProfile, User
from labs.models import Lab, LabSession, LabAttendance
from .models import (
    Assessment, Question, TestCase, StudentAssessmentAttempt,
    CodeDraft, Submission, AssessmentSecurityEvent
)
from .forms import AssessmentForm, QuestionForm, TestCaseForm, SubmissionOverrideForm, MARKS_CHOICES
from .services.execution import evaluate_test_cases, get_executor, ExecutionResult


# ==========================================
# TEACHER VIEWS: ASSESSMENT & QUESTION MGMT
# ==========================================

@teacher_required
def assessment_list_view(request):
    teacher = request.user.teacher_profile
    assessments = Assessment.objects.filter(teacher=teacher).annotate(
        q_count=Count('questions', distinct=True),
        attempt_count=Count('student_attempts', distinct=True)
    ).order_by('-created_at')
    
    return render(request, 'assessments/assessment_list.html', {
        'assessments': assessments,
        'profile': teacher,
    })


@teacher_required
def assessment_create_view(request):
    teacher = request.user.teacher_profile
    if request.method == 'POST':
        form = AssessmentForm(request.POST)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.teacher = teacher
            assessment.save()
            messages.success(request, f"Assessment '{assessment.title}' created successfully!")
            return redirect('assessment_detail', assessment_id=assessment.id)
    else:
        form = AssessmentForm()

    return render(request, 'assessments/assessment_form.html', {
        'form': form,
        'title': 'Create New Assessment',
        'profile': teacher,
    })


@teacher_required
def assessment_detail_view(request, assessment_id):
    teacher = request.user.teacher_profile
    assessment = get_object_or_404(
        Assessment.objects.prefetch_related('questions__test_cases'),
        id=assessment_id,
        teacher=teacher
    )
    questions = assessment.questions.all().order_by('order', 'id')
    submissions_count = Submission.objects.filter(question__assessment=assessment).count()
    attempts_count = assessment.student_attempts.count()

    return render(request, 'assessments/assessment_detail.html', {
        'assessment': assessment,
        'questions': questions,
        'submissions_count': submissions_count,
        'attempts_count': attempts_count,
        'profile': teacher,
    })


@teacher_required
def assessment_edit_view(request, assessment_id):
    teacher = request.user.teacher_profile
    assessment = get_object_or_404(Assessment, id=assessment_id, teacher=teacher)
    
    if request.method == 'POST':
        form = AssessmentForm(request.POST, instance=assessment)
        if form.is_valid():
            form.save()
            messages.success(request, f"Assessment '{assessment.title}' updated successfully.")
            return redirect('assessment_detail', assessment_id=assessment.id)
    else:
        form = AssessmentForm(instance=assessment)

    return render(request, 'assessments/assessment_form.html', {
        'form': form,
        'title': f'Edit Assessment: {assessment.title}',
        'profile': teacher,
    })


@teacher_required
def assessment_toggle_publish_view(request, assessment_id):
    teacher = request.user.teacher_profile
    assessment = get_object_or_404(Assessment, id=assessment_id, teacher=teacher)
    
    if assessment.questions.count() == 0:
        messages.error(request, "Cannot publish an assessment without any coding questions.")
        return redirect('assessment_detail', assessment_id=assessment.id)

    assessment.is_published = not assessment.is_published
    assessment.save(update_fields=['is_published'])
    status_str = "Published and available to students" if assessment.is_published else "Unpublished (Draft)"
    messages.success(request, f"Assessment '{assessment.title}' is now {status_str}.")
    return redirect('assessment_detail', assessment_id=assessment.id)


@teacher_required
def assessment_archive_view(request, assessment_id):
    teacher = request.user.teacher_profile
    assessment = get_object_or_404(Assessment, id=assessment_id, teacher=teacher)
    assessment.is_archived = not assessment.is_archived
    assessment.save(update_fields=['is_archived'])
    msg = "archived" if assessment.is_archived else "restored from archive"
    messages.success(request, f"Assessment '{assessment.title}' has been {msg}.")
    return redirect('assessment_detail', assessment_id=assessment.id)


@teacher_required
def assessment_delete_view(request, assessment_id):
    teacher = request.user.teacher_profile
    assessment = get_object_or_404(Assessment, id=assessment_id, teacher=teacher)
    if request.method == 'POST':
        title = assessment.title
        assessment.delete()
        messages.success(request, f"Assessment '{title}' deleted successfully.")
        return redirect('assessment_list')
    return render(request, 'assessments/confirm_delete.html', {
        'item_name': f"Assessment: {assessment.title}",
        'cancel_url': 'assessment_detail',
        'cancel_id': assessment.id,
        'profile': teacher,
    })


# Question & Test Case views
@teacher_required
def question_create_view(request, assessment_id):
    teacher = request.user.teacher_profile
    assessment = get_object_or_404(Assessment, id=assessment_id, teacher=teacher)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        # Check if quick questions form was submitted
        if action == 'quick_add' or 'question_title[]' in request.POST or 'question_title' in request.POST:
            titles = request.POST.getlist('question_title[]') or request.POST.getlist('question_title')
            marks_list = request.POST.getlist('question_marks[]') or request.POST.getlist('question_marks')
            
            created_count = 0
            current_order = assessment.questions.count()
            for idx, title in enumerate(titles):
                t = title.strip()
                if not t:
                    continue
                try:
                    m = float(marks_list[idx]) if idx < len(marks_list) else 10.0
                except (ValueError, TypeError):
                    m = 10.0
                current_order += 1
                Question.objects.create(
                    assessment=assessment,
                    teacher=teacher,
                    title=t[:250],
                    problem_statement=t,
                    max_marks=m,
                    order=current_order,
                    input_format="Standard input format",
                    output_format="Standard output format",
                    difficulty=Question.Difficulty.MEDIUM,
                )
                created_count += 1
                
            if created_count > 0:
                messages.success(request, f"Successfully added {created_count} question(s) to '{assessment.title}'!")
                return redirect('assessment_detail', assessment_id=assessment.id)
            else:
                messages.error(request, "Please enter at least one question title.")
        else:
            form = QuestionForm(request.POST)
            if form.is_valid():
                question = form.save(commit=False)
                question.assessment = assessment
                question.teacher = teacher
                question.save()
                messages.success(request, f"Question '{question.title}' added to assessment!")
                return redirect('assessment_detail', assessment_id=assessment.id)
    else:
        next_order = assessment.questions.count() + 1
        form = QuestionForm(initial={'order': next_order})

    return render(request, 'assessments/question_form.html', {
        'form': form,
        'assessment': assessment,
        'marks_choices': MARKS_CHOICES,
        'title': f"Add Questions to {assessment.title}",
        'profile': teacher,
    })


@teacher_required
def question_edit_view(request, question_id):
    teacher = request.user.teacher_profile
    question = get_object_or_404(Question, id=question_id, teacher=teacher)
    
    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()
            messages.success(request, f"Question '{question.title}' updated successfully.")
            return redirect('assessment_detail', assessment_id=question.assessment_id)
    else:
        form = QuestionForm(instance=question)

    test_case_form = TestCaseForm()
    test_cases = question.test_cases.all().order_by('order', 'id')

    return render(request, 'assessments/question_form.html', {
        'form': form,
        'question': question,
        'assessment': question.assessment,
        'test_cases': test_cases,
        'test_case_form': test_case_form,
        'title': f"Edit Question: {question.title}",
        'profile': teacher,
    })


@teacher_required
def question_delete_view(request, question_id):
    teacher = request.user.teacher_profile
    question = get_object_or_404(Question, id=question_id, teacher=teacher)
    assessment_id = question.assessment_id
    if request.method == 'POST':
        title = question.title
        question.delete()
        messages.success(request, f"Question '{title}' deleted.")
        return redirect('assessment_detail', assessment_id=assessment_id)
    return render(request, 'assessments/confirm_delete.html', {
        'item_name': f"Question: {question.title}",
        'cancel_url': 'assessment_detail',
        'cancel_id': assessment_id,
        'profile': teacher,
    })


@teacher_required
def test_case_create_view(request, question_id):
    teacher = request.user.teacher_profile
    question = get_object_or_404(Question, id=question_id, teacher=teacher)
    
    if request.method == 'POST':
        form = TestCaseForm(request.POST)
        if form.is_valid():
            tc = form.save(commit=False)
            tc.question = question
            tc.save()
            kind = "Sample" if tc.is_sample else "Private"
            messages.success(request, f"{kind} testcase added to question.")
    return redirect('question_edit', question_id=question.id)


@teacher_required
def test_case_delete_view(request, test_case_id):
    teacher = request.user.teacher_profile
    tc = get_object_or_404(TestCase, id=test_case_id, question__teacher=teacher)
    question_id = tc.question_id
    tc.delete()
    messages.success(request, "Test case deleted.")
    return redirect('question_edit', question_id=question_id)


# Submissions & Manual Overrides
@teacher_required
def assessment_submissions_view(request, assessment_id):
    teacher = request.user.teacher_profile
    assessment = get_object_or_404(Assessment, id=assessment_id, teacher=teacher)
    
    submissions = (
        Submission.objects
        .filter(question__assessment=assessment)
        .select_related('student', 'question', 'overridden_by')
        .order_by('-submitted_at')
    )

    # Filter by student or question if provided in query params
    roll_filter = request.GET.get('roll', '').strip()
    if roll_filter:
        submissions = submissions.filter(student__roll_number__icontains=roll_filter)
    
    q_filter = request.GET.get('question', '').strip()
    if q_filter.isdigit():
        submissions = submissions.filter(question_id=int(q_filter))

    questions = assessment.questions.all()

    return render(request, 'assessments/submissions_list.html', {
        'assessment': assessment,
        'submissions': submissions,
        'questions': questions,
        'roll_filter': roll_filter,
        'q_filter': q_filter,
        'profile': teacher,
    })


@teacher_required
def submission_detail_view(request, submission_id):
    teacher = request.user.teacher_profile
    submission = get_object_or_404(
        Submission.objects.select_related('student', 'question__assessment', 'overridden_by'),
        id=submission_id,
        question__teacher=teacher
    )
    
    # Associated security events for this student on this assessment
    security_events = AssessmentSecurityEvent.objects.filter(
        student=submission.student,
        assessment=submission.question.assessment
    ).order_by('-timestamp')

    override_form = SubmissionOverrideForm(instance=submission)

    return render(request, 'assessments/submission_detail.html', {
        'submission': submission,
        'security_events': security_events,
        'override_form': override_form,
        'profile': teacher,
    })


@teacher_required
def submission_override_view(request, submission_id):
    teacher = request.user.teacher_profile
    submission = get_object_or_404(Submission, id=submission_id, question__teacher=teacher)
    
    if request.method == 'POST':
        form = SubmissionOverrideForm(request.POST, instance=submission)
        if form.is_valid():
            with transaction.atomic():
                sub = form.save(commit=False)
                sub.overridden_by = teacher
                sub.save()
                # Recalculate student's attempt total score
                if sub.attempt:
                    sub.attempt.recalculate_total_score()
            messages.success(request, f"Score for Submission #{submission.id} successfully overridden with audit record.")
    return redirect('submission_detail', submission_id=submission.id)


@teacher_required
def student_performance_detail_view(request, student_id):
    teacher = request.user.teacher_profile
    student = get_object_or_404(StudentProfile, id=student_id)
    
    # All submissions by this student for teacher's assessments
    submissions = (
        Submission.objects
        .filter(student=student, question__teacher=teacher)
        .select_related('question__assessment')
        .order_by('-submitted_at')
    )

    # Assessments attempted
    attempts = (
        StudentAssessmentAttempt.objects
        .filter(student=student, assessment__teacher=teacher)
        .select_related('assessment')
        .order_by('-started_at')
    )

    # Attendance statistics
    total_sessions = LabSession.objects.filter(batch=student.batch, teacher=teacher).count()
    present_sessions = LabAttendance.objects.filter(
        student=student, session__teacher=teacher, status=LabAttendance.Status.PRESENT
    ).count()
    att_rate = round((present_sessions / total_sessions * 100), 1) if total_sessions > 0 else 0

    # Total score calculation
    total_marks_obtained = sum(float(a.total_score_obtained) for a in attempts)
    total_max_marks = sum(float(a.assessment.total_marks) for a in attempts)

    return render(request, 'assessments/student_performance_detail.html', {
        'student': student,
        'submissions': submissions,
        'attempts': attempts,
        'attendance_rate': att_rate,
        'present_sessions': present_sessions,
        'total_sessions': total_sessions,
        'total_marks_obtained': total_marks_obtained,
        'total_max_marks': total_max_marks,
        'profile': teacher,
    })


# ==========================================
# STUDENT VIEWS: LEETCODE CODING INTERFACE
# ==========================================

@student_required
def coding_assessment_view(request, assessment_id):
    student = request.user.student_profile
    assessment = get_object_or_404(
        Assessment.objects.prefetch_related('questions__test_cases'),
        id=assessment_id
    )

    # 1. Validate Batch Assignment
    if student.batch.strip().upper() != assessment.assigned_batch.strip().upper():
        messages.error(request, f"This assessment is designated for {assessment.assigned_batch}. Access denied.")
        return redirect('student_dashboard')

    # 2. Validate Publishing & Window
    now = timezone.now()
    if not assessment.is_published or assessment.is_archived:
        messages.error(request, "This assessment is currently unavailable.")
        return redirect('student_dashboard')
    
    if now < assessment.start_time:
        messages.warning(request, f"This assessment will open on {timezone.localtime(assessment.start_time).strftime('%b %d, %Y at %I:%M %p')}.")
        return redirect('student_dashboard')
    
    if now > assessment.end_time:
        messages.error(request, "This assessment has expired.")
        return redirect('student_dashboard')

    # 3. Get or create StudentAssessmentAttempt
    attempt, created = StudentAssessmentAttempt.objects.get_or_create(
        assessment=assessment,
        student=student,
        defaults={'status': StudentAssessmentAttempt.Status.IN_PROGRESS}
    )

    questions = list(assessment.questions.all().order_by('order', 'id'))
    if not questions:
        messages.error(request, "This assessment has no questions configured.")
        return redirect('student_dashboard')

    # Active question selection
    active_q_id = request.GET.get('q')
    active_question = None
    if active_q_id and active_q_id.isdigit():
        for q in questions:
            if q.id == int(active_q_id):
                active_question = q
                break
    if not active_question:
        active_question = questions[0]

    # Only expose SAMPLE test cases to student view! Private test cases are hidden!
    sample_test_cases = active_question.test_cases.filter(is_sample=True).order_by('order')

    # Load initial code draft for this question (default python or student's latest draft)
    latest_draft = CodeDraft.objects.filter(student=student, question=active_question).order_by('-updated_at').first()
    selected_language = latest_draft.language if latest_draft else 'python'
    
    starter_codes = {
        'c': getattr(active_question, 'c_starter_code', '') or "// C Solution\n#include <stdio.h>\n\nint main() {\n    // Write your code here\n    \n    return 0;\n}",
        'cpp': active_question.cpp_starter_code or "// C++ Solution\n#include <iostream>\nusing namespace std;\n\nint main() {\n    // Write your code here\n    \n    return 0;\n}",
        'java': active_question.java_starter_code or "// Java Solution\nimport java.util.Scanner;\n\npublic class Solution {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        // Write your code here\n        \n    }\n}",
        'python': active_question.python_starter_code or "# Python Solution\ndef main():\n    # Write your code here\n    pass\n\nif __name__ == '__main__':\n    main()",
    }
    initial_code = latest_draft.code if latest_draft else starter_codes.get(selected_language, starter_codes['python'])

    # Find current question index and prev/next questions
    q_index = 0
    for idx, q in enumerate(questions):
        if q.id == active_question.id:
            q_index = idx
            break
    prev_question = questions[q_index - 1] if q_index > 0 else None
    next_question = questions[q_index + 1] if q_index < len(questions) - 1 else None

    # Check remaining time in seconds
    remaining_seconds = max(0, int((assessment.end_time - now).total_seconds()))

    assessment_data = {
        'question_id': active_question.id,
        'assessment_id': assessment.id,
        'attempt_id': attempt.id,
        'initial_code': initial_code,
        'selected_language': selected_language,
        'starter_codes': starter_codes,
    }

    return render(request, 'assessments/coding_interface.html', {
        'assessment': assessment,
        'attempt': attempt,
        'questions': questions,
        'active_question': active_question,
        'q_index': q_index + 1,
        'prev_question': prev_question,
        'next_question': next_question,
        'sample_test_cases': sample_test_cases,
        'selected_language': selected_language,
        'initial_code': initial_code,
        'starter_codes_json': json.dumps(starter_codes),
        'assessment_data_json': json.dumps(assessment_data),
        'remaining_seconds': remaining_seconds,
        'profile': student,
    })


# ==========================================
# AJAX APIS: RUN CODE, SUBMIT, AUTOSAVE DRAFT
# ==========================================

@student_required
@require_POST
@csrf_protect
def api_run_code(request):
    """Run code against sample test cases or custom input without awarding marks."""
    student = request.user.student_profile
    try:
        data = json.loads(request.body)
        question_id = data.get('question_id')
        language = data.get('language', 'python').lower()
        source_code = data.get('source_code', '')
        custom_input = data.get('custom_input', None)

        question = get_object_or_404(Question, id=question_id)
        # Verify student belongs to assessment batch
        if student.batch.strip().upper() != question.assessment.assigned_batch.strip().upper():
            return JsonResponse({'error': 'Unauthorized assessment'}, status=403)

        if not source_code.strip():
            return JsonResponse({'error': 'Source code cannot be empty'}, status=400)

        # If custom input provided, run single test
        if custom_input is not None and custom_input.strip() != "":
            executor = get_executor()
            res = executor.execute(
                language=language,
                source_code=source_code,
                stdin=custom_input,
                time_limit_sec=float(question.time_limit_seconds),
                memory_limit_mb=int(question.memory_limit_mb)
            )
            return JsonResponse({
                'status': res.status,
                'stdout': res.stdout,
                'stderr': res.stderr,
                'compile_output': res.compile_output,
                'time_ms': res.time_ms,
                'memory_kb': res.memory_kb,
                'is_custom': True,
            })

        # Run against question's sample test cases only
        sample_test_cases = question.test_cases.filter(is_sample=True)
        if not sample_test_cases.exists():
            # If no sample testcases defined, execute empty stdin to verify compilation/runtime
            executor = get_executor()
            res = executor.execute(language=language, source_code=source_code, stdin="")
            return JsonResponse({
                'status': res.status,
                'stdout': res.stdout,
                'stderr': res.stderr,
                'compile_output': res.compile_output,
                'time_ms': res.time_ms,
                'test_results': [],
            })

        eval_result = evaluate_test_cases(question, language, source_code, sample_test_cases, executor=get_executor())
        return JsonResponse(eval_result)

    except Exception as e:
        return JsonResponse({'error': f'Execution failed: {str(e)}'}, status=500)


@student_required
@require_POST
@csrf_protect
def api_submit_code(request):
    """
    Evaluates solution against all private test cases, calculates score,
    and persists Submission record.
    """
    student = request.user.student_profile
    try:
        data = json.loads(request.body)
        question_id = data.get('question_id')
        language = data.get('language', 'python').lower()
        source_code = data.get('source_code', '')
        attempt_id = data.get('attempt_id')

        question = get_object_or_404(Question.objects.select_related('assessment'), id=question_id)
        assessment = question.assessment

        # Validate Batch & Assessment Window
        if student.batch.strip().upper() != assessment.assigned_batch.strip().upper():
            return JsonResponse({'error': 'Unauthorized assessment'}, status=403)
        
        if timezone.now() > assessment.end_time:
            return JsonResponse({'error': 'Assessment deadline has passed. Submissions are closed.'}, status=400)

        attempt = get_object_or_404(StudentAssessmentAttempt, id=attempt_id, student=student, assessment=assessment)

        all_test_cases = question.test_cases.all().order_by('order', 'id')
        if not all_test_cases.exists():
            return JsonResponse({'error': 'No test cases configured for this problem.'}, status=400)

        # Run evaluation against ALL test cases (private + sample)
        eval_result = evaluate_test_cases(question, language, source_code, all_test_cases, executor=get_executor())

        # Save Submission in atomic transaction
        with transaction.atomic():
            submission = Submission.objects.create(
                attempt=attempt,
                student=student,
                question=question,
                language=language,
                source_code=source_code,
                status=eval_result['status'],
                marks_awarded=eval_result['marks_awarded'],
                test_cases_passed=eval_result['passed_count'],
                total_test_cases=eval_result['total_count'],
                execution_time_ms=eval_result['execution_time_ms'],
                memory_kb=eval_result['memory_kb'],
                compiler_output=eval_result['compiler_output'],
                evaluation_details=eval_result['test_results'],
            )
            # Recalculate student's attempt score
            total_score = attempt.recalculate_total_score()

        return JsonResponse({
            'success': True,
            'submission_id': submission.id,
            'status': submission.status,
            'marks_awarded': float(submission.marks_awarded),
            'max_marks': float(question.max_marks),
            'passed_count': eval_result['passed_count'],
            'total_count': eval_result['total_count'],
            'total_score_obtained': float(total_score),
            'test_results': eval_result['test_results'],
            'compiler_output': eval_result['compiler_output'],
        })

    except Exception as e:
        return JsonResponse({'error': f'Submission error: {str(e)}'}, status=500)


@student_required
@require_POST
@csrf_protect
def api_save_draft(request):
    """Autosaves code drafts per student, question, and language."""
    student = request.user.student_profile
    try:
        data = json.loads(request.body)
        question_id = data.get('question_id')
        language = data.get('language', 'python').lower()
        source_code = data.get('source_code', '')

        question = get_object_or_404(Question, id=question_id)
        draft, created = CodeDraft.objects.update_or_create(
            student=student,
            question=question,
            language=language,
            defaults={'code': source_code}
        )
        return JsonResponse({'success': True, 'saved_at': timezone.localtime(draft.updated_at).strftime('%H:%M:%S')})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@student_required
def api_get_draft(request):
    """Retrieve saved code draft for a question and language."""
    student = request.user.student_profile
    question_id = request.GET.get('question_id')
    language = request.GET.get('language', 'python').lower()
    
    question = get_object_or_404(Question, id=question_id)
    draft = CodeDraft.objects.filter(student=student, question=question, language=language).first()
    
    if draft:
        code = draft.code
    else:
        # Default starter template
        if language == 'c':
            code = getattr(question, 'c_starter_code', '') or "// C Solution\n#include <stdio.h>\n\nint main() {\n    // Write your code here\n    \n    return 0;\n}"
        elif language == 'cpp':
            code = question.cpp_starter_code or "// C++ Solution\n#include <iostream>\nusing namespace std;\n\nint main() {\n    // Write your code here\n    \n    return 0;\n}"
        elif language == 'java':
            code = question.java_starter_code or "// Java Solution\nimport java.util.Scanner;\n\npublic class Solution {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        // Write your code here\n        \n    }\n}"
        else:
            code = question.python_starter_code or "# Python Solution\ndef main():\n    # Write your code here\n    pass\n\nif __name__ == '__main__':\n    main()"

    return JsonResponse({'code': code})


@student_required
@require_POST
@csrf_protect
def api_log_security_event(request):
    """Records browser restriction events (fullscreen exit, tab switch, window blur)."""
    student = request.user.student_profile
    try:
        data = json.loads(request.body)
        assessment_id = data.get('assessment_id')
        event_type = data.get('event_type')
        details = data.get('details', '')

        assessment = get_object_or_404(Assessment, id=assessment_id)
        attempt = StudentAssessmentAttempt.objects.filter(assessment=assessment, student=student).first()

        AssessmentSecurityEvent.objects.create(
            attempt=attempt,
            student=student,
            assessment=assessment,
            event_type=event_type,
            details=details[:250],
            timestamp=timezone.now()
        )
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
