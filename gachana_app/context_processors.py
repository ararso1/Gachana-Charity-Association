from .models import Sponsor, StaffProfile, User


def public_sponsors(request):
    """Active sponsors for the public website sponsors section."""
    return {
        'public_sponsors': Sponsor.objects.publicly_visible().order_by('sort_order', 'name'),
    }


def portal_staff(request):
    if not request.user.is_authenticated:
        return {'staff_profile': None, 'staff_can_manage_donations': False}

    if request.user.is_superuser or request.user.role == User.Role.ADMIN:
        return {'staff_profile': None, 'staff_can_manage_donations': True}

    if request.user.role != User.Role.STAFF:
        return {'staff_profile': None, 'staff_can_manage_donations': False}

    profile = StaffProfile.objects.filter(user=request.user).first()
    return {
        'staff_profile': profile,
        'staff_can_manage_donations': bool(profile and profile.can_manage_donations),
    }
