import json

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from decimal import Decimal

from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
import mimetypes

from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .chapa import ChapaError, parse_webhook_payload, verify_payment, verify_webhook_signature
from .donation_service import (
    confirm_chapa_donation,
    save_manual_donation,
    start_chapa_checkout,
)
from .decorators import (
    donation_manager_required,
    role_required,
    staff_module_required,
    user_can_manage_donations,
)
from .forms import (
    ChapaDonationForm,
    DonationBankForm,
    DonationForm,
    MemberProfileForm,
    MemberSignupForm,
    PortalSettingsForm,
    StaffAdminUpdateForm,
    StaffCreateForm,
    StaffDesignationForm,
    StaffProfileAdminForm,
    StaffProfileForm,
)
from .models import (
    Donation,
    DonationBank,
    MemberProfile,
    PortalSettings,
    StaffDesignation,
    StaffProfile,
    User,
)
from .utils import (
    community_donation_total,
    community_goal_progress_percent,
    confirm_donation,
    generate_employee_id,
    generate_membership_id,
    get_dashboard_url_name,
    get_or_create_member_profile,
    get_portal_settings,
    refresh_member_totals,
)


@login_required(login_url='/login/')
def portal_home(request):
    return redirect(get_dashboard_url_name(request.user))


def member_signup(request):
    if request.user.is_authenticated:
        return redirect(get_dashboard_url_name(request.user))
    return redirect(f"{reverse('login')}?register=1")


@login_required(login_url='/login/')
@role_required(User.Role.MEMBER)
def member_dashboard(request):
    profile = get_or_create_member_profile(request.user)
    portal_settings = get_portal_settings()
    donations = request.user.donations.select_related('bank').all()[:5]
    confirmed_total = (
        request.user.donations.filter(status=Donation.Status.CONFIRMED).aggregate(t=Sum('amount'))['t'] or 0
    )
    pending_count = request.user.donations.filter(status=Donation.Status.PENDING).count()
    community_total = community_donation_total()
    goal = portal_settings.annual_giving_goal
    return render(
        request,
        'portal/member/dashboard.html',
        {
            'profile': profile,
            'portal_settings': portal_settings,
            'donations': donations,
            'confirmed_total': confirmed_total,
            'pending_count': pending_count,
            'community_total': community_total,
            'community_progress': community_goal_progress_percent(goal),
            'personal_progress': profile.progress_toward_goal(goal),
        },
    )


@login_required(login_url='/login/')
@role_required(User.Role.MEMBER)
def member_donate(request):
    profile = get_or_create_member_profile(request.user)
    portal_settings = get_portal_settings()
    banks = DonationBank.objects.filter(is_active=True)
    manual_form = DonationForm()
    chapa_form = ChapaDonationForm(member_user=request.user)
    active_tab = request.GET.get('tab', 'chapa')

    if request.method == 'POST':
        payment_type = request.POST.get('payment_type')
        active_tab = payment_type if payment_type in ('chapa', 'manual') else active_tab
        if payment_type == 'manual':
            if not banks.exists():
                messages.error(request, 'Bank transfer is not available yet. Please use Chapa or contact support.')
            else:
                manual_form = DonationForm(request.POST, request.FILES)
                if manual_form.is_valid():
                    save_manual_donation(form=manual_form, member=request.user)
                    messages.success(
                        request,
                        'Donation submitted. It will appear on your membership card once confirmed by our team.',
                    )
                    return redirect('member_donations')
        elif payment_type == 'chapa':
            chapa_form = ChapaDonationForm(request.POST, member_user=request.user)
            if chapa_form.is_valid():
                return start_chapa_checkout(
                    request,
                    amount=chapa_form.cleaned_data['amount'],
                    member=request.user,
                    email=request.user.email,
                    first_name=request.user.first_name,
                    last_name=request.user.last_name,
                    phone_number=chapa_form.cleaned_data['phone'],
                    error_redirect_name='member_donate',
                    description='Membership donation',
                )

    banks_data = [
        {
            'id': b.pk,
            'name': b.name,
            'account_name': b.account_name,
            'account_number': b.account_number,
            'branch': b.branch,
        }
        for b in banks
    ]

    return render(
        request,
        'portal/member/donate.html',
        {
            'profile': profile,
            'portal_settings': portal_settings,
            'manual_form': manual_form,
            'chapa_form': chapa_form,
            'banks': banks,
            'banks_json': json.dumps(banks_data),
            'active_tab': active_tab,
            'has_banks': banks.exists(),
        },
    )


