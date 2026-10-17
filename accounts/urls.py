from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('student/register/', views.student_register_view, name='student_register'),
    path('student/login/', views.student_login_view, name='student_login'),
    path('teacher/register/', views.teacher_register_view, name='teacher_register'),
    path('teacher/login/', views.teacher_login_view, name='teacher_login'),
    path('logout/', views.logout_view, name='logout'),
    path('student/dashboard/', views.student_dashboard_view, name='student_dashboard'),
    path('teacher/dashboard/', views.teacher_dashboard_view, name='teacher_dashboard'),
]
