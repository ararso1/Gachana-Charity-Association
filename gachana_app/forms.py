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


class GalleryForm(forms.ModelForm):
    class Meta:
        model = Gallery
        fields = ['category', 'img', 'description']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'img': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['img'].required = False


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
        fields = ['amount', 'bank', 'manual_proof']
        widgets = {
            'amount': forms.NumberInput(
                attrs={'min': '1', 'step': '0.01', 'class': 'form-control member-input', 'placeholder': '0.00'}
            ),
            'bank': forms.Select(attrs={'class': 'form-select member-input', 'id': 'id_bank'}),
            'manual_proof': forms.FileInput(
                attrs={'class': 'form-control member-input', 'accept': 'image/*,.pdf'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bank'].queryset = DonationBank.objects.filter(is_active=True)
        self.fields['bank'].empty_label = 'Select a bank'
        self.fields['bank'].required = True
        self.fields['manual_proof'].required = True

    def clean_bank(self):
        bank = self.cleaned_data.get('bank')
        if not bank or not bank.is_active:
            raise forms.ValidationError('Please select a valid bank.')
        return bank


class DonationBankForm(forms.ModelForm):
    class Meta:
        model = DonationBank
        fields = ['name', 'account_name', 'account_number', 'branch', 'is_active', 'sort_order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'branch': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }


class ChapaDonationForm(forms.Form):
    amount = forms.DecimalField(
        min_value=1,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={'class': 'form-control member-input', 'min': '1', 'step': '0.01', 'placeholder': '0.00'}
        ),
    )


class MemberProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'photo']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control member-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control member-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-control member-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-control member-input'}),
            'address': forms.TextInput(attrs={'class': 'form-control member-input'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control member-input'}),
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


class PortalSettingsForm(forms.ModelForm):
    class Meta:
        model = PortalSettings
        fields = ['annual_giving_goal', 'giving_goal_headline', 'giving_goal_message']
        widgets = {
            'annual_giving_goal': forms.NumberInput(
                attrs={'class': 'form-control', 'min': '1', 'step': '0.01'}
            ),
            'giving_goal_headline': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Help us however you can'}
            ),
            'giving_goal_message': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4}
            ),
        }

    def clean_annual_giving_goal(self):
        goal = self.cleaned_data['annual_giving_goal']
        if goal is not None and goal <= 0:
            raise forms.ValidationError('Goal must be greater than zero.')
        return goal