@login_required(login_url='/login/')
@role_required(User.Role.MEMBER)
def member_donations(request):
    donations = request.user.donations.select_related('bank').all()
    return render(request, 'portal/member/donations.html', {'donations': donations})


@login_required(login_url='/login/')
@role_required(User.Role.MEMBER)
def member_profile(request):
    profile = get_or_create_member_profile(request.user)
    if request.method == 'POST':
        form = MemberProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('member_profile')
    else:
        form = MemberProfileForm(instance=request.user)
    return render(request, 'portal/member/profile.html', {'form': form, 'profile': profile})


@login_required(login_url='/login/')
@role_required(User.Role.MEMBER)
def member_card(request):
    profile = get_or_create_member_profile(request.user)
    if not profile.has_membership_card:
        messages.warning(request, 'Your membership card will be available after your first confirmed donation.')
        return redirect('member_dashboard')
    return render(request, 'portal/member/card.html', {'profile': profile, 'user': request.user})


@csrf_exempt
@require_POST
def chapa_callback(request):
    """Chapa server webhook — auto-confirms successful payments."""
    signature = request.headers.get('Chapa-Signature', '')
    if not verify_webhook_signature(request.body, signature):
        return HttpResponse('Invalid signature', status=400)

    try:
        payload = parse_webhook_payload(request.body)
    except json.JSONDecodeError:
        return HttpResponse('Invalid payload', status=400)

    tx_ref = payload.get('tx_ref') or payload.get('reference')
    status = (payload.get('status') or '').lower()
    if not tx_ref:
        return HttpResponse('Missing tx_ref', status=400)

    donation = Donation.objects.filter(chapa_tx_ref=tx_ref).first()
    if not donation:
        return HttpResponse('Donation not found', status=404)

    if status in ('success', 'successful'):
        confirm_chapa_donation(donation)
    elif status in ('failed', 'cancelled'):
        donation.status = Donation.Status.CANCELLED
        donation.save(update_fields=['status', 'updated_at'])

    return HttpResponse('OK')


def chapa_return(request, tx_ref):
    donation = get_object_or_404(Donation, chapa_tx_ref=tx_ref)

    if donation.member_id:
        if not request.user.is_authenticated or request.user.pk != donation.member_id:
            messages.info(request, 'Please sign in to view your donation status.')
            return redirect('login')
        if donation.status == Donation.Status.CONFIRMED:
            messages.success(request, 'Thank you! Your donation was confirmed and your membership card is ready.')
            return redirect('member_card')
        try:
            result = verify_payment(tx_ref)
            data = result.get('data', {})
            if data.get('status') == 'success':
                confirm_chapa_donation(donation)
                messages.success(request, 'Payment successful! Your membership card is now available.')
                return redirect('member_card')
        except ChapaError:
            pass
        messages.info(request, 'Payment is being processed. You will be notified once it is confirmed.')
        return redirect('member_donations')

    if donation.status == Donation.Status.CONFIRMED:
        messages.success(request, 'Thank you! Your donation was received successfully.')
        return redirect('donate')

    try:
        result = verify_payment(tx_ref)
        data = result.get('data', {})
        if data.get('status') == 'success':
            confirm_chapa_donation(donation)
            messages.success(request, 'Thank you! Your payment was successful.')
            return redirect(f"{reverse('donate')}?paid=1")
    except ChapaError:
        pass

    messages.info(request, 'Payment is being processed. Thank you for your support.')
    return redirect('donate')


