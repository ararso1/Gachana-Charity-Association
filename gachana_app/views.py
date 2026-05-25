from django.shortcuts import render,redirect, get_object_or_404
from .models import *
from django.http import JsonResponse
from django.utils import timezone
from .forms import *
from .models import MemberProfile
from .utils import generate_membership_id
from django.contrib.auth.decorators import login_required
from .decorators import role_required
from .models import User
from .utils import get_dashboard_url_name
from django.db.models import Max, F
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import authenticate, login,logout
from django.contrib import messages
from django.db.models import Count
from django.contrib.auth.views import PasswordResetView
from django.urls import reverse, reverse_lazy
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.db import IntegrityError
from django.db.models import Q



# Create your views here.

def home(request):
    blogs = Blog.objects.filter(status=1).order_by('-created_at')[:3]
    return render(request, 'index.html', {'blogs':blogs})

def about(request, category=None):
    gal = Gallery.objects.select_related('category').all()
    if category:
        gal = gal.filter(category__slug=category)
    return render(request, 'about.html', {'gal': gal, 'selected_category': category})

def gallery(request):
    categories = GalleryCategory.objects.filter(is_active=True).order_by('sort_order', 'name')
    return render(request, 'gallery.html', {'gallery_categories': categories})

def fetch_gallery(request, category):
    """Return gallery items as JSON based on category slug or 'all'."""
    if category == 'all':
        gal = Gallery.objects.select_related('category').all()
    else:
        gal = Gallery.objects.filter(category__slug=category).select_related('category')

    gallery_data = [
        {
            'description': image.description or '',
            'category': image.category.slug,
            'image_url': image.img.url,
        }
        for image in gal
    ]
    return JsonResponse({'gallery': gallery_data})

def blogs(request):
    blogs = Blog.objects.filter(status=1).order_by('-created_at')
    return render(request, 'blogs.html', {'blogs':blogs})

def blog_details(request, slug):
    blog = get_object_or_404(Blog, slug=slug)
    top5 = Blog.objects.filter(status=1).order_by('-created_at')[:5]
    all_blogs = Blog.objects.filter(status=1).order_by('-created_at')
    categories = Category.objects.annotate(count=Count('blogs')).order_by('-count')
    comments = blog.comments.all().order_by('-created_at')[:3]

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.blog = blog
            comment.save()
            return redirect('blog_details', slug=blog.slug)
    else:
        form = CommentForm()

    return render(
        request,
        'blog_details.html',
        {
            'blog': blog,
            'all_blogs': all_blogs,
            'top5': top5,
            'categories': categories,
            'comments': comments,
            'form': form,
        },
    )


def blog_details_legacy(request, blog_id):
    blog = get_object_or_404(Blog, pk=blog_id)
    return redirect('blog_details', slug=blog.slug, permanent=True)

def blog_by_category(request, category_id=None):
    categories = Category.objects.annotate(count=Count('blogs')).order_by('-count')  # Get all categories with post counts
    all_blogs = Blog.objects.filter(status=1).order_by('-created_at')
    top5 = Blog.objects.filter(status=1).order_by('-created_at')[:5]

    if category_id:
        selected_category = get_object_or_404(Category, id=category_id)  # Get the selected category
        blogs = Blog.objects.filter(
            categories=selected_category,
            status=1,
        ).order_by('-created_at')
    else:
        selected_category = None
        blogs = Blog.objects.filter(status=1).order_by('-created_at')

    return render(request, 'blogby_category.html', {
        'blogs': blogs,
        'all_blogs':all_blogs,
        'categories': categories,
        'selected_category': selected_category,
        'top5':top5
    })

