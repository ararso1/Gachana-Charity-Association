from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from ckeditor.fields import RichTextField

# Create your models here.

class User(AbstractUser):

    phone = models.CharField(max_length=15, null=True, blank=True)
    address = models.CharField(max_length=200, null=True, blank=True)
    photo = models.ImageField(upload_to='images/', null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)
            
    def __str__(self):
        return f"{self.username}"
    
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