@login_required(login_url='/login/')
@role_required(User.Role.STAFF)
def staff_dashboard(request):
    staff_profile, _ = StaffProfile.objects.get_or_create(
        user=request.user,
        defaults={'employee_id': generate_employee_id()},
    )
    pending_donations = 0
    if user_can_manage_donations(request.user):
        pending_donations = Donation.objects.filter(status=Donation.Status.PENDING).count()
    member_count = MemberProfile.objects.count()
    return render(
        request,
        'portal/staff/dashboard.html',
        {
            'staff_profile': staff_profile,
            'pending_donations': pending_donations,
            'member_count': member_count,
        },
    )


@login_required(login_url='/login/')
@role_required(User.Role.STAFF)
def staff_profile_view(request):
    staff_profile, _ = StaffProfile.objects.get_or_create(
        user=request.user,
        defaults={'employee_id': generate_employee_id()},
    )
    if request.method == 'POST':
        user_form = StaffProfileForm(request.POST, request.FILES, instance=request.user)
        if user_form.is_valid():
            user_form.save()
            messages.success(request, 'Profile updated.')
            return redirect('staff_profile')
    else:
        user_form = StaffProfileForm(instance=request.user)
    return render(
        request,
        'portal/staff/profile.html',
        {'user_form': user_form, 'staff_profile': staff_profile},
    )


@login_required(login_url='/login/')
@role_required(User.Role.STAFF)
def staff_id_card(request):
    staff_profile = get_object_or_404(
        StaffProfile.objects.select_related('designation', 'user'),
        user=request.user,
    )
    return render(request, 'portal/staff/id_card.html', {'staff_profile': staff_profile, 'user': request.user})


@login_required(login_url='/login/')
@donation_manager_required
def portal_donation_list(request):
    donations = Donation.objects.select_related('member', 'bank').order_by('-created_at')
    status_filter = request.GET.get('status')
    if status_filter:
        donations = donations.filter(status=status_filter)
    is_staff_only = (
        request.user.role == User.Role.STAFF
        and not request.user.is_superuser
    )
    base_template = (
        'portal/staff/base_staff.html'
        if is_staff_only
        else 'portal/admin/base_admin.html'
    )
    return render(
        request,
        'portal/donations/list.html',
        {
            'donations': donations,
            'status_filter': status_filter,
            'base_template': base_template,
        },
    )


@login_required(login_url='/login/')
@donation_manager_required
def portal_donation_proof(request, donation_id):
    donation = get_object_or_404(Donation, pk=donation_id)
    if not donation.manual_proof:
        raise Http404('No payment proof uploaded.')
    content_type, _ = mimetypes.guess_type(donation.manual_proof.name)
    if not content_type:
        content_type = 'application/octet-stream'
    return FileResponse(
        donation.manual_proof.open('rb'),
        content_type=content_type,
        as_attachment=False,
        filename=donation.manual_proof.name.split('/')[-1],
    )


@login_required(login_url='/login/')
@donation_manager_required
@require_POST
def portal_confirm_donation(request, donation_id):
    donation = get_object_or_404(Donation, pk=donation_id)
    if donation.status != Donation.Status.PENDING:
        message = 'Only pending donations can be confirmed.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'message': message}, status=400)
        messages.warning(request, message)
    else:
        confirm_donation(donation, confirmed_by=request.user)
        message = 'Donation confirmed. Membership card issued if eligible.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'message': message})
        messages.success(request, message)
    next_url = request.POST.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('portal_donation_list')