def contact(request):
    if request.method != 'POST':
        return render(request, 'contact.html')

    name = (request.POST.get('name') or '').strip()
    email = (request.POST.get('email') or '').strip().lower()
    subject = (request.POST.get('subject') or '').strip()
    message = (request.POST.get('message') or '').strip()

    errors = []
    if not name:
        errors.append('Please enter your name.')
    elif len(name) > 255:
        errors.append('Name is too long.')
    if not email:
        errors.append('Please enter your email.')
    else:
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError

        try:
            validate_email(email)
        except ValidationError:
            errors.append('Please enter a valid email address.')
    if not subject:
        errors.append('Please enter a subject.')
    elif len(subject) > 455:
        errors.append('Subject is too long.')
    if not message:
        errors.append('Please enter your message.')

    if errors:
        return JsonResponse({'success': False, 'message': ' '.join(errors)}, status=400)

    from .utils import contact_rate_limit_exceeded, send_contact_notification_emails

    if contact_rate_limit_exceeded(email):
        return JsonResponse(
            {
                'success': False,
                'message': (
                    'You can only send up to 3 messages per day using this email address. '
                    'Please try again tomorrow.'
                ),
            },
            status=429,
        )

    try:
        Contact.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message,
        )
    except Exception:
        return JsonResponse(
            {
                'success': False,
                'message': 'We could not save your message. Please try again in a few minutes.',
            },
            status=500,
        )

    import threading

    threading.Thread(
        target=send_contact_notification_emails,
        args=(name, email, subject, message),
        daemon=True,
    ).start()

    return JsonResponse(
        {
            'success': True,
            'message': (
                'Your message was sent successfully! '
                'We will get back to you as soon as possible.'
            ),
        }
    )

def climate(request):
    return render(request, 'climate.html')

def our_work(request):
    blogs = Blog.objects.filter(status=1).order_by('-created_at')[:3]
    return render(request, 'our_work.html', {"blogs":blogs})

def why_donate(request):
    return render(request, 'why_donate.html')

def vacancy(request):
    vac = Vacancy.objects.all().order_by('-created_at')
    return render(request, 'vacancy.html', {'vac':vac})

def vacancy_details(request, vac_id):
    vacancy = get_object_or_404(Vacancy, id=vac_id)
    return render(request, 'vacancy details.html', {'vacancy':vacancy})

def signin(request):
    return redirect('login')

def donate(request):
    return render(request, 'donate.html')

def custom_404(request, exception=None):
    return render(request, '404.html', status=404)


def user_login(request):
    if request.user.is_authenticated:
        return redirect(get_dashboard_url_name(request.user))

    signup_form = MemberSignupForm()
    show_signup = request.GET.get('register') == '1'

    if request.method == 'POST':
        form_type = request.POST.get('form_type', 'login')

        if form_type == 'signup':
            show_signup = True
            signup_form = MemberSignupForm(request.POST)
            if signup_form.is_valid():
                user = signup_form.save()
                MemberProfile.objects.create(
                    user=user,
                    membership_id=generate_membership_id(),
                )
                login(request, user)
                messages.success(
                    request,
                    f'Welcome to Gachana Charity Association! Your membership ID is {user.member_profile.membership_id}.',
                )
                return redirect('member_dashboard')
        else:
            email = request.POST.get('email', '').strip().lower()
            password = request.POST.get('password')

            account = User.objects.filter(email__iexact=email).first()
            user = None
            if account:
                user = authenticate(request, username=account.username, password=password)

            if user is not None:
                login(request, user)
                return redirect(get_dashboard_url_name(user))
            messages.error(request, 'Invalid email or password.')

    return render(request, 'login.html', {'signup_form': signup_form, 'show_signup': show_signup})


