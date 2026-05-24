from django import forms
from .models import *
from ckeditor.widgets import CKEditorWidget

class BlogForm(forms.ModelForm):
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
    )
    media_type = forms.ChoiceField(
        choices=Blog.MediaType.choices,
        widget=forms.RadioSelect(attrs={'class': 'blog-media-type-input'}),
        initial=Blog.MediaType.IMAGE,
    )

    class Meta:
        model = Blog
        fields = [
            'title',
            'categories',
            'description',
            'status',
            'media_type',
            'banner',
            'banner_video',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'rich-text-editor'}),
            'banner': forms.FileInput(
                attrs={'class': 'form-control blog-banner-input', 'accept': 'image/*'}
            ),
            'banner_video': forms.FileInput(
                attrs={'class': 'form-control', 'accept': 'video/mp4,video/webm,video/quicktime,video/x-msvideo'}
            ),
        }

    def clean(self):
        cleaned = super().clean()
        media_type = cleaned.get('media_type')
        banner = cleaned.get('banner')
        banner_video = cleaned.get('banner_video')

        if media_type == Blog.MediaType.IMAGE:
            has_image = banner or (self.instance.pk and self.instance.banner)
            if not has_image:
                self.add_error('banner', 'Upload an image for image posts.')
        elif media_type == Blog.MediaType.VIDEO:
            has_video = banner_video or (self.instance.pk and self.instance.banner_video)
            if not has_video:
                self.add_error('banner_video', 'Upload a video for video posts.')
        return cleaned

    def save(self, commit=True):
        blog = super().save(commit=False)
        media_type = self.cleaned_data['media_type']
        blog.media_type = media_type

        if media_type == Blog.MediaType.IMAGE:
            new_banner = self.cleaned_data.get('banner')
            if new_banner:
                blog.banner = new_banner
            if blog.banner_video:
                blog.banner_video.delete(save=False)
                blog.banner_video = None
        else:
            new_video = self.cleaned_data.get('banner_video')
            if new_video:
                blog.banner_video = new_video
            new_cover = self.cleaned_data.get('banner')
            if new_cover:
                blog.banner = new_cover

        if commit:
            blog.save()
            self.save_m2m()
        return blog


class BlogCategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Community news'}),
        }


class GalleryCategoryForm(forms.ModelForm):
    class Meta:
        model = GalleryCategory
        fields = ['name', 'slug', 'sort_order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'auto-generated if blank'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slug'].required = False
        self.fields['slug'].help_text = 'Used in gallery URLs and filters. Leave blank to generate from name.'

    def clean_slug(self):
        slug = (self.cleaned_data.get('slug') or '').strip()
        if slug:
            return slug
        if self.instance.pk:
            return self.instance.slug
        return ''


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
        self.fields['category'].queryset = GalleryCategory.objects.order_by('sort_order', 'name')
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
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'}),
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'address']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
        }

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


class StaffAdminUpdateForm(forms.ModelForm):
    designation = forms.ModelChoiceField(
        queryset=StaffDesignation.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    department = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    is_active = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    can_manage_donations = forms.BooleanField(
        required=False,
        label='Can manage donations',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Allow this staff member to review and confirm member donations.',
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'address']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        staff_profile = kwargs.pop('staff_profile', None)
        super().__init__(*args, **kwargs)
        if staff_profile:
            self.fields['designation'].initial = staff_profile.designation_id
            self.fields['department'].initial = staff_profile.department
            self.fields['is_active'].initial = staff_profile.is_active
            self.fields['can_manage_donations'].initial = staff_profile.can_manage_donations

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        qs = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Email already registered.')
        return email


class StaffDesignationForm(forms.ModelForm):
    class Meta:
        model = StaffDesignation
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


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