@login_required(login_url='/login/')
@donation_manager_required
@require_POST
def portal_reject_donation(request, donation_id):
    donation = get_object_or_404(Donation, pk=donation_id)
    if donation.status != Donation.Status.PENDING:
        message = 'Only pending donations can be rejected.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'message': message}, status=400)
        messages.warning(request, message)
    else:
        donation.status = Donation.Status.REJECTED
        donation.confirmed_by = request.user
        donation.confirmed_at = timezone.now()
        donation.save()
        message = 'Donation marked as rejected.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'message': message})
        messages.info(request, message)
    next_url = request.POST.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('portal_donation_list')


MEMBERS_PER_PAGE = 15


def _members_filters_query(request):
    params = request.GET.copy()
    params.pop('page', None)
    return params.urlencode()


@login_required(login_url='/login/')
@staff_module_required(StaffDesignation.Module.MEMBERS)
def portal_manage_members(request):
    base_qs = User.objects.filter(role=User.Role.MEMBER)
    stats = {
        'total': base_qs.count(),
        'cards_issued': MemberProfile.objects.filter(
            user__role=User.Role.MEMBER,
            card_issued_at__isnull=False,
        ).count(),
        'total_donated': MemberProfile.objects.filter(user__role=User.Role.MEMBER).aggregate(
            t=Sum('total_donated')
        )['t']
        or 0,
    }

    members_qs = base_qs.select_related('member_profile').annotate(
        donated_total=Coalesce('member_profile__total_donated', Value(Decimal('0')))
    )

    q = request.GET.get('q', '').strip()
    card = request.GET.get('card', '')
    donation = request.GET.get('donation', '')

    if q:
        members_qs = members_qs.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(email__icontains=q)
            | Q(username__icontains=q)
            | Q(phone__icontains=q)
            | Q(address__icontains=q)
            | Q(member_profile__membership_id__icontains=q)
        )

    if card == 'issued':
        members_qs = members_qs.filter(member_profile__card_issued_at__isnull=False)
    elif card == 'pending':
        members_qs = members_qs.filter(
            Q(member_profile__isnull=True) | Q(member_profile__card_issued_at__isnull=True)
        )

    if donation == 'none':
        members_qs = members_qs.filter(donated_total=0)
    elif donation == 'under_1k':
        members_qs = members_qs.filter(donated_total__gt=0, donated_total__lt=1000)
    elif donation == '1k_10k':
        members_qs = members_qs.filter(donated_total__gte=1000, donated_total__lt=10000)
    elif donation == '10k_plus':
        members_qs = members_qs.filter(donated_total__gte=10000)

    members_qs = members_qs.order_by('-date_joined')
    paginator = Paginator(members_qs, MEMBERS_PER_PAGE)
    members_page = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'portal/admin/members.html',
        {
            'members': members_page,
            'page_obj': members_page,
            'paginator': paginator,
            'stats': stats,
            'filtered_total': paginator.count,
            'filters': {
                'q': q,
                'card': card,
                'donation': donation,
            },
            'filters_query': _members_filters_query(request),
            'member_detail_url_template': reverse(
                'portal_member_detail',
                kwargs={'user_id': 0},
            ),
            'can_manage_donations': user_can_manage_donations(request.user),
        },
    )


