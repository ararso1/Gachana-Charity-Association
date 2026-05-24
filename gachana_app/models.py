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
    can_manage_donations = models.BooleanField(
        default=False,
        help_text='When enabled, this staff member can review and confirm donations in the portal.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.employee_id})"


class PortalSettings(models.Model):
    """Singleton site-wide settings for the member portal."""

    annual_giving_goal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=100000,
        help_text='Community fundraising target shown to all members (ETB).',
    )
    giving_goal_headline = models.CharField(
        max_length=200,
        default='Help us however you can',
    )
    giving_goal_message = models.TextField(
        blank=True,
        default=(
            'Our annual giving goal supports programs across the community. '
            'Every gift counts—give what feels right for you.'
        ),
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Portal settings'
        verbose_name_plural = 'Portal settings'

    def __str__(self):
        return 'Member portal settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class MemberProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='member_profile')
    membership_id = models.CharField(max_length=20, unique=True, blank=True)
    membership_goal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=10000,
        help_text='Deprecated: use PortalSettings.annual_giving_goal.',
    )
    total_donated = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    card_issued_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.membership_id or str(self.user)

    def progress_toward_goal(self, goal):
        if not goal:
            return 0
        return min(100, int((self.total_donated / goal) * 100))

    @property
    def progress_percent(self):
        return self.progress_toward_goal(PortalSettings.load().annual_giving_goal)

    @property
    def has_membership_card(self):
        return bool(self.card_issued_at)


class DonationBank(models.Model):
    """Bank accounts members can transfer donations to."""

    name = models.CharField(max_length=120, help_text='Bank name shown in the dropdown.')
    account_name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=80)
    branch = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'donation bank'
        verbose_name_plural = 'donation banks'

    def __str__(self):
        return self.name


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
    bank = models.ForeignKey(
        DonationBank,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='donations',
    )
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

    @property
    def provider_display(self):
        if self.payment_method == self.PaymentMethod.CHAPA:
            return 'Chapa'
        if self.bank_id:
            return self.bank.name
        return 'Bank transfer'

    @property
    def proof_is_image(self):
        if not self.manual_proof:
            return False
        name = self.manual_proof.name.lower()
        return name.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'))

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

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'blog categories'

    def __str__(self):
        return self.name


class GalleryCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(
        default=True,
        help_text='Inactive categories are hidden on the public gallery filters.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name_plural = 'gallery categories'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            base = slugify(self.name) or 'category'
            slug = base
            counter = 1
            while GalleryCategory.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

class Blog(models.Model):
    STATUS_CHOICES = [
        (1, 'Published'),
        (0, 'Unpublished'),
    ]

    class MediaType(models.TextChoices):
        IMAGE = 'image', 'Image'
        VIDEO = 'video', 'Video'

    title = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    categories = models.ManyToManyField(Category, related_name='blogs')
    description = RichTextField()
    status = models.IntegerField(choices=STATUS_CHOICES)
    media_type = models.CharField(
        max_length=10,
        choices=MediaType.choices,
        default=MediaType.IMAGE,
    )
    banner = models.ImageField(upload_to='images/', null=True, blank=True)
    banner_video = models.FileField(upload_to='blog_videos/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='blogs_added')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='blogs_updated')

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            base = slugify(self.title)[:250] or 'post'
            slug = base
            counter = 1
            while Blog.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('blog_details', kwargs={'slug': self.slug})

    @property
    def is_video_post(self):
        return self.media_type == self.MediaType.VIDEO

    @property
    def has_banner_image(self):
        return bool(self.banner)

    @property
    def has_banner_video(self):
        return bool(self.banner_video)


class Gallery(models.Model):
    category = models.ForeignKey(
        GalleryCategory,
        on_delete=models.PROTECT,
        related_name='images',
    )
    img = models.ImageField(upload_to='gallery/')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        verbose_name_plural = 'gallery images'

    def __str__(self):
        label = self.category.name if self.category_id else 'Gallery'
        if self.description:
            return f"{label} — {self.description[:40]}"
        return f"{label} — Image #{self.pk}" if self.pk else label

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