def password_reset_request(request):
    if request.method == "POST":
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            associated_users = User.objects.filter(email=email)
            if associated_users.exists():
                user = associated_users.first()
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                reset_url = f"{settings.SITE_URL}/reset-password/{uid}/{token}/"

                send_mail(
                    subject="Password Reset Request",
                    message=f"Click the link below to reset your password:\n\n{reset_url}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                )
                
                messages.success(request, "A reset link has been sent to your email.")
                return redirect("login")
            else:
                messages.error(request, "No account found with this email.")
    else:
        form = PasswordResetForm()

    return render(request, "password_reset.html", {"form": form})

def password_reset_confirm(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = get_object_or_404(User, pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == "POST":
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Your password has been reset successfully!")
                return redirect("login")
        else:
            form = SetPasswordForm(user)

        return render(request, "password_reset_email.html", {"form": form})

    else:
        messages.error(request, "Invalid or expired password reset link.")
        return redirect("password_reset_request")


def logout_user(request):
    logout(request)  # Logs out the user
    return redirect('home')  # Redirect to the login page

# Admin pages start here
@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def admin_dashboard(request):
    return redirect('portal_admin_dashboard')


# vacancy part
@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def vacancy_list(request):
    query = request.GET.get('q')
    vacancies = Vacancy.objects.all().order_by('-created_at')

    if query:
        vacancies = vacancies.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        ).distinct()

    total = Vacancy.objects.count()
    return render(request, 'portal/admin/content/vacancy_list.html', {
        'vacancies': vacancies,
        'query': query,
        'stats': {
            'total': total,
            'published': Vacancy.objects.filter(status=1).count(),
            'unpublished': Vacancy.objects.filter(status=0).count(),
            'filtered': vacancies.count(),
        },
    })


@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def create_vacancy(request):
    if request.method == "POST":
        form = VacancyForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                vacancy = form.save(commit=False)
                vacancy.added_by = request.user
                vacancy.save()
                form.save_m2m()
                return JsonResponse({'success': True})
            except IntegrityError:
                form.add_error('title', 'A vacancy with this title already exists.')
        return render(request, 'portal/admin/content/vacancy_form.html', {'form': form, 'is_edit': False}, status=400)
    else:
        form = VacancyForm()

    return render(request, 'portal/admin/content/vacancy_form.html', {'form': form, 'is_edit': False})


@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def update_vacancy(request, vacancy_id):
    vacancy = get_object_or_404(Vacancy, id=vacancy_id)
    
    if request.method == 'POST':
        form = VacancyForm(request.POST, request.FILES, instance=vacancy)
        if form.is_valid():
            vacancy = form.save(commit=False)
            # blog.updated_by = request.user  # Set the user who last updated the blog
            vacancy.updated_by = request.user
            vacancy.save()
            messages.success(request, 'Vacancy updated successfully.')
            return redirect('vacancy_list')
    else:
        form = VacancyForm(instance=vacancy)

    return render(request, 'portal/admin/content/vacancy_form.html', {'form': form, 'vacancy': vacancy, 'is_edit': True})

@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def delete_vacancy(request, vacancy_id):
    vacancy = get_object_or_404(Vacancy, id=vacancy_id)
    if request.method == "POST":
        vacancy.delete()
        return redirect('vacancy_list')  # Adjust to your blog list view name
    return redirect('vacancy_list')


# blog part
@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def blog_list(request):
    query = request.GET.get('q')
    blogs = Blog.objects.prefetch_related('categories').order_by('-created_at')

    if query:
        blogs = blogs.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        ).distinct()

    total = Blog.objects.count()
    return render(request, 'portal/admin/content/blog_list.html', {
        'blogs': blogs,
        'query': query,
        'stats': {
            'total': total,
            'published': Blog.objects.filter(status=1).count(),
            'unpublished': Blog.objects.filter(status=0).count(),
            'filtered': blogs.count(),
        },
    })


@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def create_blogs(request):
    if request.method == 'POST':
        form = BlogForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                blog = form.save(commit=False)
                blog.added_by = request.user
                blog.save()
                form.save_m2m()
                return JsonResponse({'success': True})  # Tell JS that submission was successful
            except IntegrityError as e:
                form.add_error('title', 'A blog with this title already exists.')
        else:
            print(form.errors)
        return render(request, 'portal/admin/content/blog_form.html', {'form': form, 'is_edit': False}, status=400)
    else:
        form = BlogForm()
    return render(request, 'portal/admin/content/blog_form.html', {'form': form, 'is_edit': False})


@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def update_blog(request, blog_id):
    blog = get_object_or_404(Blog, id=blog_id)
    
    if request.method == 'POST':
        form = BlogForm(request.POST, request.FILES, instance=blog)
        if form.is_valid():
            blog = form.save(commit=False)
            blog.updated_by = request.user
            blog.save()
            form.save_m2m()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            messages.success(request, 'Blog updated successfully.')
            return redirect('blog_list')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return render(
                request,
                'portal/admin/content/blog_form.html',
                {'form': form, 'blog': blog, 'is_edit': True},
                status=400,
            )
    else:
        form = BlogForm(instance=blog)

    return render(request, 'portal/admin/content/blog_form.html', {'form': form, 'blog': blog, 'is_edit': True})

@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def delete_blog(request, blog_id):
    blog = get_object_or_404(Blog, id=blog_id)
    if request.method == "POST":
        blog.delete()
        return redirect('blog_list')  # Adjust to your blog list view name
    return redirect('blog_list')

# gallery part
@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def gallery_list(request):
    query = request.GET.get('q')
    category_slug = request.GET.get('category')
    items = Gallery.objects.select_related('category').order_by('-created_at')

    if category_slug:
        items = items.filter(category__slug=category_slug)
    if query:
        items = items.filter(
            Q(description__icontains=query) | Q(category__name__icontains=query)
        )

    total = Gallery.objects.count()
    return render(request, 'portal/admin/content/gallery_list.html', {
        'items': items,
        'query': query,
        'category_filter': category_slug,
        'gallery_categories': GalleryCategory.objects.order_by('sort_order', 'name'),
        'stats': {
            'total': total,
            'categories': GalleryCategory.objects.count(),
            'filtered': items.count(),
        },
    })


@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def create_gallery(request):
    if request.method == 'POST':
        form = GalleryForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Gallery image added successfully.')
            return redirect('gallery_list')
    else:
        form = GalleryForm()
    return render(request, 'portal/admin/content/gallery_form.html', {'form': form, 'is_edit': False})


@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def update_gallery(request, gallery_id):
    item = get_object_or_404(Gallery, id=gallery_id)
    if request.method == 'POST':
        form = GalleryForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Gallery image updated successfully.')
            return redirect('gallery_list')
    else:
        form = GalleryForm(instance=item)
    return render(request, 'portal/admin/content/gallery_form.html', {
        'form': form,
        'item': item,
        'is_edit': True,
    })


@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def delete_gallery(request, gallery_id):
    item = get_object_or_404(Gallery, id=gallery_id)
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Gallery image deleted.')
    return redirect('gallery_list')


@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def blog_category_list(request):
    categories = Category.objects.annotate(blog_count=Count('blogs')).order_by('name')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            form = BlogCategoryForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Blog category added.')
                return redirect('blog_category_list')
        elif action == 'update':
            category = get_object_or_404(Category, pk=request.POST.get('category_id'))
            form = BlogCategoryForm(request.POST, instance=category)
            if form.is_valid():
                form.save()
                messages.success(request, 'Blog category updated.')
                return redirect('blog_category_list')
        elif action == 'delete':
            category = get_object_or_404(Category, pk=request.POST.get('category_id'))
            if category.blogs.exists():
                messages.error(
                    request,
                    f'Cannot delete "{category.name}" while blog posts use it. Reassign posts first.',
                )
            else:
                category.delete()
                messages.success(request, 'Blog category removed.')
            return redirect('blog_category_list')

    return render(
        request,
        'portal/admin/content/blog_category_list.html',
        {
            'categories': categories,
            'category_form': BlogCategoryForm(),
            'stats': {
                'total': Category.objects.count(),
                'in_use': Category.objects.filter(blogs__isnull=False).distinct().count(),
            },
        },
    )


@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def gallery_category_list(request):
    categories = GalleryCategory.objects.annotate(image_count=Count('images')).order_by(
        'sort_order', 'name'
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            form = GalleryCategoryForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Gallery category added.')
                return redirect('gallery_category_list')
        elif action == 'update':
            category = get_object_or_404(GalleryCategory, pk=request.POST.get('category_id'))
            form = GalleryCategoryForm(request.POST, instance=category)
            if form.is_valid():
                form.save()
                messages.success(request, 'Gallery category updated.')
                return redirect('gallery_category_list')
        elif action == 'delete':
            category = get_object_or_404(GalleryCategory, pk=request.POST.get('category_id'))
            if category.images.exists():
                messages.error(
                    request,
                    f'Cannot delete "{category.name}" while images use it. Reassign or delete images first.',
                )
            else:
                category.delete()
                messages.success(request, 'Gallery category removed.')
            return redirect('gallery_category_list')

    return render(
        request,
        'portal/admin/content/gallery_category_list.html',
        {
            'categories': categories,
            'category_form': GalleryCategoryForm(),
            'stats': {
                'total': categories.count(),
                'active': categories.filter(is_active=True).count(),
            },
        },
    )


# Sponsors (public website showcase)
@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def sponsor_list(request):
    query = request.GET.get('q')
    tier_filter = request.GET.get('tier')
    sponsors = Sponsor.objects.all().order_by('sort_order', 'name')

    if tier_filter:
        sponsors = sponsors.filter(tier=tier_filter)
    if query:
        sponsors = sponsors.filter(
            Q(name__icontains=query)
            | Q(tagline__icontains=query)
        )

    total = Sponsor.objects.count()
    return render(
        request,
        'portal/admin/content/sponsor_list.html',
        {
            'sponsors': sponsors,
            'query': query,
            'tier_filter': tier_filter,
            'tier_choices': Sponsor.Tier.choices,
            'stats': {
                'total': total,
                'active': Sponsor.objects.filter(is_active=True).count(),
                'live_on_site': Sponsor.objects.publicly_visible().count(),
                'filtered': sponsors.count(),
            },
        },
    )


@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def create_sponsor(request):
    if request.method == 'POST':
        form = SponsorForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sponsor added successfully.')
            return redirect('sponsor_list')
    else:
        form = SponsorForm()
    return render(request, 'portal/admin/content/sponsor_form.html', {'form': form, 'is_edit': False})


@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def update_sponsor(request, sponsor_id):
    sponsor = get_object_or_404(Sponsor, pk=sponsor_id)
    if request.method == 'POST':
        form = SponsorForm(request.POST, request.FILES, instance=sponsor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sponsor updated successfully.')
            return redirect('sponsor_list')
    else:
        form = SponsorForm(instance=sponsor)
    return render(
        request,
        'portal/admin/content/sponsor_form.html',
        {'form': form, 'sponsor': sponsor, 'is_edit': True},
    )


@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def delete_sponsor(request, sponsor_id):
    sponsor = get_object_or_404(Sponsor, pk=sponsor_id)
    if request.method == 'POST':
        sponsor.delete()
        messages.success(request, 'Sponsor removed.')
    return redirect('sponsor_list')


# Contact form messages (public website)
@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def contact_message_list(request):
    from datetime import timedelta

    query = request.GET.get('q')
    messages_qs = Contact.objects.all().order_by('-created_at')

    if query:
        messages_qs = messages_qs.filter(
            Q(name__icontains=query)
            | Q(email__icontains=query)
            | Q(subject__icontains=query)
            | Q(message__icontains=query)
        )

    total = Contact.objects.count()
    return render(
        request,
        'portal/admin/content/contact_message_list.html',
        {
            'contact_messages': messages_qs,
            'query': query,
            'stats': {
                'total': total,
                'filtered': messages_qs.count(),
                'last_7_days': Contact.objects.filter(
                    created_at__gte=timezone.now() - timedelta(days=7)
                ).count(),
            },
        },
    )


@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def contact_message_detail(request, message_id):
    message = get_object_or_404(Contact, pk=message_id)
    return render(
        request,
        'portal/admin/content/contact_message_detail.html',
        {'message': message},
    )


@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def delete_contact_message(request, message_id):
    message = get_object_or_404(Contact, pk=message_id)
    if request.method == 'POST':
        message.delete()
        messages.success(request, 'Contact message deleted.')
    return redirect('contact_message_list')


@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def profile(request):
    return render(request, 'portal/admin/profile.html')

@login_required(login_url='/login/')
@role_required(User.Role.ADMIN)
def profile_edit(request):
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
    else:
        form = ProfileEditForm(instance=request.user)

    return render(request, 'portal/admin/profile_edit.html', {'form': form})