@login_required(login_url='/login/')
@staff_module_required(StaffDesignation.Module.MEMBERS)
def portal_member_detail(request, user_id):
    user = get_object_or_404(
        User.objects.select_related('member_profile'),
        pk=user_id,
        role=User.Role.MEMBER,
    )
    profile = getattr(user, 'member_profile', None)
    donations = Donation.objects.filter(member=user).select_related('bank').order_by('-created_at')[:8]
    donation_stats = Donation.objects.filter(member=user).aggregate(
        confirmed=Count('id', filter=Q(status=Donation.Status.CONFIRMED)),
        pending=Count('id', filter=Q(status=Donation.Status.PENDING)),
    )
    can_manage_donations = user_can_manage_donations(request.user)

    return JsonResponse(
        {
            'id': user.pk,
            'full_name': user.get_full_name() or user.username,
            'username': user.username,
            'email': user.email,
            'phone': user.phone or '',
            'address': user.address or '',
            'photo_url': user.photo.url if user.photo else '',
            'membership_id': profile.membership_id if profile else '',
            'total_donated': float(profile.total_donated) if profile else 0,
            'has_card': profile.has_membership_card if profile else False,
            'card_issued_at': profile.card_issued_at.strftime('%B %d, %Y') if profile and profile.card_issued_at else '',
            'date_joined': user.date_joined.strftime('%B %d, %Y'),
            'donation_stats': donation_stats,
            'can_manage_donations': can_manage_donations,
            'recent_donations': [
                {
                    'id': d.pk,
                    'amount': float(d.amount),
                    'currency': d.currency,
                    'status': d.get_status_display(),
                    'status_key': d.status,
                    'provider': d.provider_display,
                    'payment_method': d.payment_method,
                    'date': d.created_at.strftime('%b %d, %Y'),
                    'has_proof': bool(d.manual_proof),
                    'proof_is_image': d.proof_is_image,
                    'proof_url': reverse('portal_donation_proof', kwargs={'donation_id': d.pk})
                    if d.manual_proof
                    else '',
                    'can_review': (
                        can_manage_donations
                        and d.status == Donation.Status.PENDING
                        and d.payment_method == Donation.PaymentMethod.MANUAL
                    ),
                    'confirm_url': reverse('portal_confirm_donation', kwargs={'donation_id': d.pk}),
                    'reject_url': reverse('portal_reject_donation', kwargs={'donation_id': d.pk}),
                }
                for d in donations
            ],
        }
    )


@login_required(login_url='/login/')
@staff_module_required(StaffDesignation.Module.STAFF)
def portal_manage_staff(request):
    staff_users = User.objects.filter(role=User.Role.STAFF).select_related(
        'staff_profile',
        'staff_profile__designation',
    ).prefetch_related('staff_profile__designations').order_by('-date_joined')
    staff_form = StaffCreateForm()
    designations = StaffDesignation.objects.order_by('title')

    active_count = StaffProfile.objects.filter(user__role=User.Role.STAFF, is_active=True).count()
    stats = {
        'total': staff_users.count(),
        'active': active_count,
        'designations': designations.count(),
    }

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create_staff':
            staff_form = StaffCreateForm(request.POST)
            if staff_form.is_valid():
                user = staff_form.save()
                selected_designations = StaffDesignation.objects.filter(
                    pk__in=request.POST.getlist('designations'),
                )
                primary_designation = selected_designations.first()
                can_manage_donations = any(
                    StaffDesignation.Module.DONATIONS in (designation.modules or [])
                    for designation in selected_designations
                )
                profile = StaffProfile.objects.create(
                    user=user,
                    employee_id=generate_employee_id(),
                    designation=primary_designation,
                    department=request.POST.get('department', ''),
                    can_manage_donations=can_manage_donations,
                )
                profile.designations.set(selected_designations)
                messages.success(request, 'Staff account created.')
                return redirect('portal_manage_staff')
        elif action == 'update_staff':
            user = get_object_or_404(User, pk=request.POST.get('user_id'), role=User.Role.STAFF)
            profile = get_object_or_404(StaffProfile, user=user)
            form = StaffAdminUpdateForm(request.POST, instance=user, staff_profile=profile)
            if form.is_valid():
                user = form.save()
                user.username = form.cleaned_data['email'].lower()
                user.email = form.cleaned_data['email'].lower()
                user.save(update_fields=['username', 'email'])
                selected_designations = form.cleaned_data.get('designations')
                profile.designation = selected_designations.first() if selected_designations else None
                profile.department = form.cleaned_data.get('department', '')
                profile.is_active = form.cleaned_data.get('is_active', False)
                profile.can_manage_donations = any(
                    StaffDesignation.Module.DONATIONS in (designation.modules or [])
                    for designation in selected_designations
                )
                profile.save()
                profile.designations.set(selected_designations)
                messages.success(request, 'Staff account updated.')
                return redirect('portal_manage_staff')
        elif action == 'toggle_staff':
            profile = get_object_or_404(
                StaffProfile,
                user_id=request.POST.get('user_id'),
                user__role=User.Role.STAFF,
            )
            profile.is_active = not profile.is_active
            profile.save(update_fields=['is_active', 'updated_at'])
            state = 'activated' if profile.is_active else 'deactivated'
            messages.success(request, f'Staff account {state}.')
            return redirect('portal_manage_staff')
        elif action == 'delete_staff':
            user = get_object_or_404(User, pk=request.POST.get('user_id'), role=User.Role.STAFF)
            if user.pk == request.user.pk:
                messages.error(request, 'You cannot delete your own account.')
                return redirect('portal_manage_staff')
            name = user.get_full_name() or user.email
            user.delete()
            messages.success(request, f'Staff account "{name}" removed.')
            return redirect('portal_manage_staff')

    return render(
        request,
        'portal/admin/staff.html',
        {
            'staff_users': staff_users,
            'designations': designations,
            'staff_form': staff_form,
            'stats': stats,
            'staff_detail_url_template': reverse('portal_staff_detail', kwargs={'user_id': 0}),
            'staff_id_card_url_template': reverse('portal_admin_staff_id_card', kwargs={'user_id': 0}),
        },
    )


