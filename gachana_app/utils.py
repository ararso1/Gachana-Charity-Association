import uuid

from django.db.models import Max
from django.utils import timezone

from .models import Donation, MemberProfile, PortalSettings, User


def get_portal_settings():
    return PortalSettings.load()


def community_donation_total():
    from django.db.models import Sum

    return (
        Donation.objects.filter(status=Donation.Status.CONFIRMED).aggregate(total=Sum('amount'))['total']
        or 0
    )


def community_goal_progress_percent(goal):
    if not goal:
        return 0
    total = community_donation_total()
    return min(100, int((total / goal) * 100))


def get_dashboard_url_name(user):
    if user.is_superuser or user.role == User.Role.ADMIN:
        return 'portal_admin_dashboard'
    if user.role == User.Role.STAFF:
        return 'staff_dashboard'
    return 'member_dashboard'


def generate_membership_id():
    last = (
        MemberProfile.objects.filter(membership_id__startswith='GCA-')
        .aggregate(Max('membership_id'))
        .get('membership_id__max')
    )
    if last:
        try:
            num = int(last.split('-')[-1]) + 1
        except ValueError:
            num = MemberProfile.objects.count() + 1
    else:
        num = 1
    return f'GCA-{num:05d}'


def generate_employee_id():
    from .models import StaffProfile

    last = (
        StaffProfile.objects.filter(employee_id__startswith='GCS-')
        .aggregate(Max('employee_id'))
        .get('employee_id__max')
    )
    if last:
        try:
            num = int(last.split('-')[-1]) + 1
        except ValueError:
            num = StaffProfile.objects.count() + 1
    else:
        num = 1
    return f'GCS-{num:05d}'


def generate_tx_ref():
    return f'gca-{uuid.uuid4().hex[:12]}'


def get_or_create_member_profile(user):
    profile, _ = MemberProfile.objects.get_or_create(
        user=user,
        defaults={'membership_id': generate_membership_id()},
    )
    return profile


def issue_membership_card_if_eligible(member_profile):
    """Issue membership card after the member's first confirmed donation."""
    if member_profile.card_issued_at:
        return False

    has_confirmed = Donation.objects.filter(
        member=member_profile.user,
        status=Donation.Status.CONFIRMED,
    ).exists()

    if has_confirmed:
        member_profile.card_issued_at = timezone.now()
        member_profile.save(update_fields=['card_issued_at', 'updated_at'])
        return True
    return False


def confirm_donation(donation, confirmed_by=None):
    donation.status = Donation.Status.CONFIRMED
    donation.confirmed_at = timezone.now()
    donation.confirmed_by = confirmed_by
    donation.save(update_fields=['status', 'confirmed_at', 'confirmed_by', 'updated_at'])
    profile = get_or_create_member_profile(donation.member)
    refresh_member_totals(profile)
    return donation


def refresh_member_totals(member_profile):
    from django.db.models import Sum

    total = (
        Donation.objects.filter(
            member=member_profile.user,
            status=Donation.Status.CONFIRMED,
        ).aggregate(total=Sum('amount'))['total']
        or 0
    )
    member_profile.total_donated = total
    member_profile.save(update_fields=['total_donated', 'updated_at'])
    issue_membership_card_if_eligible(member_profile)
    return member_profile
