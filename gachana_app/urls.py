from . import views, portal_views
from django.urls import path
from django.conf.urls import handler404
from .views import custom_404
from django.contrib.auth import views as auth_views

handler404 = custom_404

urlpatterns = [
    path('', views.home, name='home'),
    path('about', views.about, name='about'),
    path('gallery', views.gallery, name='gallery'),
    path('gallery/fetch/<str:category>/', views.fetch_gallery, name='fetch_gallery'),
    path('blogs', views.blogs, name='blogs'),
    path('blog_details/<int:blog_id>/', views.blog_details, name='blog_details'),
    path('blog_by_category_with_id', views.blog_by_category, name='blog_by_category'),
    path('blogs/category/<int:category_id>/', views.blog_by_category, name='blog_by_category_with_id'),
    path('contact', views.contact, name='contact'),
    path('climate', views.climate, name='climate'),
    path('our_work', views.our_work, name='our_work'),
    path('why_donate', views.why_donate, name='why_donate'),
    path('vacancy', views.vacancy, name='vacancy'),
    path('vacancy_details/<int:vac_id>/', views.vacancy_details, name='vacancy_details'),
    path('signin', views.signin, name='signin'),
    path('donate', views.donate, name='donate'),
    # Admin panel
    path('login/', views.user_login, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path("password-reset/", views.password_reset_request, name="password_reset_request"),
    path("reset-password/<uidb64>/<token>/", views.password_reset_confirm, name="password_reset_confirm"),
    # path('manage_category',views.manage_category,name='manage-category'),
    # path('categories',views.categories,name='category-page'),
    path('admin_dashboard',views.admin_dashboard, name='admin_panel'),
    path('blog_list', views.blog_list, name='blog_list'),
    path('vacancy_list', views.vacancy_list, name='vacancy_list'),
    path('create_blogs', views.create_blogs, name='create_blogs'),
    path('create_vacancy', views.create_vacancy, name='create_vacancy'),
    path('edit_blog/<int:blog_id>/', views.update_blog, name='edit_blog'),
    path('delete_blog/<int:blog_id>/', views.delete_blog, name='delete_blog'),
    path('edit_vacancy/<int:vacancy_id>/', views.update_vacancy, name='edit_vacancy'),
    path('delete_vacancy/<int:vacancy_id>/', views.delete_vacancy, name='delete_vacancy'),

    path('admin_page/profile', views.profile, name='profile'),
    path('admin_page/edit_profile', views.profile_edit, name='profile_edit'),

    # Member Management Portal
    path('portal/', portal_views.portal_home, name='portal_home'),
    path('portal/signup/', portal_views.member_signup, name='member_signup'),

    # Member
    path('portal/member/', portal_views.member_dashboard, name='member_dashboard'),
    path('portal/member/donate/', portal_views.member_donate, name='member_donate'),
    path('portal/member/donations/', portal_views.member_donations, name='member_donations'),
    path('portal/member/profile/', portal_views.member_profile, name='member_profile'),
    path('portal/member/card/', portal_views.member_card, name='member_card'),

    # Staff
    path('portal/staff/', portal_views.staff_dashboard, name='staff_dashboard'),
    path('portal/staff/profile/', portal_views.staff_profile_view, name='staff_profile'),
    path('portal/staff/id-card/', portal_views.staff_id_card, name='staff_id_card'),

    # Admin portal (members, staff, donations)
    path('portal/admin/', portal_views.portal_admin_dashboard, name='portal_admin_dashboard'),
    path('portal/admin/members/', portal_views.portal_manage_members, name='portal_manage_members'),
    path('portal/admin/staff/', portal_views.portal_manage_staff, name='portal_manage_staff'),

    # Donations (staff + admin)
    path('portal/donations/', portal_views.portal_donation_list, name='portal_donation_list'),
    path('portal/donations/<int:donation_id>/confirm/', portal_views.portal_confirm_donation, name='portal_confirm_donation'),
    path('portal/donations/<int:donation_id>/reject/', portal_views.portal_reject_donation, name='portal_reject_donation'),

    # Chapa
    path('payments/chapa/callback/', portal_views.chapa_callback, name='chapa_callback'),
    path('payments/chapa/return/<str:tx_ref>/', portal_views.chapa_return, name='chapa_return'),
]