@login_required(login_url='/login/')
@staff_module_required(StaffDesignation.Module.STAFF)
def portal_manage_designations(request):
    designations = StaffDesignation.objects.annotate(
        staff_count=Count('staff_profiles', distinct=True),
    ).order_by('title')
    designation_form = StaffDesignationForm()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create_designation':
            designation_form = StaffDesignationForm(request.POST)
            if designation_form.is_valid():
                designation_form.save()
                messages.success(request, 'Designation added.')
                return redirect('portal_manage_designations')
        elif action == 'update_designation':
            designation = get_object_or_404(StaffDesignation, pk=request.POST.get('designation_id'))
            designation_form = StaffDesignationForm(request.POST, instance=designation)
            if designation_form.is_valid():
                designation_form.save()
                messages.success(request, 'Designation updated.')
                return redirect('portal_manage_designations')
        elif action == 'delete_designation':
            designation = get_object_or_404(StaffDesignation, pk=request.POST.get('designation_id'))
            if designation.staff_profiles.exists() or designation.staff_members.exists():
                messages.error(
                    request,
                    f'Cannot delete "{designation.title}" while staff are assigned. Reassign them first.',
                )
            else:
                designation.delete()
                messages.success(request, 'Designation removed.')
            return redirect('portal_manage_designations')

    return render(
        request,
        'portal/admin/designations.html',
        {
            'designations': designations,
            'designation_form': designation_form,
            'module_choices': StaffDesignation.Module.choices,
            'stats': {
                'total': designations.count(),
                'in_use': designations.filter(staff_count__gt=0).count(),
            },
        },
    )


@login_required(login_url='/login/')
@staff_module_required(StaffDesignation.Module.STAFF)
def portal_staff_detail(request, user_id):
    user = get_object_or_404(
        User.objects.select_related('staff_profile', 'staff_profile__designation').prefetch_related(
            'staff_profile__designations',
        ),
        pk=user_id,
        role=User.Role.STAFF,
    )
    profile = getattr(user, 'staff_profile', None)
    if not profile:
        profile = StaffProfile.objects.create(
            user=user,
            employee_id=generate_employee_id(),
        )

    return JsonResponse(
        {
            'id': user.pk,
            'full_name': user.get_full_name() or user.username,
            'email': user.email,
            'phone': user.phone or '',
            'address': user.address or '',
            'photo_url': user.photo.url if user.photo else '',
            'employee_id': profile.employee_id,
            'designation': ', '.join(profile.get_designation_titles()),
            'designation_ids': [designation.pk for designation in profile.get_designations()],
            'modules': profile.get_module_labels(),
            'department': profile.department or '',
            'is_active': profile.is_active,
            'can_manage_donations': profile.has_module(StaffDesignation.Module.DONATIONS),
            'date_joined': user.date_joined.strftime('%B %d, %Y'),
            'id_card_url': reverse('portal_admin_staff_id_card', kwargs={'user_id': user.pk}),
        }
    )


