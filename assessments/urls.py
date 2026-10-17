from django.urls import path
from . import views

urlpatterns = [
    # Teacher Assessment Management
    path('teacher/assessments/', views.assessment_list_view, name='assessment_list'),
    path('teacher/assessments/create/', views.assessment_create_view, name='assessment_create'),
    path('teacher/assessments/<int:assessment_id>/', views.assessment_detail_view, name='assessment_detail'),
    path('teacher/assessments/<int:assessment_id>/edit/', views.assessment_edit_view, name='assessment_edit'),
    path('teacher/assessments/<int:assessment_id>/delete/', views.assessment_delete_view, name='assessment_delete'),
    path('teacher/assessments/<int:assessment_id>/toggle-publish/', views.assessment_toggle_publish_view, name='assessment_toggle_publish'),
    path('teacher/assessments/<int:assessment_id>/archive/', views.assessment_archive_view, name='assessment_archive'),
    path('teacher/assessments/<int:assessment_id>/submissions/', views.assessment_submissions_view, name='assessment_submissions'),
    
    # Question Management
    path('teacher/assessments/<int:assessment_id>/questions/create/', views.question_create_view, name='question_create'),
    path('teacher/questions/<int:question_id>/edit/', views.question_edit_view, name='question_edit'),
    path('teacher/questions/<int:question_id>/delete/', views.question_delete_view, name='question_delete'),
    
    # Test Cases
    path('teacher/questions/<int:question_id>/testcases/create/', views.test_case_create_view, name='test_case_create'),
    path('teacher/testcases/<int:test_case_id>/delete/', views.test_case_delete_view, name='test_case_delete'),
    
    # Submissions & Overrides
    path('teacher/submissions/<int:submission_id>/', views.submission_detail_view, name='submission_detail'),
    path('teacher/submissions/<int:submission_id>/override/', views.submission_override_view, name='submission_override'),
    
    # Individual Student Performance Detail
    path('teacher/students/<int:student_id>/performance/', views.student_performance_detail_view, name='student_performance_detail'),

    # Student Coding Interface
    path('student/assessments/<int:assessment_id>/', views.coding_assessment_view, name='coding_assessment'),

    # AJAX Execution & Autosave APIs
    path('api/run-code/', views.api_run_code, name='api_run_code'),
    path('api/submit-code/', views.api_submit_code, name='api_submit_code'),
    path('api/save-draft/', views.api_save_draft, name='api_save_draft'),
    path('api/get-draft/', views.api_get_draft, name='api_get_draft'),
    path('api/log-event/', views.api_log_security_event, name='api_log_security_event'),
]
