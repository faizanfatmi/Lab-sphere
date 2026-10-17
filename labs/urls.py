from django.urls import path
from . import views

urlpatterns = [
    path('sessions/', views.session_list_view, name='session_list'),
    path('sessions/create/', views.session_create_view, name='session_create'),
    path('sessions/<int:session_id>/', views.session_detail_view, name='session_detail'),
    path('sessions/<int:session_id>/override/<int:student_id>/', views.attendance_override_view, name='attendance_override'),
    path('sessions/<int:session_id>/export/', views.attendance_export_csv_view, name='attendance_export'),
    path('sessions/<int:session_id>/checkin/', views.student_checkin_view, name='student_checkin'),
]
