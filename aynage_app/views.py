from django.shortcuts import render,redirect, get_object_or_404
from .models import *
from django.http import JsonResponse
from django.utils import timezone
from .forms import *
from django.contrib.auth.decorators import login_required
from django.db.models import Max, F
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import authenticate, login,logout
from django.contrib import messages
from django.db.models import Count
from django.contrib.auth.views import PasswordResetView
from django.urls import reverse_lazy
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
    if category:
        gal = Gallery.objects.filter(category=category)
    else:
        gal = Gallery.objects.all()
    return render(request, 'about.html', {'gal': gal, 'selected_category': category})

def gallery(request):
    return render(request, 'gallery.html')

def fetch_gallery(request, category):
    """ Return gallery items as JSON based on category """
    if category == 'all':
        gal = Gallery.objects.all()
    else:
        gal = Gallery.objects.filter(category=category)
    
    gallery_data = [
        {
            'description': image.description,
            'category': image.category,
            'image_url': image.img.url
        } for image in gal
    ]
    return JsonResponse({'gallery': gallery_data})

def blogs(request):
    blogs = Blog.objects.filter(status=1).order_by('-created_at')
    return render(request, 'blogs.html', {'blogs':blogs})

def blog_details(request, blog_id):
    blog = get_object_or_404(Blog, id=blog_id)
    top5 = Blog.objects.filter(status=1).order_by('-created_at')[:5]
    all_blogs = Blog.objects.filter(status=1).order_by('-created_at')
    categories = Category.objects.annotate(count=Count('blogs')).order_by('-count')
    comments = blog.comments.all().order_by('-created_at')[:3] 

    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.blog = blog  # Associate the comment with the blog
            comment.save()
            return redirect("blog_details", blog_id=blog.id)  # Refresh the page

    else:
        form = CommentForm()

    return render(request, 'blog_details.html', {
        'blog': blog,
        'all_blogs': all_blogs,
        'top5': top5,
        'categories': categories,
        'comments': comments,
        'form': form
    })

def blog_by_category(request, category_id=None):
    categories = Category.objects.annotate(count=Count('blogs')).order_by('-count')  # Get all categories with post counts
    all_blogs = Blog.objects.filter(status=1).order_by('-created_at')
    top5 = Blog.objects.filter(status=1).order_by('-created_at')[:5]

    if category_id:
        selected_category = get_object_or_404(Category, id=category_id)  # Get the selected category
        blogs = Blog.objects.filter(categories=selected_category).order_by('-created_at')  # Filter blogs
    else:
        selected_category = None
        blogs = Blog.objects.all().order_by('-created_at')  # Show all blogs if no category selected

    return render(request, 'blogby_category.html', {
        'blogs': blogs,
        'all_blogs':all_blogs,
        'categories': categories,
        'selected_category': selected_category,
        'top5':top5
    })

def contact(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        subject = request.POST.get("subject")
        message = request.POST.get("message")

        # Save message to the database
        contact = Contact.objects.create(
            name=name, 
            email=email, 
            subject=subject, 
            message=message
        )

        # Email to admin
        admin_email = "areealisho12@gmail.com"
        admin_subject = f"New Contact Form Submission: {subject}"
        admin_message = f"""
        You have received a new contact form submission:
        
        Name: {name}
        Email: {email}
        Subject: {subject}
        Message: {message}
        
        Please respond to this inquiry promptly.
        """
        
        send_mail(
            admin_subject,
            admin_message,
            settings.DEFAULT_FROM_EMAIL,  # Use your configured email
            [admin_email],
            fail_silently=False,
        )

        # Thank you email to user
        user_subject = "Thank you for contacting us"
        user_message = f"""
        Dear {name},
        
        Thank you for reaching out to us. We have received your message regarding:
        "{subject}"
        
        Our team will review your inquiry and get back to you as soon as possible.
        
        Here's a copy of your message for your reference:
        {message}
        
        Best regards,
        Aynage Child and Family Development Orginization
        """
        
        send_mail(
            user_subject,
            user_message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )

        # Send a success response
        return JsonResponse({
            "success": True, 
            "message": "Your message has been sent successfully! A confirmation email has been sent to your inbox."
        })
    return render(request, 'contact.html')

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
    return render(request, 'login.html')

def donate(request):
    return render(request, 'donate.html')

def custom_404(request, exception=None):
    return render(request, '404.html', status=404)


def user_login(request):
    if request.user.is_authenticated:
        return redirect("admin_panel")  

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            user = authenticate(request, username=email, password=password)
        except User.DoesNotExist:
            user = None

        if user is not None:
            login(request, user)
            return redirect("admin_panel")  
        else:
            messages.error(request, "Invalid email or password.")

    return render(request, "login.html")


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
def admin_dashboard(request):
    blog_count = Blog.objects.count()
    vacancy_count = Vacancy.objects.count()

    # Initialize variables for last updates
    last_blog_update = "No updates yet"
    last_vacancy_update = "No updates yet"

    # Check if there are any blog entries before aggregating
    if blog_count > 0:
        last_blog_update = Blog.objects.aggregate(last_updated=Max('updated_at'))['last_updated']
        if last_blog_update is None:
            last_blog_update = "No updates yet"

    # Check if there are any vacancy entries before aggregating
    if vacancy_count > 0:
        last_vacancy_update = Vacancy.objects.aggregate(last_updated=Max('updated_at'))['last_updated']
        if last_vacancy_update is None:
            last_vacancy_update = "No updates yet"

    return render(request, 'admin_page/dashboard.html', {
        'blog': blog_count,
        'vacancy': vacancy_count,
        'last_blog': last_blog_update,
        'last_vacancy': last_vacancy_update
    })


# vacancy part
@login_required(login_url='/login/')
def vacancy_list(request):
    query = request.GET.get('q')
    vacancies = Vacancy.objects.all().order_by('-created_at') 

    if query:
        vacancies = vacancies.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        ).distinct()
    return render(request, 'admin_page/vacancy_list.html', {'vacancies':vacancies, 'query': query,})