@login_required(login_url='/login/')
@staff_module_required(StaffDesignation.Module.STAFF)
def portal_admin_staff_id_card(request, user_id):
    user = get_object_or_404(User, pk=user_id, role=User.Role.STAFF)
    staff_profile = get_object_or_404(
        StaffProfile.objects.select_related('designation'),
        user=user,
    )
    return render(
        request,
        'portal/admin/staff_id_card.html',
        {'staff_profile': staff_profile, 'user': user},
    )


@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def portal_admin_dashboard(request):
    from datetime import timedelta

    from django.db.models import Count, Max
    from django.db.models.functions import TruncMonth
    from django.utils import timezone

    from .models import Blog, Contact, Gallery, Sponsor, Vacancy

    now = timezone.now()
    six_months_ago = now - timedelta(days=183)

    blog_count = Blog.objects.count()
    vacancy_count = Vacancy.objects.count()
    gallery_count = Gallery.objects.count()
    contact_count = Contact.objects.count()
    sponsor_count = Sponsor.objects.publicly_visible().count()
    published_blogs = Blog.objects.filter(status=1).count()

    last_blog = Blog.objects.aggregate(last=Max('updated_at'))['last'] if blog_count else None
    last_vacancy = Vacancy.objects.aggregate(last=Max('updated_at'))['last'] if vacancy_count else None
    last_gallery = Gallery.objects.aggregate(last=Max('created_at'))['last'] if gallery_count else None

    donations_total = (
        Donation.objects.filter(status=Donation.Status.CONFIRMED).aggregate(t=Sum('amount'))['t'] or 0
    )
    pending_count = Donation.objects.filter(status=Donation.Status.PENDING).count()
    confirmed_count = Donation.objects.filter(status=Donation.Status.CONFIRMED).count()
    rejected_count = Donation.objects.filter(status=Donation.Status.REJECTED).count()
    cancelled_count = Donation.objects.filter(status=Donation.Status.CANCELLED).count()

    donation_status_chart = {
        'labels': ['Confirmed', 'Pending', 'Rejected', 'Cancelled'],
        'values': [confirmed_count, pending_count, rejected_count, cancelled_count],
        'colors': ['#06a84a', '#f0b429', '#ef4444', '#94a3b8'],
    }

    monthly_rows = (
        Donation.objects.filter(
            status=Donation.Status.CONFIRMED,
            created_at__gte=six_months_ago,
        )
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('month')
    )
    monthly_donations_chart = {
        'labels': [row['month'].strftime('%b %Y') for row in monthly_rows if row['month']],
        'amounts': [float(row['total'] or 0) for row in monthly_rows],
        'counts': [row['count'] for row in monthly_rows],
    }

    member_rows = (
        User.objects.filter(role=User.Role.MEMBER, date_joined__gte=six_months_ago)
        .annotate(month=TruncMonth('date_joined'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    member_growth_chart = {
        'labels': [row['month'].strftime('%b %Y') for row in member_rows if row['month']],
        'values': [row['count'] for row in member_rows],
    }

    content_chart = {
        'labels': ['Blogs', 'Published blogs', 'Vacancies', 'Gallery'],
        'values': [blog_count, published_blogs, vacancy_count, gallery_count],
        'colors': ['#2563eb', '#06a84a', '#7c3aed', '#e67e22'],
    }

    gallery_by_category = (
        Gallery.objects.values('category__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    gallery_category_chart = {
        'labels': [row['category__name'] or 'Uncategorized' for row in gallery_by_category],
        'values': [row['count'] for row in gallery_by_category],
    }

    recent_donations = (
        Donation.objects.select_related('member', 'bank')
        .order_by('-created_at')[:5]
    )

    stats = {
        'members': User.objects.filter(role=User.Role.MEMBER).count(),
        'staff': User.objects.filter(role=User.Role.STAFF).count(),
        'donations_total': donations_total,
        'pending_donations': pending_count,
        'confirmed_donations': confirmed_count,
        'blogs': blog_count,
        'published_blogs': published_blogs,
        'vacancies': vacancy_count,
        'gallery': gallery_count,
        'contact_messages': contact_count,
        'sponsors': sponsor_count,
        'last_blog': last_blog,
        'last_vacancy': last_vacancy,
        'last_gallery': last_gallery,
    }

    chart_data = {
        'donation_status': donation_status_chart,
        'monthly_donations': monthly_donations_chart,
        'member_growth': member_growth_chart,
        'content': content_chart,
        'gallery_categories': gallery_category_chart,
    }

    portal_settings = get_portal_settings()
    community_total = community_donation_total()

    return render(
        request,
        'portal/admin/dashboard.html',
        {
            'stats': stats,
            'chart_data': chart_data,
            'recent_donations': recent_donations,
            'portal_settings': portal_settings,
            'community_total': community_total,
            'community_progress': community_goal_progress_percent(portal_settings.annual_giving_goal),
        },
    )


@login_required(login_url='/login/')
@staff_module_required(StaffDesignation.Module.BANKS)
def portal_admin_banks(request):
    banks = DonationBank.objects.all()
    bank_form = DonationBankForm()
    edit_bank = None
    edit_form = None

    if request.method == 'POST':
        action = request.POST.get('action', 'create')
        if action == 'delete':
            bank = get_object_or_404(DonationBank, pk=request.POST.get('bank_id'))
            bank.delete()
            messages.success(request, f'Bank "{bank.name}" removed.')
            return redirect('portal_admin_banks')
        if action == 'update':
            edit_bank = get_object_or_404(DonationBank, pk=request.POST.get('bank_id'))
            edit_form = DonationBankForm(request.POST, instance=edit_bank)
            if edit_form.is_valid():
                edit_form.save()
                messages.success(request, 'Bank account updated.')
                return redirect('portal_admin_banks')
        else:
            bank_form = DonationBankForm(request.POST)
            if bank_form.is_valid():
                bank_form.save()
                messages.success(request, 'Bank account added.')
                return redirect('portal_admin_banks')

    edit_id = request.GET.get('edit')
    if edit_id:
        edit_bank = get_object_or_404(DonationBank, pk=edit_id)
        edit_form = DonationBankForm(instance=edit_bank)

    return render(
        request,
        'portal/admin/banks.html',
        {
            'banks': banks,
            'bank_form': bank_form,
            'edit_bank': edit_bank,
            'edit_form': edit_form,
        },
    )


@login_required(login_url='/login/')
@staff_module_required(StaffDesignation.Module.SETTINGS)
def portal_admin_member_settings(request):
    settings = get_portal_settings()
    if request.method == 'POST':
        form = PortalSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Member giving goal updated. All members will see the new message.')
            return redirect('portal_admin_member_settings')
    else:
        form = PortalSettingsForm(instance=settings)

    community_total = community_donation_total()
    goal = settings.annual_giving_goal

    return render(
        request,
        'portal/admin/member_settings.html',
        {
            'form': form,
            'settings': settings,
            'community_total': community_total,
            'community_progress': community_goal_progress_percent(goal),
        },
    )
