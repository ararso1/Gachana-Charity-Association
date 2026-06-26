from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from .models import StaffDesignation, User


def user_has_staff_module(user, module):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.role == User.Role.ADMIN:
        return True
    if user.role != User.Role.STAFF:
        return False

    profile = getattr(user, 'staff_profile', None)
    return bool(profile and profile.has_module(module))


def user_can_manage_donations(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.role == User.Role.ADMIN:
        return True
    if user.role == User.Role.STAFF:
        profile = getattr(user, 'staff_profile', None)
        return bool(
            profile
            and profile.is_active
            and (
                profile.can_manage_donations
                or profile.has_module(StaffDesignation.Module.DONATIONS)
            )
        )
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


def staff_module_required(module):
    """Allow admins and staff assigned a designation with the requested module."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect('login')

            if user_has_staff_module(user, module):
                return view_func(request, *args, **kwargs)

            messages.error(request, 'You do not have permission to access that module.')
            if user.role == User.Role.STAFF:
                return redirect('staff_dashboard')
            return redirect('portal_home')

        return wrapper

    return decorator


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
