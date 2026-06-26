"""Shared donation checkout logic for member portal and public donate page."""

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

from .chapa import ChapaError, initialize_payment
from .models import Donation, User
from .utils import confirm_donation, generate_tx_ref


def member_user_for_donation(user):
    if user.is_authenticated and user.role == User.Role.MEMBER:
        return user
    return None


def start_chapa_checkout(
    request,
    *,
    amount,
    member=None,
    email='',
    first_name='',
    last_name='',
    error_redirect_name,
    description='Charity donation',
):
    tx_ref = generate_tx_ref()
    donation = Donation.objects.create(
        member=member,
        donor_email=email.lower() if email else '',
        donor_first_name=first_name or '',
        donor_last_name=last_name or '',
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
            email=email,
            first_name=first_name,
            last_name=last_name,
            tx_ref=tx_ref,
            callback_url=callback_url,
            return_url=return_url,
            description=description,
        )
    except ChapaError as exc:
        donation.status = Donation.Status.CANCELLED
        donation.save(update_fields=['status', 'updated_at'])
        messages.error(request, str(exc))
        return redirect(error_redirect_name)

    donation.chapa_checkout_url = data.get('checkout_url', '')
    donation.save(update_fields=['chapa_checkout_url', 'updated_at'])
    return redirect(donation.chapa_checkout_url)


def save_manual_donation(*, form, member=None, donor_email='', donor_first_name='', donor_last_name=''):
    donation = form.save(commit=False)
    donation.member = member
    donation.donor_email = donor_email.lower() if donor_email else ''
    donation.donor_first_name = donor_first_name or ''
    donation.donor_last_name = donor_last_name or ''
    donation.payment_method = Donation.PaymentMethod.MANUAL
    donation.status = Donation.Status.PENDING
    donation.save()
    return donation


def confirm_chapa_donation(donation):
    if donation.status == Donation.Status.CONFIRMED:
        return
    confirm_donation(donation)


def chapa_donor_details(request, *, email='', first_name='', last_name=''):
    member = member_user_for_donation(request.user)
    if member:
        return {
            'member': member,
            'email': member.email,
            'first_name': member.first_name,
            'last_name': member.last_name,
        }
    return {
        'member': None,
        'email': email,
        'first_name': first_name,
        'last_name': last_name,
    }
