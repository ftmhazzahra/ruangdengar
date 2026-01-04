from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views
from django.contrib.auth import views as auth_views

from .views import (
    RoleSelectionView,
    UserRegisterView,
    AdminRegisterView,
    CustomLoginView,
    home_view,
    landing_view,
    dashboard_admin_view,
    dashboard_user_view,
    kelola_laporan_view,
    kelola_pengguna_view,
    edit_laporan_view,
    kelola_konten_view,
    VerifyEmailView,
    ResendVerificationEmailView,
    forgot_password_view,
    reset_password_view,
    # Pastikan Anda mengimpor view untuk notifikasi jika menggunakan Class-Based View
)

urlpatterns = [
    # Verifikasi Email
    path('verify-email/', VerifyEmailView.as_view(), name='verify_email'),
    # Kirim ulang email verifikasi
    path('resend-verification/', ResendVerificationEmailView.as_view(), name='resend_verification'),
    # Lupa Password & Reset Password
    path('forgot-password/', forgot_password_view, name='forgot-password'),
    path('reset-password/', reset_password_view, name='reset-password'),
    # Landing page umum
    path('', landing_view, name='landing'),

    # Halaman login utama
    path('login/', CustomLoginView.as_view(), name='login'),

    # Logout
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Lengkapi Profil (untuk Microsoft OAuth)
    path('lengkapi-profil/', views.lengkapi_profil_view, name='lengkapi_profil'),

    # Registrasi
    path('register/select-role/', RoleSelectionView.as_view(), name='select_role'),
    path('register/user/', UserRegisterView.as_view(), name='register_user'),
    path('register/admin/', AdminRegisterView.as_view(), name='register_admin'),

    # Dashboard
    path('dashboard/admin/', dashboard_admin_view, name='dashboard_admin'),
    path('dashboard/user/', dashboard_user_view, name='dashboard_user'),

    # Detail Artikel User
    path('dashboard/user/artikel/<int:id>/', views.artikel_detail_view, name='artikel-detail'),
    # Buat Laporan User
    path('dashboard/user/buat-laporan/', views.buat_laporan_view, name='buat-laporan'),
    # Riwayat Laporan User
    path('dashboard/user/riwayat-laporan/', views.riwayat_laporan_view, name='riwayat-laporan'),
    # Detail Laporan User
    path("laporan/<int:report_id>/detail/", views.detail_laporan_view, name="detail-laporan"),
    # Booking Konseling User
    path("dashboard/user/buat-booking-konseling/", views.booking_konseling_view, name="booking-konseling"),
    # Status Laporan User
    path("dashboard/user/status-laporan/", views.status_laporan_view, name="status-laporan"),
    # Laporan Terkirim User
    path("dashboard/user/laporan-terkirim/", views.laporan_terkirim_view, name="laporan-terkirim"),
    #Kelola Jadwal Punya Admin
    path('dashboard/kelola-jadwal/', views.kelola_jadwal_view, name='kelola-jadwal'),
    # Edit Booking Konseling (Admin)
    path('dashboard/booking/<int:booking_id>/edit/', views.edit_booking_view, name='edit-booking'),
    # Cancel Booking Konseling (Admin)
    path('dashboard/booking/<int:booking_id>/cancel/', views.cancel_booking_view, name='cancel-booking'),
    # Complete Booking Konseling (Admin)
    path('dashboard/booking/<int:booking_id>/complete/', views.complete_booking_view, name='complete-booking'),
    # Delete Booking Konseling (Admin)
    path('dashboard/booking/<int:booking_id>/delete/', views.delete_booking_view, name='delete-booking'),
    # Edit Counselor (Admin)
    path('dashboard/counselor/<int:counselor_id>/edit/', views.edit_counselor_view, name='edit-counselor'),
    # Delete Counselor (Admin)
    path('dashboard/counselor/<int:counselor_id>/delete/', views.delete_counselor_view, name='delete-counselor'),
    #Lihat Jadwal Punya Admin
    path('dashboard/lihat-jadwal/', views.lihat_jadwal_view, name='lihat-jadwal'),
    
    # 🩺 Rekam Medis Konseling URLs
    path('dashboard/booking/<int:booking_id>/rekam-medis/', views.rekam_medis_list_view, name='rekam-medis-list'),
    path('dashboard/booking/<int:booking_id>/rekam-medis/add/', views.rekam_medis_add_view, name='rekam-medis-add'),
    path('dashboard/rekam-medis/<int:rekam_id>/detail/', views.rekam_medis_detail_view, name='rekam-medis-detail'),
    path('dashboard/rekam-medis/<int:rekam_id>/edit/', views.rekam_medis_edit_view, name='rekam-medis-edit'), 

    path('dashboard/kelola-laporan/', views.kelola_laporan_view, name='kelola-laporan'),
    # 🎉 Kelola Pengguna Punya Admin
    path('dashboard/kelola-pengguna/', views.kelola_pengguna_view, name='kelola-pengguna'),
    path('dashboard/user/<int:user_id>/delete/', views.delete_user_view, name='delete-user'),
    # Edit Laporan (URL BARU)
    path('dashboard/laporan/edit/<int:report_id>/', views.edit_laporan_view, name='edit-laporan'), 
    # Admin detail laporan (read-only view for admins)
    path('dashboard/laporan/<int:report_id>/detail/', views.admin_laporan_detail_view, name='admin-detail-laporan'),
    # Delete laporan (admin)
    path('dashboard/laporan/<int:report_id>/delete/', views.delete_laporan_view, name='delete-laporan'),
    # 🎉 URL BARU UNTUK KELOLA KONTEN
    path('dashboard/kelola-konten/', views.kelola_konten_view, name='kelola-konten'),
    path('dashboard/konten/<int:konten_id>/edit/', views.edit_konten_view, name='edit-konten'),
    path('dashboard/konten/<int:konten_id>/delete/', views.delete_konten_view, name='delete-konten'),
    path('dashboard/konten/<int:konten_id>/toggle/', views.toggle_konten_view, name='toggle-konten'),
    # API endpoint untuk fetch konten
    path('api/konten/<int:konten_id>/', views.get_konten_api, name='get-konten-api'),
    
    # Edit Profile (Admin & User)
    path('profile/edit/', views.edit_profile_view, name='edit-profile'),
    
    # 🔔 Notification URLs
    path('notifikasi/', views.notification_list_view, name='notifikasi'),
    path('notifikasi/<int:notification_id>/read/', views.mark_notification_read_view, name='mark-notification-read'),
    path('notifikasi/read-all/', views.mark_all_notifications_read_view, name='mark-all-notifications-read'),
    
    # 🔒 Privacy Policy
    path('kebijakan-privasi/', views.kebijakan_privasi_view, name='kebijakan-privasi'),
    
    # 💬 Bantuan & Kontak
    path('bantuan/', views.bantuan_view, name='bantuan'),
    
    # 🎯 Admin Approval URLs
    path('dashboard/admin/<int:user_id>/approve/', views.approve_admin_view, name='approve-admin'),
    path('dashboard/admin/<int:user_id>/reject/', views.reject_admin_view, name='reject-admin'),
    
    # Home
    path('home/', home_view, name='home'),
]