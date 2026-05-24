from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from .models import User


def user_can_manage_donations(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.role == User.Role.ADMIN:
        return True
    if user.role == User.Role.STAFF:
        profile = getattr(user, 'staff_profile', None)
        return bool(profile and profile.can_manage_donations)
    return False


def donation_manager_required(view_func):
    """Allow admins and staff with can_manage_donations permission."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect('login')

        if user_can_manage_donations(user):
            return view_func(request, *args, **kwargs)

        messages.error(request, 'You do not have permission to manage donations.')
        if user.role == User.Role.STAFF:
            return redirect('staff_dashboard')
        return redirect('portal_home')

    return wrapper


def role_required(*roles):
    """Restrict a view to users whose role is in *roles (or superuser)."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect('login')

            if user.is_superuser or user.role == User.Role.ADMIN:
                if User.Role.ADMIN in roles or user.role in roles:
                    return view_func(request, *args, **kwargs)

            if user.role in roles:
                return view_func(request, *args, **kwargs)

            messages.error(request, 'You do not have permission to access that page.')
            return redirect('portal_home')

        return wrapper

    return decorator
