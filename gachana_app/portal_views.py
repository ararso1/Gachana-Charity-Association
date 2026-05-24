import json

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from decimal import Decimal

from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .chapa import ChapaError, initialize_payment, parse_webhook_payload, verify_payment, verify_webhook_signature
from .decorators import role_required
from .forms import (
    ChapaDonationForm,
    DonationBankForm,
    DonationForm,
    MemberProfileForm,
    MemberSignupForm,
    PortalSettingsForm,
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
    generate_tx_ref,
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
    donations = request.user.donations.all()[:5]
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
    chapa_form = ChapaDonationForm()
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
                    donation = manual_form.save(commit=False)
                    donation.member = request.user
                    donation.payment_method = Donation.PaymentMethod.MANUAL
                    donation.status = Donation.Status.PENDING
                    donation.save()
                    messages.success(
                        request,
                        'Donation submitted. It will appear on your membership card once confirmed by our team.',
                    )
                    return redirect('member_donations')
        elif payment_type == 'chapa':
            chapa_form = ChapaDonationForm(request.POST)
            if chapa_form.is_valid():
                return _start_chapa_checkout(request, chapa_form.cleaned_data['amount'])

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


def _start_chapa_checkout(request, amount):
    tx_ref = generate_tx_ref()
    donation = Donation.objects.create(
        member=request.user,
        amount=amount,
        purpose='',
        payment_method=Donation.PaymentMethod.CHAPA,
        status=Donation.Status.PENDING,
        chapa_tx_ref=tx_ref,
    )
    callback_url = request.build_absolute_uri(reverse('chapa_callback'))
    return_url = request.build_absolute_uri(reverse('chapa_return', kwargs={'tx_ref': tx_ref}))

    try:
        data = initialize_payment(
            amount=amount,
            email=request.user.email,
            first_name=request.user.first_name,
            last_name=request.user.last_name,
            tx_ref=tx_ref,
            callback_url=callback_url,
            return_url=return_url,
        )
    except ChapaError as exc:
        donation.status = Donation.Status.CANCELLED
        donation.save(update_fields=['status', 'updated_at'])
        messages.error(request, str(exc))
        return redirect('member_donate')

    donation.chapa_checkout_url = data.get('checkout_url', '')
    donation.save(update_fields=['chapa_checkout_url', 'updated_at'])
    return redirect(donation.chapa_checkout_url)


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
        _confirm_chapa_donation(donation)
    elif status in ('failed', 'cancelled'):
        donation.status = Donation.Status.CANCELLED
        donation.save(update_fields=['status', 'updated_at'])

    return HttpResponse('OK')


@login_required(login_url='/login/')
def chapa_return(request, tx_ref):
    donation = get_object_or_404(Donation, chapa_tx_ref=tx_ref, member=request.user)
    if donation.status == Donation.Status.CONFIRMED:
        messages.success(request, 'Thank you! Your donation was confirmed and your membership card is ready.')
        return redirect('member_card')

    try:
        result = verify_payment(tx_ref)
        data = result.get('data', {})
        if data.get('status') == 'success':
            _confirm_chapa_donation(donation)
            messages.success(request, 'Payment successful! Your membership card is now available.')
            return redirect('member_card')
    except ChapaError:
        pass

    messages.info(request, 'Payment is being processed. You will be notified once it is confirmed.')
    return redirect('member_donations')


def _confirm_chapa_donation(donation):
    if donation.status == Donation.Status.CONFIRMED:
        return
    confirm_donation(donation)


@login_required(login_url='/login/')
@role_required(User.Role.STAFF)
def staff_dashboard(request):
    staff_profile, _ = StaffProfile.objects.get_or_create(
        user=request.user,
        defaults={'employee_id': generate_employee_id()},
    )
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
@role_required(User.Role.STAFF, User.Role.ADMIN)
def portal_donation_list(request):
    donations = Donation.objects.select_related('member', 'bank').all()
    status_filter = request.GET.get('status')
    if status_filter:
        donations = donations.filter(status=status_filter)
    return render(request, 'portal/donations/list.html', {'donations': donations, 'status_filter': status_filter})


@login_required(login_url='/login/')
@role_required(User.Role.STAFF, User.Role.ADMIN)
@require_POST
def portal_confirm_donation(request, donation_id):
    donation = get_object_or_404(Donation, pk=donation_id)
    if donation.status != Donation.Status.PENDING:
        messages.warning(request, 'Only pending donations can be confirmed.')
    else:
        confirm_donation(donation, confirmed_by=request.user)
        messages.success(request, 'Donation confirmed. Membership card issued if eligible.')
    return redirect('portal_donation_list')


@login_required(login_url='/login/')
@role_required(User.Role.STAFF, User.Role.ADMIN)
@require_POST
def portal_reject_donation(request, donation_id):
    donation = get_object_or_404(Donation, pk=donation_id)
    donation.status = Donation.Status.REJECTED
    donation.confirmed_by = request.user
    donation.confirmed_at = timezone.now()
    donation.save()
    messages.info(request, 'Donation marked as rejected.')
    return redirect('portal_donation_list')


MEMBERS_PER_PAGE = 15


def _members_filters_query(request):
    params = request.GET.copy()
    params.pop('page', None)
    return params.urlencode()


@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
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
        },
    )


