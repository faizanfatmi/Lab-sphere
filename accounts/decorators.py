from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def student_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to access this page.')
            return redirect('landing')
        if not request.user.is_student:
            messages.error(request, 'Access denied. This page is for students only.')
            return redirect('landing')
        return view_func(request, *args, **kwargs)
    return wrapper


def teacher_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to access this page.')
            return redirect('landing')
        if not request.user.is_teacher:
            messages.error(request, 'Access denied. This page is for teachers only.')
            return redirect('landing')
        return view_func(request, *args, **kwargs)
    return wrapper
