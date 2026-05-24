import json

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
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
    DonationForm,
    MemberProfileForm,
    MemberSignupForm,
    StaffCreateForm,
    StaffDesignationForm,
    StaffProfileAdminForm,
    StaffProfileForm,
)
from .models import Donation, MemberProfile, StaffDesignation, StaffProfile, User
from .utils import (
    confirm_donation,
    generate_employee_id,
    generate_membership_id,
    generate_tx_ref,
    get_dashboard_url_name,
    get_or_create_member_profile,
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
    donations = request.user.donations.all()[:5]
    confirmed_total = (
        request.user.donations.filter(status=Donation.Status.CONFIRMED).aggregate(t=Sum('amount'))['t'] or 0
    )
    pending_count = request.user.donations.filter(status=Donation.Status.PENDING).count()
    return render(
        request,
        'portal/member/dashboard.html',
        {
            'profile': profile,
            'donations': donations,
            'confirmed_total': confirmed_total,
            'pending_count': pending_count,
        },
    )


@login_required(login_url='/login/')
@role_required(User.Role.MEMBER)
def member_donate(request):
    profile = get_or_create_member_profile(request.user)
    manual_form = DonationForm()
    chapa_form = ChapaDonationForm()

    if request.method == 'POST':
        payment_type = request.POST.get('payment_type')
        if payment_type == 'manual':
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
                return _start_chapa_checkout(request, chapa_form.cleaned_data['amount'], chapa_form.cleaned_data.get('purpose', ''))

    return render(
        request,
        'portal/member/donate.html',
        {'profile': profile, 'manual_form': manual_form, 'chapa_form': chapa_form},
    )


def _start_chapa_checkout(request, amount, purpose):
    tx_ref = generate_tx_ref()
    donation = Donation.objects.create(
        member=request.user,
        amount=amount,
        purpose=purpose,
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
    donations = request.user.donations.all()
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
    donations = Donation.objects.select_related('member').all()
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


@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def portal_manage_members(request):
    members = User.objects.filter(role=User.Role.MEMBER).select_related('member_profile').order_by('-date_joined')
    return render(request, 'portal/admin/members.html', {'members': members})


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
    from .models import Blog, Vacancy
    from django.db.models import Max

    blog_count = Blog.objects.count()
    vacancy_count = Vacancy.objects.count()
    last_blog = Blog.objects.aggregate(last=Max('updated_at'))['last'] if blog_count else None
    last_vacancy = Vacancy.objects.aggregate(last=Max('updated_at'))['last'] if vacancy_count else None

    stats = {
        'members': User.objects.filter(role=User.Role.MEMBER).count(),
        'staff': User.objects.filter(role=User.Role.STAFF).count(),
        'donations_total': Donation.objects.filter(status=Donation.Status.CONFIRMED).aggregate(t=Sum('amount'))['t'] or 0,
        'pending_donations': Donation.objects.filter(status=Donation.Status.PENDING).count(),
        'blogs': blog_count,
        'vacancies': vacancy_count,
        'last_blog': last_blog,
        'last_vacancy': last_vacancy,
    }
    return render(request, 'portal/admin/dashboard.html', {'stats': stats})
