from .models import Sponsor, StaffDesignation, StaffProfile, User


def public_sponsors(request):
    """Active sponsors for the public website sponsors section."""
    return {
        'public_sponsors': Sponsor.objects.publicly_visible().order_by('sort_order', 'name'),
    }


def portal_staff(request):
    if not request.user.is_authenticated:
        return {
            'staff_profile': None,
            'staff_can_manage_donations': False,
            'staff_modules': set(),
        }

    if request.user.is_superuser or request.user.role == User.Role.ADMIN:
        return {
            'staff_profile': None,
            'staff_can_manage_donations': True,
            'staff_modules': {choice[0] for choice in StaffDesignation.Module.choices},
        }

    if request.user.role != User.Role.STAFF:
        return {
            'staff_profile': None,
            'staff_can_manage_donations': False,
            'staff_modules': set(),
        }

    profile = StaffProfile.objects.prefetch_related('designations').filter(user=request.user).first()
    modules = profile.get_module_codes() if profile else set()
    return {
        'staff_profile': profile,
        'staff_can_manage_donations': StaffDesignation.Module.DONATIONS in modules,
        'staff_modules': modules,
    }