@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def portal_member_detail(request, user_id):
    user = get_object_or_404(
        User.objects.select_related('member_profile'),
        pk=user_id,
        role=User.Role.MEMBER,
    )
    profile = getattr(user, 'member_profile', None)
    donations = Donation.objects.filter(member=user).order_by('-created_at')[:8]
    donation_stats = Donation.objects.filter(member=user).aggregate(
        confirmed=Count('id', filter=Q(status=Donation.Status.CONFIRMED)),
        pending=Count('id', filter=Q(status=Donation.Status.PENDING)),
    )

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
            'recent_donations': [
                {
                    'amount': float(d.amount),
                    'currency': d.currency,
                    'status': d.get_status_display(),
                    'status_key': d.status,
                    'method': d.get_payment_method_display(),
                    'date': d.created_at.strftime('%b %d, %Y'),
                }
                for d in donations
            ],
        }
    )


@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def portal_manage_staff(request):
    staff_users = User.objects.filter(role=User.Role.STAFF).select_related('staff_profile', 'staff_profile__designation')
    designations = StaffDesignation.objects.annotate(staff_count=Count('staff_members'))
    staff_form = StaffCreateForm()
    designation_form = StaffDesignationForm()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create_staff':
            staff_form = StaffCreateForm(request.POST)
            if staff_form.is_valid():
                user = staff_form.save()
                StaffProfile.objects.create(
                    user=user,
                    employee_id=generate_employee_id(),
                    designation_id=request.POST.get('designation') or None,
                    department=request.POST.get('department', ''),
                )
                messages.success(request, 'Staff account created.')
                return redirect('portal_manage_staff')
        elif action == 'create_designation':
            designation_form = StaffDesignationForm(request.POST)
            if designation_form.is_valid():
                designation_form.save()
                messages.success(request, 'Designation added.')
                return redirect('portal_manage_staff')

    return render(
        request,
        'portal/admin/staff.html',
        {
            'staff_users': staff_users,
            'designations': designations,
            'staff_form': staff_form,
            'designation_form': designation_form,
        },
    )


@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def portal_admin_dashboard(request):
    from datetime import timedelta

    from django.db.models import Count, Max
    from django.db.models.functions import TruncMonth
    from django.utils import timezone

    from .models import Blog, Gallery, Vacancy

    now = timezone.now()
    six_months_ago = now - timedelta(days=183)

    blog_count = Blog.objects.count()
    vacancy_count = Vacancy.objects.count()
    gallery_count = Gallery.objects.count()
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
        Gallery.objects.values('category')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    category_labels = dict(Gallery.CATEGORY_CHOICES)
    gallery_category_chart = {
        'labels': [category_labels.get(row['category'], row['category']) for row in gallery_by_category],
        'values': [row['count'] for row in gallery_by_category],
    }

    recent_donations = (
        Donation.objects.select_related('member')
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
@role_required(User.Role.ADMIN)
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
@role_required(User.Role.ADMIN)
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
