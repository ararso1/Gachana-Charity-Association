from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from ckeditor.fields import RichTextField

# Create your models here.

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        STAFF = 'staff', 'Staff'
        MEMBER = 'member', 'Member'

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    phone = models.CharField(max_length=15, null=True, blank=True)
    address = models.CharField(max_length=200, null=True, blank=True)
    photo = models.ImageField(upload_to='images/', null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.username}"

    @property
    def is_portal_admin(self):
        return self.is_superuser or self.role == self.Role.ADMIN

    @property
    def is_portal_staff(self):
        return self.role == self.Role.STAFF

    @property
    def is_portal_member(self):
        return self.role == self.Role.MEMBER


class StaffDesignation(models.Model):
    title = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title


class StaffProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    employee_id = models.CharField(max_length=20, unique=True, blank=True)
    designation = models.ForeignKey(
        StaffDesignation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_members',
    )
    department = models.CharField(max_length=120, blank=True)
    date_joined = models.DateField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.employee_id})"


class MemberProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='member_profile')
    membership_id = models.CharField(max_length=20, unique=True, blank=True)
    membership_goal = models.DecimalField(max_digits=12, decimal_places=2, default=10000)
    total_donated = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    card_issued_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.membership_id or str(self.user)

    @property
    def progress_percent(self):
        if not self.membership_goal:
            return 0
        return min(100, int((self.total_donated / self.membership_goal) * 100))

    @property
    def has_membership_card(self):
        return bool(self.card_issued_at)


class Donation(models.Model):
    class PaymentMethod(models.TextChoices):
        MANUAL = 'manual', 'Manual / Bank Transfer'
        CHAPA = 'chapa', 'Chapa (Online)'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        REJECTED = 'rejected', 'Rejected'
        CANCELLED = 'cancelled', 'Cancelled'

    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name='donations')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='ETB')
    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    purpose = models.CharField(max_length=255, blank=True)
    manual_reference = models.CharField(max_length=255, blank=True)
    manual_proof = models.FileField(upload_to='donation_proofs/', null=True, blank=True)
    chapa_tx_ref = models.CharField(max_length=100, unique=True, null=True, blank=True)
    chapa_checkout_url = models.URLField(max_length=500, blank=True)
    confirmed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='donations_confirmed',
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.member} - {self.amount} {self.currency} ({self.status})"
    
""" class Category(models.Model):
    name = models.CharField(max_length=250)
    description = models.TextField(blank=True, null=True)
    status = models.IntegerField(default = 1)
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name """
    
class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name

class Blog(models.Model):
    STATUS_CHOICES = [
        (1, 'Published'),
        (0, 'Unpublished'),
    ]

    title = models.CharField(max_length=255, unique=True)
    categories = models.ManyToManyField(Category, related_name='blogs')
    description = RichTextField()
    status = models.IntegerField(choices=STATUS_CHOICES)
    banner = models.ImageField(upload_to='images/', null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='blogs_added')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='blogs_updated')

    def __str__(self):
        return self.title


class Gallery(models.Model):
    CATEGORY_CHOICES = [
        ('certifications', 'Certifications'),
        ('early_child_development', 'Early Child Development'),
        ('basic_educations', 'Basic Education'),
        ('youth_Development', 'Youth Development'),
        ('community_empowerment', 'Community Empowerment'),
    ]

    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)
    img = models.ImageField(upload_to='gallery/')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    
    def __str__(self):
        return self.category

class Vacancy(models.Model):
    JOB_TYPE_CHOICES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
    ]

    STATUS_CHOICES = [
        (1, 'Published'),
        (0, 'Unpublished'),
    ]

    title = models.CharField(max_length=250, unique=True)
    department = models.CharField(max_length=250, default="General")
    experience = models.CharField(max_length=100, blank=True, null=True)
    position = models.CharField(max_length=100, blank=True, null=True)
    job_type = models.CharField(max_length=20, default='full_time', choices=JOB_TYPE_CHOICES)
    description = RichTextField()
    location = models.CharField(max_length=255, default='Silte')
    salary = models.CharField(max_length=200, blank=True, null=True)
    banner = models.ImageField(upload_to='images/', blank=True, null=True)
    status = models.IntegerField(choices=STATUS_CHOICES, default=1)
    link = models.CharField(max_length=2000, blank=True, null=True)
    deadline = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='vacancy_added')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='vacancy_updated')

    def __str__(self):
        return self.title


class Contact(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    subject = models.CharField(max_length=455)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name} - {self.subject}"

class Comment(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name="comments")
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.name} on {self.blog.title}"