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
    path('blog/<slug:slug>/', views.blog_details, name='blog_details'),
    path('blog_details/<int:blog_id>/', views.blog_details_legacy, name='blog_details_legacy'),
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
    path('blog_categories/', views.blog_category_list, name='blog_category_list'),
    path('vacancy_list', views.vacancy_list, name='vacancy_list'),
    path('create_blogs', views.create_blogs, name='create_blogs'),
    path('create_vacancy', views.create_vacancy, name='create_vacancy'),
    path('edit_blog/<int:blog_id>/', views.update_blog, name='edit_blog'),
    path('delete_blog/<int:blog_id>/', views.delete_blog, name='delete_blog'),
    path('edit_vacancy/<int:vacancy_id>/', views.update_vacancy, name='edit_vacancy'),
    path('delete_vacancy/<int:vacancy_id>/', views.delete_vacancy, name='delete_vacancy'),

    path('gallery_list', views.gallery_list, name='gallery_list'),
    path('gallery_categories/', views.gallery_category_list, name='gallery_category_list'),
    path('create_gallery', views.create_gallery, name='create_gallery'),
    path('edit_gallery/<int:gallery_id>/', views.update_gallery, name='edit_gallery'),
    path('delete_gallery/<int:gallery_id>/', views.delete_gallery, name='delete_gallery'),

    path('sponsors/', views.sponsor_list, name='sponsor_list'),
    path('sponsors/add/', views.create_sponsor, name='create_sponsor'),
    path('sponsors/<int:sponsor_id>/edit/', views.update_sponsor, name='edit_sponsor'),
    path('sponsors/<int:sponsor_id>/delete/', views.delete_sponsor, name='delete_sponsor'),

    path('contact_messages/', views.contact_message_list, name='contact_message_list'),
    path('contact_messages/<int:message_id>/', views.contact_message_detail, name='contact_message_detail'),
    path('contact_messages/<int:message_id>/delete/', views.delete_contact_message, name='delete_contact_message'),

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
    path('portal/admin/members/<int:user_id>/', portal_views.portal_member_detail, name='portal_member_detail'),
    path('portal/admin/member-settings/', portal_views.portal_admin_member_settings, name='portal_admin_member_settings'),
    path('portal/admin/banks/', portal_views.portal_admin_banks, name='portal_admin_banks'),
    path('portal/admin/staff/', portal_views.portal_manage_staff, name='portal_manage_staff'),
    path('portal/admin/staff/<int:user_id>/detail/', portal_views.portal_staff_detail, name='portal_staff_detail'),
    path('portal/admin/staff/<int:user_id>/id-card/', portal_views.portal_admin_staff_id_card, name='portal_admin_staff_id_card'),

    # Donations (staff + admin)
    path('portal/donations/', portal_views.portal_donation_list, name='portal_donation_list'),
    path('portal/donations/<int:donation_id>/proof/', portal_views.portal_donation_proof, name='portal_donation_proof'),
    path('portal/donations/<int:donation_id>/confirm/', portal_views.portal_confirm_donation, name='portal_confirm_donation'),
    path('portal/donations/<int:donation_id>/reject/', portal_views.portal_reject_donation, name='portal_reject_donation'),

    # Chapa
    path('payments/chapa/callback/', portal_views.chapa_callback, name='chapa_callback'),
    path('payments/chapa/return/<str:tx_ref>/', portal_views.chapa_return, name='chapa_return'),
]