@login_required(login_url='/login/')
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
        return render(request, 'admin_page/create_vacancy.html', {'form': form}, status=400)
    else:
        form = VacancyForm()
    
    return render(request, 'admin_page/create_vacancy.html', {'form': form})


@login_required(login_url='/login/')
def update_vacancy(request, vacancy_id):
    vacancy = get_object_or_404(Vacancy, id=vacancy_id)
    
    if request.method == 'POST':
        form = VacancyForm(request.POST, request.FILES, instance=vacancy)
        if form.is_valid():
            vacancy = form.save(commit=False)
            # blog.updated_by = request.user  # Set the user who last updated the blog
            vacancy.save()
            return redirect('blog_list')
    else:
        form = BlogForm(instance=vacancy)
    
    return render(request, 'admin_page/edit_vacancy.html', {'form': form, 'vacancy': vacancy})

@login_required(login_url='/login/')
def delete_vacancy(request, vacancy_id):
    vacancy = get_object_or_404(Vacancy, id=vacancy_id)
    if request.method == "POST":
        vacancy.delete()
        return redirect('vacancy_list')  # Adjust to your blog list view name
    return redirect('vacancy_list')


# blog part
@login_required(login_url='/login/')
def blog_list(request):
    query = request.GET.get('q')
    blogs = Blog.objects.all().order_by('-created_at')

    if query:
        blogs = blogs.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        ).distinct()

    return render(request, 'admin_page/blog_list.html', {
        'blogs': blogs,
        'query': query,
    })


@login_required(login_url='/login/')
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
        return render(request, 'admin_page/create_blog.html', {'form': form}, status=400)
    else:
        form = BlogForm()
    return render(request, 'admin_page/create_blog.html', {'form': form})


@login_required(login_url='/login/')
def update_blog(request, blog_id):
    blog = get_object_or_404(Blog, id=blog_id)
    
    if request.method == 'POST':
        form = BlogForm(request.POST, request.FILES, instance=blog)
        if form.is_valid():
            blog = form.save(commit=False)
            blog.updated_by = request.user  # Set the user who last updated the blog
            blog.save()
            form.save_m2m() 
            return redirect('blog_list')
    else:
        form = BlogForm(instance=blog)
    
    return render(request, 'admin_page/edit_blog.html', {'form': form, 'blog': blog})

@login_required(login_url='/login/')
def delete_blog(request, blog_id):
    blog = get_object_or_404(Blog, id=blog_id)
    if request.method == "POST":
        blog.delete()
        return redirect('blog_list')  # Adjust to your blog list view name
    return redirect('blog_list')

@login_required(login_url='/login/')
def profile(request):
    return render(request, 'admin_page/profile.html')

@login_required(login_url='/login/')
def profile_edit(request):
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('profile')  # Redirect to the same page after saving
    else:
        form = ProfileEditForm(instance=request.user)
    
    return render(request, 'admin_page/profile_edit.html', {'form': form})