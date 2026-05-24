from django import forms
from .models import *
from ckeditor.widgets import CKEditorWidget

class BlogForm(forms.ModelForm):
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True    
    )
    
    class Meta:
        model = Blog
        fields = ['title', 'categories', 'description', 'status', 'banner']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'rich-text-editor'}),
        }


class VacancyForm(forms.ModelForm):
    description = forms.CharField(widget=CKEditorWidget())
    class Meta:
        model = Vacancy
        fields = [
            'title', 'department', 'experience', 'position','job_type', 'description',
            'location', 'salary', 'banner', 'status', 'link', 'deadline'
        ]

class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'photo']
        widgets = {
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        }

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["name", "email", "message"]


class MemberSignupForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'auth-input', 'placeholder': 'Create a password'}),
    )
    password2 = forms.CharField(
        label='Confirm password',
        widget=forms.PasswordInput(attrs={'class': 'auth-input', 'placeholder': 'Confirm your password'}),
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'address']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'auth-input', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'auth-input', 'placeholder': 'Last name'}),
            'email': forms.EmailInput(attrs={'class': 'auth-input', 'placeholder': 'Email address'}),
            'phone': forms.TextInput(attrs={'class': 'auth-input', 'placeholder': 'Phone (optional)'}),
            'address': forms.TextInput(attrs={'class': 'auth-input', 'placeholder': 'Address (optional)'}),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password1') != cleaned.get('password2'):
            raise forms.ValidationError('Passwords do not match.')
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email'].lower()
        user.email = self.cleaned_data['email'].lower()
        user.role = User.Role.MEMBER
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class DonationForm(forms.ModelForm):
    class Meta:
        model = Donation
        fields = ['amount', 'purpose', 'manual_reference', 'manual_proof']
        widgets = {
            'amount': forms.NumberInput(attrs={'min': '1', 'step': '0.01', 'class': 'form-control'}),
            'purpose': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional purpose'}),
            'manual_reference': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Bank transfer reference'}
            ),
            'manual_proof': forms.FileInput(attrs={'class': 'form-control'}),
        }


class ChapaDonationForm(forms.Form):
    amount = forms.DecimalField(
        min_value=1,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'step': '0.01'}),
    )
    purpose = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )


class MemberProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'photo']
        widgets = {
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class StaffProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'photo']
        widgets = {
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class StaffProfileAdminForm(forms.ModelForm):
    class Meta:
        model = StaffProfile
        fields = ['designation', 'department', 'is_active']


class StaffCreateForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'address']

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Email already registered.')
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password1') != cleaned.get('password2'):
            raise forms.ValidationError('Passwords do not match.')
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email'].lower()
        user.email = self.cleaned_data['email'].lower()
        user.role = User.Role.STAFF
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class StaffDesignationForm(forms.ModelForm):
    class Meta:
        model = StaffDesignation
        fields = ['title', 'description']