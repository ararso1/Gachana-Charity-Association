from django.contrib import admin
from .models import *
# Register your models here.

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'is_staff', 'is_superuser')
    list_filter = ('role', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')


admin.site.register(Blog)
admin.site.register(Vacancy)
admin.site.register(Gallery)
admin.site.register(Contact)
admin.site.register(Category)
admin.site.register(StaffDesignation)
admin.site.register(StaffProfile)
admin.site.register(MemberProfile)
admin.site.register(Donation)
admin.site.register(DonationBank)
admin.site.register(PortalSettings)

