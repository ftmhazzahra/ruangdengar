# View untuk kirim ulang email verifikasi
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View as DjangoView

class ResendVerificationEmailView(DjangoView):
    def get(self, request):
        return render(request, 'users/resend_verification.html')

    def post(self, request):
        from .email_utils import send_notification_email
        import secrets
        email = request.POST.get('email')
        user = CustomUser.objects.filter(email=email).first()
        if not user:
            messages.error(request, 'Email tidak ditemukan.')
            return render(request, 'users/resend_verification.html')
        if user.email_verified:
            messages.info(request, 'Email sudah diverifikasi. Silakan login.')
            return render(request, 'users/resend_verification.html')
        # Generate token baru dan kirim ulang email verifikasi
        user.email_verification_token = secrets.token_urlsafe(32)
        user.save()
        verify_url = request.build_absolute_uri(f"/verify-email/?token={user.email_verification_token}&email={user.email}")
        context = {'user': user, 'verify_url': verify_url}
        send_notification_email(
            subject='Verifikasi Email Akun Ruang Dengar',
            recipient_list=[user.email],
            template_name='emails/email_confirm.html',
            context=context,
            fail_silently=False
        )
        messages.success(request, 'Email verifikasi sudah dikirim ulang. Silakan cek inbox Anda.')
        return render(request, 'users/resend_verification.html')
# View untuk verifikasi email
from django.views import View
from django.shortcuts import get_object_or_404
from .models import CustomUser
from django.utils import timezone

class VerifyEmailView(View):
    def get(self, request):
        token = request.GET.get('token')
        email = request.GET.get('email')
        user = get_object_or_404(CustomUser, email=email, email_verification_token=token)
        if not user.email_verified:
            user.email_verified = True
            user.email_verification_token = None
            # Jika admin, tetap tidak aktif sampai disetujui super admin
            if user.role == CustomUser.Role.ADMIN:
                user.is_active = False
                user.save()
                messages.success(request, 'Email berhasil diverifikasi! Akun Anda menunggu persetujuan super admin.')
            else:
                user.is_active = True
                user.save()
                messages.success(request, 'Email berhasil diverifikasi! Silakan login.')
        else:
            messages.info(request, 'Email sudah diverifikasi. Silakan login.')
        return redirect('login')
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from types import SimpleNamespace
import os
from django.contrib import messages
from django.urls import reverse_lazy
from django.views import generic
from django.contrib.auth import views as auth_views
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import CustomUser, Laporan, Progress, Evidence, Booking, Counselor, Konten, Notification, RekamMedisKonseling
from django.utils import timezone
from datetime import datetime, timedelta
from .forms import CustomUserCreationForm, AdminUserCreationForm, CustomAuthenticationForm
from .ai_moderation import moderate_laporan
from .email_utils import (
    send_laporan_created_notification,
    send_laporan_status_updated_notification,
    send_urgent_laporan_alert,
    send_booking_created_notification,
    send_high_risk_alert,
    get_admin_emails,
    get_management_emails
)
import logging

logger = logging.getLogger(__name__)


# 🏠 Landing Page (public)
def landing_view(request):
    return render(request, 'landing.html', {})


# 🧩 Lengkapi Profil (untuk Google OAuth)
@login_required
def lengkapi_profil_view(request):
    """
    View untuk melengkapi profil user setelah login dengan Google OAuth
    """
    user = request.user
    
    # Jika profil sudah lengkap, redirect ke dashboard
    if user.is_profile_complete:
        if user.role == CustomUser.Role.ADMIN:
            return redirect('dashboard_admin')
        else:
            return redirect('dashboard_user')
    
    if request.method == 'POST':
        # Ambil data dari form
        status_pengguna = request.POST.get('status_pengguna')
        nim = request.POST.get('nim')
        nidn = request.POST.get('nidn')
        fakultas = request.POST.get('fakultas')
        prodi = request.POST.get('prodi')
        usia = request.POST.get('usia')
        no_whatsapp = request.POST.get('no_whatsapp')
        
        # Update user
        user.status_pengguna = status_pengguna
        if status_pengguna == 'Mahasiswa':
            user.nim = nim
        else:
            user.nidn = nidn
        user.fakultas = fakultas
        user.prodi = prodi
        user.usia = usia
        user.no_whatsapp = no_whatsapp
        user.is_profile_complete = True
        user.save()
        
        messages.success(request, 'Profil berhasil dilengkapi! Selamat datang di Ruang Dengar.')
        
        # Redirect berdasarkan role
        if user.role == CustomUser.Role.ADMIN:
            return redirect('dashboard_admin')
        else:
            return redirect('dashboard_user')
    
    return render(request, 'users/lengkapi_profil.html', {'user': user})


# 🧩 Halaman Pilih Role
class RoleSelectionView(generic.TemplateView):
    template_name = 'users/role_selection.html'


# 🧩 Registrasi Pengguna
class UserRegisterView(generic.CreateView):
    form_class = CustomUserCreationForm
    template_name = 'users/register_user.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        import secrets
        from django.utils import timezone
        from .email_utils import send_notification_email
        user = form.save(commit=False)
        user.is_active = False  # User tidak bisa login sebelum verifikasi
        user.email_verified = False
        user.email_verification_token = secrets.token_urlsafe(32)
        user.email_verification_sent_at = timezone.now()
        user.save()

        # Kirim email verifikasi
        verify_url = self.request.build_absolute_uri(
            f"/verify-email/?token={user.email_verification_token}&email={user.email}"
        )
        context = {
            'user': user,
            'verify_url': verify_url,
        }
        send_notification_email(
            subject='Verifikasi Email Akun Ruang Dengar',
            recipient_list=[user.email],
            template_name='emails/email_confirm.html',
            context=context,
            fail_silently=False
        )
        messages.success(self.request, 'Akun berhasil dibuat! Silakan cek email Anda untuk verifikasi sebelum login.')
        return super().form_valid(form)


# 🧩 Registrasi Admin
class AdminRegisterView(generic.CreateView):
    form_class = AdminUserCreationForm
    template_name = 'users/register_admin.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        import secrets
        from django.utils import timezone
        from .email_utils import send_notification_email
        # Set akun admin baru sebagai pending (tidak aktif) dan belum disetujui
        user = form.save(commit=False)
        user.is_active = False  # Akun tidak aktif sampai disetujui
        user.is_approved = False  # Belum disetujui
        user.email_verified = False
        user.email_verification_token = secrets.token_urlsafe(32)
        user.email_verification_sent_at = timezone.now()
        user.save()

        # Kirim email verifikasi
        verify_url = self.request.build_absolute_uri(
            f"/verify-email/?token={user.email_verification_token}&email={user.email}"
        )
        context = {
            'user': user,
            'verify_url': verify_url,
        }
        send_notification_email(
            subject='Verifikasi Email Akun Admin Ruang Dengar',
            recipient_list=[user.email],
            template_name='emails/email_confirm.html',
            context=context,
            fail_silently=False
        )
        messages.success(self.request, 'Pendaftaran admin berhasil! Silakan cek email Anda untuk verifikasi sebelum menunggu persetujuan super admin.')
        return redirect(self.success_url)


# 🧩 Login View
class CustomLoginView(auth_views.LoginView):
    template_name = 'users/login.html'
    form_class = CustomAuthenticationForm

    def get_success_url(self):
        user = self.request.user
        # Cek jika admin belum disetujui
        if user.role == CustomUser.Role.ADMIN and not user.is_approved:
            messages.warning(self.request, 'Akun admin Anda masih menunggu persetujuan dari super admin.')
            return reverse_lazy('login')
        # Arahkan sesuai role
        if user.role == CustomUser.Role.ADMIN:
            return reverse_lazy('dashboard_admin')
        else:
            return reverse_lazy('dashboard_user')

    def form_valid(self, form):
        remember_me = form.cleaned_data.get('remember_me')
        if not remember_me:
            self.request.session.set_expiry(0)
            messages.info(self.request, 'Anda akan logout otomatis saat browser ditutup.')
        else:
            self.request.session.set_expiry(None)

        user = form.get_user()
        # Cek jika user belum verifikasi email, kecuali superuser
        if not user.email_verified and not user.is_superuser:
            messages.error(self.request, 'Akun Anda belum diverifikasi. Silakan cek email Anda untuk verifikasi sebelum login.')
            return redirect('login')
        # Cek jika user admin dan belum diapprove
        if user.role == CustomUser.Role.ADMIN and not user.is_approved:
            messages.error(self.request, 'Akun admin Anda masih menunggu persetujuan. Silakan hubungi super admin.')
            return redirect('login')
        return super().form_valid(form)


# 🧩 Dashboard Admin
@login_required(login_url='login')
def dashboard_admin_view(request):
    logger.debug(f"dashboard_admin: user={request.user.email}, role={request.user.role}, is_admin={request.user.role == CustomUser.Role.ADMIN}")
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
        return redirect('dashboard_user')
    
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Count, Q
    
    # Get current month date range
    today = timezone.now().date()
    first_day_month = today.replace(day=1)
    
    # Statistics
    # 1. Sesi Konseling Mendatang (status terjadwal, tanggal >= hari ini)
    upcoming_sessions = Booking.objects.filter(status='terjadwal', tanggal__gte=today).count()
    total_sessions_month = Booking.objects.filter(tanggal__gte=first_day_month).count()
    
    # 2. Laporan Terbaru (semua laporan)
    new_reports = Laporan.objects.filter(status__in=['diterima', 'verifikasi_awal']).count()
    total_reports = Laporan.objects.count()
    
    # 3. Total Konten dari database
    total_content = Konten.objects.filter(is_published=True).count()
    
    # 4. Jenis Konseling Statistics untuk chart
    jenis_stats = Booking.objects.values('jenis').annotate(count=Count('jenis')).order_by('-count')
    
    # 4b. Jenis Laporan Statistics untuk pie chart
    jenis_laporan_stats = Laporan.objects.values('jenis').annotate(count=Count('jenis')).order_by('-count')
    
    # 5. Monthly Booking Trends (last 12 months)
    from datetime import date
    from django.db.models.functions import TruncMonth
    
    # Get 12 months ago (more accurate: use relative_delta or datetime arithmetic)
    # Calculate first day of current month
    first_day_this_month = today.replace(day=1)
    # Go back 12 months from first day of this month
    twelve_months_ago = first_day_this_month - timedelta(days=1)
    twelve_months_ago = twelve_months_ago.replace(day=1)
    
    logger.debug(f"Today: {today}, Twelve months ago: {twelve_months_ago}")
    
    # Query bookings grouped by month and jenis
    monthly_bookings = Booking.objects.filter(
        tanggal__gte=twelve_months_ago
    ).annotate(
        month=TruncMonth('tanggal')
    ).values('month', 'jenis').annotate(
        count=Count('id')
    ).order_by('month')
    
    # Generate last 12 months labels
    from calendar import month_abbr
    import locale
    
    # Try to set Indonesian locale, fall back to default if not available
    try:
        locale.setlocale(locale.LC_TIME, 'id_ID.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, 'id_ID')
        except locale.Error:
            pass  # Use system default locale
    
    months_labels = []
    months_data = {}
    
    # Generate 12 months from current month going backwards
    for i in range(11, -1, -1):
        # Calculate month by going back i months
        year = first_day_this_month.year
        month = first_day_this_month.month
        
        # Subtract i months
        month = month - i
        while month <= 0:
            month += 12
            year -= 1
        
        # Create timezone-aware datetime
        month_date = timezone.make_aware(datetime(year, month, 1))
        month_label = month_date.strftime('%b')
        months_labels.append(month_label)
        months_data[month_date] = {}
    
    logger.debug(f"Month labels: {months_labels}")
    logger.debug(f"Month keys: {list(months_data.keys())}")
    
    # Fill data from query
    for booking in monthly_bookings:
        month_key = booking['month']
        jenis = booking['jenis']
        count = booking['count']
        if month_key in months_data:
            months_data[month_key][jenis] = count
    
    # Get unique jenis for datasets
    all_jenis = list(Booking.objects.values_list('jenis', flat=True).distinct())
    
    # Build datasets for each jenis
    monthly_datasets = []
    color_map = {
        'Karier & Pengembangan Diri': '#6366f1',
        'Akademik & Studi': '#3b82f6',
        'Hubungan Interpersonal': '#fbbf24',
        'Kesehatan Mental': '#10b981',
        'Keluarga': '#a855f7',
        'Lainnya': '#ef4444'
    }
    
    for jenis in all_jenis:
        if jenis:
            data_points = []
            for month_key in sorted(months_data.keys()):
                data_points.append(months_data[month_key].get(jenis, 0))
            
            monthly_datasets.append({
                'label': jenis,
                'data': data_points,
                'backgroundColor': color_map.get(jenis, '#9ca3af')
            })
    
    # 6. Monthly Laporan Trends (last 12 months) - CHART BARU
    # Get all laporans in last 12 months
    all_laporans_12m = Laporan.objects.filter(
        created_at__gte=twelve_months_ago
    ).values('created_at', 'jenis')
    
    logger.debug(f"Total laporans in 12 months: {all_laporans_12m.count()}")
    print(f"[DEBUG] Total laporans: {all_laporans_12m.count()}")
    
    # Manually group by month
    laporan_months_data = {month_key: {} for month_key in months_data.keys()}
    
    print(f"[DEBUG] Expected month keys: {list(laporan_months_data.keys())}")
    
    for laporan_obj in all_laporans_12m:
        created_dt = laporan_obj['created_at']
        if created_dt:
            # Create month_key - preserve timezone!
            month_key = created_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            jenis = laporan_obj['jenis']
            
            print(f"[DEBUG] Processing: created_dt={created_dt}, month_key={month_key}, jenis={jenis}, in_dict={month_key in laporan_months_data}")
            
            if month_key in laporan_months_data:
                if jenis not in laporan_months_data[month_key]:
                    laporan_months_data[month_key][jenis] = 0
                laporan_months_data[month_key][jenis] += 1
            else:
                # Try to find matching key by date only (ignore time/timezone differences)
                matched = False
                for key in laporan_months_data.keys():
                    if key.year == month_key.year and key.month == month_key.month:
                        if jenis not in laporan_months_data[key]:
                            laporan_months_data[key][jenis] = 0
                        laporan_months_data[key][jenis] += 1
                        matched = True
                        print(f"[DEBUG] Matched with key: {key}")
                        break
                if not matched:
                    print(f"[DEBUG] No match found for month_key: {month_key}")
    
    logger.debug(f"Laporan months_data after fill: {laporan_months_data}")
    print(f"[DEBUG] Laporan months_data: {laporan_months_data}")
    
    # Get unique jenis laporan for datasets
    all_jenis_laporan = list(Laporan.objects.values_list('jenis', flat=True).distinct())
    
    # Build datasets for each jenis laporan
    laporan_datasets = []
    laporan_color_map = {
        'Kekerasan Fisik': '#ef4444',
        'Kekerasan Psikis': '#f59e0b',
        'Kekerasan Seksual': '#dc2626',
        'Diskriminasi': '#8b5cf6',
        'Perundungan (Bullying)': '#ec4899',
        'Pelecehan': '#f43f5e',
        'Lainnya': '#6b7280'
    }
    
    # Debug log
    logger.debug(f"All jenis laporan: {all_jenis_laporan}")
    logger.debug(f"Laporan months data keys: {list(laporan_months_data.keys())}")
    print(f"[DEBUG] All jenis laporan: {all_jenis_laporan}")
    
    for jenis in all_jenis_laporan:
        if jenis:
            data_points = []
            for month_key in sorted(laporan_months_data.keys()):
                value = laporan_months_data[month_key].get(jenis, 0)
                data_points.append(value)
            
            logger.debug(f"Dataset for {jenis}: {data_points}")
            
            laporan_datasets.append({
                'label': jenis,
                'data': data_points,
                'backgroundColor': laporan_color_map.get(jenis, '#9ca3af')
            })
    
    logger.debug(f"Total laporan_datasets: {len(laporan_datasets)}")
    
    # 7. Recent Activities (last 10 activities from bookings and reports)
    recent_bookings = Booking.objects.select_related('user').order_by('-created_at')[:5]
    recent_reports = Laporan.objects.select_related('pelapor').order_by('-created_at')[:5]
    
    # Combine and sort activities
    activities = []
    for booking in recent_bookings:
        activities.append({
            'type': 'booking',
            'time': booking.created_at,
            'description': f'Booking konseling - {booking.user.nama_lengkap if booking.user else booking.nama}',
            'detail': f'{booking.jenis} dengan {booking.konselor}',
            'status': booking.status
        })
    
    for laporan in recent_reports:
        activities.append({
            'type': 'report',
            'time': laporan.created_at,
            'description': f'Laporan baru - {laporan.kode}',
            'detail': laporan.jenis,
            'status': laporan.status
        })
    
    # Sort by time descending and take top 10
    activities.sort(key=lambda x: x['time'], reverse=True)
    activities = activities[:10]
    
    return render(request, 'dashboard.html', {
        'nama_user': request.user.nama_lengkap,
        'email_user': request.user.email,
        'active_page': 'dashboard',
        'upcoming_sessions': upcoming_sessions,
        'total_sessions_month': total_sessions_month,
        'new_reports': new_reports,
        'total_reports': total_reports,
        'total_content': total_content,
        'jenis_stats': jenis_stats,
        'jenis_laporan_stats': jenis_laporan_stats,  # PIE CHART LAPORAN
        'months_labels': months_labels,
        'monthly_datasets': monthly_datasets,
        'laporan_datasets': laporan_datasets,  # BAR CHART LAPORAN
        'activities': activities,
    })

# 🧩 Halaman Kelola Jadwal Konseling (Admin)
@login_required(login_url='login')
def kelola_jadwal_view(request):
    logger.debug(f"kelola_jadwal: user={request.user.email}, role={request.user.role}, is_admin={request.user.role == CustomUser.Role.ADMIN}")
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
        return redirect('dashboard_user')

    # Handle POST request to add new counselor
    if request.method == 'POST' and request.POST.get('action') == 'add_counselor':
        counselor_name = request.POST.get('counselor_name', '').strip()
        counselor_title = request.POST.get('counselor_title', '').strip()
        if counselor_name:
            Counselor.objects.create(name=counselor_name, title=counselor_title)
            messages.success(request, f'Konselor {counselor_name} berhasil ditambahkan.')
        else:
            messages.error(request, 'Nama konselor tidak boleh kosong.')
        return redirect('kelola-jadwal')
    
    # Handle POST request to add new booking
    if request.method == 'POST' and request.POST.get('action') == 'add_booking':
        user_id = request.POST.get('user_id', '').strip()
        tanggal = request.POST.get('tanggal', '').strip()
        waktu = request.POST.get('waktu', '').strip()
        konselor_id = request.POST.get('konselor_id', '').strip()
        topik = request.POST.get('topik', '').strip()
        jenis = request.POST.get('jenis', '').strip()
        
        # Debug: log what we received
        logger.debug(f"Add Booking: user_id={user_id}, tanggal={tanggal}, waktu={waktu}, konselor_id={konselor_id}, jenis={jenis}")
        
        if not all([user_id, tanggal, waktu, konselor_id, jenis]):
            missing = []
            if not user_id: missing.append('user_id')
            if not tanggal: missing.append('tanggal')
            if not waktu: missing.append('waktu')
            if not konselor_id: missing.append('konselor_id')
            if not jenis: missing.append('jenis')
            messages.error(request, f'Field wajib belum diisi: {", ".join(missing)}')
            return redirect('kelola-jadwal')
        
        try:
            user = CustomUser.objects.get(pk=user_id)
            counselor = Counselor.objects.get(pk=konselor_id)
            
            # Parse date and time
            tanggal_obj = datetime.strptime(tanggal, '%Y-%m-%d').date()
            waktu_obj = datetime.strptime(waktu, '%H:%M').time()
            
            # Check for conflicts
            existing = Booking.objects.filter(
                tanggal=tanggal_obj,
                waktu=waktu_obj,
                konselor_fk=counselor,
                status='terjadwal'
            ).exists()
            
            if existing:
                messages.error(request, 'Konselor sudah memiliki jadwal pada waktu tersebut.')
                return redirect('kelola-jadwal')
            
            # Get lokasi dan catatan
            lokasi = request.POST.get('lokasi_konseling', 'REK-407').strip()
            catatan = request.POST.get('catatan_admin', '').strip()
            
            # Create booking
            booking = Booking.objects.create(
                user=user,
                tanggal=tanggal_obj,
                waktu=waktu_obj,
                konselor=counselor.name,
                konselor_fk=counselor,
                nama=user.nama_lengkap,
                topik=topik,
                jenis=jenis,
                status='terjadwal',
                lokasi_konseling=lokasi,
                catatan_admin=catatan if catatan else None
            )
            
            # Log booking creation
            logger.debug(f"Booking created: ID={booking.id}, user_id={booking.user.id}, email={booking.user.email}, nama_lengkap={booking.user.nama_lengkap}, tanggal={booking.tanggal}, waktu={booking.waktu}")
            
            # Verify it can be queried back
            test_query = Booking.objects.filter(user=user).count()
            logger.debug(f"Total bookings for this user: {test_query}")
            
            messages.success(request, f'Jadwal konseling untuk {user.nama_lengkap} berhasil ditambahkan.')
        except CustomUser.DoesNotExist:
            messages.error(request, 'User tidak ditemukan.')
        except Counselor.DoesNotExist:
            messages.error(request, 'Konselor tidak ditemukan.')
        except Exception as e:
            messages.error(request, f'Gagal menambahkan jadwal: {str(e)}')
        
        return redirect('kelola-jadwal')

    # Base query: default 7 hari terakhir sampai tanggal ke depan
    today = timezone.now().date()
    seven_days_ago = today - timedelta(days=7)
    bookings = Booking.objects.select_related('user', 'konselor_fk').filter(tanggal__gte=seven_days_ago)
    
    # Apply filters from GET parameters
    tanggal_dari = request.GET.get('tanggal_dari')
    tanggal_sampai = request.GET.get('tanggal_sampai')
    konselor_id = request.GET.get('konselor')
    jenis = request.GET.get('jenis')
    status = request.GET.get('status')
    
    if tanggal_dari:
        bookings = bookings.filter(tanggal__gte=tanggal_dari)
    if tanggal_sampai:
        bookings = bookings.filter(tanggal__lte=tanggal_sampai)
    if konselor_id and konselor_id != 'semua':
        bookings = bookings.filter(konselor_fk_id=konselor_id)
    if jenis and jenis != 'semua':
        bookings = bookings.filter(jenis=jenis)
    if status and status != 'semua':
        bookings = bookings.filter(status=status.lower())
    
    # Order by date and time descending
    bookings = bookings.order_by('-tanggal', '-waktu')
    counselors = Counselor.objects.all()
    users = CustomUser.objects.filter(role=CustomUser.Role.USER).order_by('nim', 'nama_lengkap')
    
    return render(request, 'dashboard/kelola_jadwal.html', {
        'nama_user': request.user.nama_lengkap,
        'email_user': request.user.email,
        'active_page': 'kelola-jadwal',  # supaya menu sidebar aktif
        'bookings': bookings,
        'counselors': counselors,
        'users': users,
    })

# 🧩 Edit Booking Konseling (Admin)
@login_required(login_url='login')
def edit_booking_view(request, booking_id):
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
        return redirect('dashboard_user')
    
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('kelola-jadwal')
    
    try:
        booking = Booking.objects.get(pk=booking_id)
    except Booking.DoesNotExist:
        messages.error(request, 'Booking tidak ditemukan.')
        return redirect('kelola-jadwal')
    
    # Simpan nilai lama untuk deteksi perubahan
    old_tanggal = booking.tanggal
    old_waktu = booking.waktu
    old_konselor = booking.konselor
    old_lokasi = booking.lokasi_konseling
    schedule_changed = False
    lokasi_changed = False
    
    # Update booking fields
    tanggal = request.POST.get('tanggal')
    waktu = request.POST.get('waktu')
    konselor_id = request.POST.get('konselor_id', '').strip()
    topik = request.POST.get('topik', '').strip()
    jenis = request.POST.get('jenis', '').strip()
    status = request.POST.get('status', '').strip()
    
    try:
        if tanggal:
            new_tanggal = datetime.strptime(tanggal, '%Y-%m-%d').date()
            if old_tanggal != new_tanggal:
                schedule_changed = True
            booking.tanggal = new_tanggal
        if waktu:
            # Handle time format (might be "HH:MM" or "HH:MM - HH:MM")
            waktu_clean = waktu.split('-')[0].strip() if '-' in waktu else waktu.strip()
            new_waktu = datetime.strptime(waktu_clean, '%H:%M').time()
            if old_waktu != new_waktu:
                schedule_changed = True
            booking.waktu = new_waktu
        if konselor_id:
            try:
                counselor = Counselor.objects.get(pk=konselor_id)
                if old_konselor != counselor.name:
                    schedule_changed = True
                booking.konselor = counselor.name
                booking.konselor_fk = counselor
            except Counselor.DoesNotExist:
                pass
        if topik:
            booking.topik = topik
        if jenis:
            booking.jenis = jenis
        if status:
            booking.status = status.lower()
        
        # Update lokasi dan catatan admin
        lokasi = request.POST.get('lokasi_konseling', 'REK-407').strip()
        catatan = request.POST.get('catatan_admin', '').strip()
        if lokasi and lokasi != old_lokasi:
            lokasi_changed = True
            booking.lokasi_konseling = lokasi
        if catatan is not None:  # Allow empty string to clear notes
            booking.catatan_admin = catatan
        
        booking.save()
        
        # 🔔 Notifikasi ke User - Jadwal atau Lokasi Berubah
        if (schedule_changed or lokasi_changed) and booking.user:
            if lokasi_changed and not schedule_changed:
                # Hanya lokasi yang berubah
                Notification.objects.create(
                    user=booking.user,
                    title='📍 Lokasi Konseling Diperbarui',
                    message=f'Lokasi konseling Anda untuk "{booking.topik}" telah diubah menjadi {booking.lokasi_konseling}. Tanggal: {booking.tanggal.strftime("%d/%m/%Y")}, Waktu: {booking.waktu.strftime("%H:%M")}.',
                    type='jadwal_berubah',
                    booking=booking
                )
            else:
                # Jadwal berubah (mungkin dengan lokasi juga)
                Notification.objects.create(
                    user=booking.user,
                    title='📅 Jadwal Konseling Diperbarui',
                    message=f'Jadwal konseling Anda untuk "{booking.topik}" telah diperbarui. Tanggal: {booking.tanggal.strftime("%d/%m/%Y")}, Waktu: {booking.waktu.strftime("%H:%M")}, Konselor: {booking.konselor}, Lokasi: {booking.lokasi_konseling}.',
                    type='jadwal_berubah',
                    booking=booking
                )
        
        messages.success(request, '✅ Perubahan berhasil disimpan!')
    except Exception as e:
        messages.error(request, f'Gagal menyimpan perubahan: {str(e)}')
    
    return redirect('kelola-jadwal')

# 🧩 Halaman Lihat Jadwal Konseling (Admin)
@login_required(login_url='login')
def lihat_jadwal_view(request):
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
        return redirect('dashboard_user')  # redirect ke dashboard user

    # show all bookings (termasuk yang dibatalkan)
    bookings = Booking.objects.select_related('user', 'konselor_fk').all().order_by('tanggal', 'waktu')
    counselors = Counselor.objects.all()
    return render(request, 'dashboard/lihat_jadwal.html', {
        'nama_user': request.user.nama_lengkap,
        'email_user': request.user.email,
        'active_page': 'lihat-jadwal',
        'bookings': bookings,
        'counselors': counselors,
    })


def cancel_booking_view(request, booking_id):
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, 'Anda tidak memiliki akses untuk membatalkan booking.')
        return redirect('dashboard_user')
    
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('lihat-jadwal')
    
    try:
        booking = Booking.objects.get(pk=booking_id)
        alasan = request.POST.get('alasan_pembatalan', '').strip()
        
        if booking.status in ['selesai', 'dibatalkan']:
            messages.error(request, f'Booking ini sudah berstatus {booking.status}. Tidak dapat dibatalkan.')
            return redirect('lihat-jadwal')
        
        if not alasan:
            messages.error(request, 'Alasan pembatalan harus diisi.')
            return redirect('lihat-jadwal')
        
        booking.status = 'dibatalkan'
        booking.alasan_pembatalan = alasan
        booking.save()
        
        # 🔔 Notifikasi ke User - Booking Dibatalkan
        if booking.user:
            Notification.objects.create(
                user=booking.user,
                title='❌ Jadwal Konseling Dibatalkan',
                message=f'Maaf, jadwal konseling Anda untuk "{booking.topik}" pada {booking.tanggal.strftime("%d/%m/%Y")} telah dibatalkan oleh admin. Alasan: {alasan}',
                type='jadwal_dibatalkan',
                booking=booking
            )
        
        messages.success(request, f'Booking berhasil dibatalkan. Alasan: {alasan}')
        return redirect('lihat-jadwal')
    
    except Booking.DoesNotExist:
        messages.error(request, 'Booking tidak ditemukan.')
        return redirect('lihat-jadwal')
    except Exception as e:
        messages.error(request, f'Gagal membatalkan booking: {str(e)}')
        return redirect('lihat-jadwal')


def complete_booking_view(request, booking_id):
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, 'Anda tidak memiliki akses untuk menyelesaikan booking.')
        return redirect('dashboard_user')
    
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('lihat-jadwal')
    
    try:
        booking = Booking.objects.get(pk=booking_id)
        
        if booking.status in ['selesai', 'dibatalkan']:
            messages.error(request, f'Booking ini sudah berstatus {booking.status}.')
            return redirect('lihat-jadwal')
        
        booking.status = 'selesai'
        booking.save()
        
        messages.success(request, f'Booking berhasil ditandai sebagai selesai.')
        return redirect('lihat-jadwal')
    
    except Booking.DoesNotExist:
        messages.error(request, 'Booking tidak ditemukan.')
        return redirect('lihat-jadwal')
    except Exception as e:
        messages.error(request, f'Gagal menyelesaikan booking: {str(e)}')
        return redirect('lihat-jadwal')


@login_required(login_url='login')
def delete_booking_view(request, booking_id):
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, 'Anda tidak memiliki akses untuk menghapus booking.')
        return redirect('dashboard_user')
    
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('kelola-jadwal')
    
    try:
        booking = Booking.objects.get(pk=booking_id)
        nama_klien = booking.nama
        booking.delete()
        
        messages.success(request, f'Booking untuk {nama_klien} berhasil dihapus.')
        return redirect('kelola-jadwal')
    
    except Booking.DoesNotExist:
        messages.error(request, 'Booking tidak ditemukan.')
        return redirect('kelola-jadwal')
    except Exception as e:
        messages.error(request, f'Gagal menghapus booking: {str(e)}')
        return redirect('kelola-jadwal')


@login_required(login_url='login')
def edit_counselor_view(request, counselor_id):
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, 'Anda tidak memiliki akses untuk mengedit konselor.')
        return redirect('dashboard_user')
    
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('kelola-jadwal')
    
    try:
        counselor = Counselor.objects.get(pk=counselor_id)
        counselor_name = request.POST.get('counselor_name', '').strip()
        counselor_title = request.POST.get('counselor_title', '').strip()
        
        if not counselor_name:
            messages.error(request, 'Nama konselor tidak boleh kosong.')
            return redirect('kelola-jadwal')
        
        counselor.name = counselor_name
        counselor.title = counselor_title
        counselor.save()
        
        messages.success(request, f'Konselor {counselor_name} berhasil diperbarui.')
        return redirect('kelola-jadwal')
    
    except Counselor.DoesNotExist:
        messages.error(request, 'Konselor tidak ditemukan.')
        return redirect('kelola-jadwal')
    except Exception as e:
        messages.error(request, f'Gagal mengedit konselor: {str(e)}')
        return redirect('kelola-jadwal')


@login_required(login_url='login')
def delete_counselor_view(request, counselor_id):
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, 'Anda tidak memiliki akses untuk menghapus konselor.')
        return redirect('dashboard_user')
    
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('kelola-jadwal')
    
    try:
        counselor = Counselor.objects.get(pk=counselor_id)
        counselor_name = counselor.name
        
        # Check if counselor has bookings
        booking_count = Booking.objects.filter(konselor_fk=counselor).count()
        if booking_count > 0:
            messages.error(request, f'Tidak dapat menghapus konselor {counselor_name} karena masih memiliki {booking_count} booking.')
            return redirect('kelola-jadwal')
        
        counselor.delete()
        messages.success(request, f'Konselor {counselor_name} berhasil dihapus.')
        return redirect('kelola-jadwal')
    
    except Counselor.DoesNotExist:
        messages.error(request, 'Konselor tidak ditemukan.')
        return redirect('kelola-jadwal')
    except Exception as e:
        messages.error(request, f'Gagal menghapus konselor: {str(e)}')
        return redirect('kelola-jadwal')


# 🩺 REKAM MEDIS KONSELING
@login_required(login_url='login')
def rekam_medis_list_view(request, booking_id):
    """List semua rekam medis untuk satu booking/klien"""
    from .models import RekamMedisKonseling
    
    # Get booking
    booking = get_object_or_404(Booking, pk=booking_id)
    
    # Access control: only ADMIN yang bisa akses rekam medis (untuk sekarang)
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, 'Anda tidak memiliki akses ke rekam medis ini.')
        return redirect('lihat-jadwal')
    
    # Get all rekam medis untuk seluruh booking user yang sama (lintas jadwal)
    rekam_medis_list = (
        RekamMedisKonseling.objects
        .filter(konseling__user=booking.user)
        .select_related('konseling')
        .order_by('-konseling__tanggal', '-konseling__waktu', '-sesi_ke')
    )
    
    context = {
        'booking': booking,
        'rekam_medis_list': rekam_medis_list,
        'klien_nama': booking.nama,
    }
    return render(request, 'dashboard/rekam_medis_list.html', context)


@login_required(login_url='login')
def rekam_medis_add_view(request, booking_id):
    """Tambah rekam medis baru untuk satu sesi"""
    from .models import RekamMedisKonseling
    
    booking = get_object_or_404(Booking, pk=booking_id)
    
    # Access control
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, 'Anda tidak memiliki akses untuk menambah rekam medis.')
        return redirect('lihat-jadwal')
    
    if request.method == 'POST':
        try:
            # Hitung sesi_ke berikutnya
            last_sesi = RekamMedisKonseling.objects.filter(konseling=booking).order_by('-sesi_ke').first()
            sesi_ke = (last_sesi.sesi_ke + 1) if last_sesi else 1
            
            rekam_medis = RekamMedisKonseling.objects.create(
                konseling=booking,
                sesi_ke=sesi_ke,
                diagnosis_awal=request.POST.get('diagnosis_awal', ''),
                mood_klien=int(request.POST.get('mood_klien', 5)),
                risiko_bunuh_diri=request.POST.get('risiko_bunuh_diri', 'tidak_ada'),
                risiko_self_harm=request.POST.get('risiko_self_harm', 'tidak_ada'),
                catatan_konselor=request.POST.get('catatan_konselor', ''),
                intervensi_diberikan=request.POST.get('intervensi_diberikan', ''),
                progress_notes=request.POST.get('progress_notes', ''),
                rencana_tindak_lanjut=request.POST.get('rencana_tindak_lanjut', ''),
                sesi_selanjutnya=request.POST.get('sesi_selanjutnya') or None,
                created_by=request.user
            )
            
            # Handle file upload
            if 'file_lampiran' in request.FILES:
                rekam_medis.file_lampiran = request.FILES['file_lampiran']
                rekam_medis.save()
            
            # 📧 High Risk Alert Email ke Management (jika risk tinggi)
            if rekam_medis.risiko_bunuh_diri == 'tinggi' or rekam_medis.risiko_self_harm == 'tinggi':
                management_emails = get_management_emails()
                if management_emails:
                    send_high_risk_alert(rekam_medis, management_emails)
                    logger.warning(f"🚨 HIGH RISK ALERT: Rekam medis ID={rekam_medis.id} untuk booking ID={booking_id} memiliki risiko tinggi. Alert sent to management.")
            
            messages.success(request, f'Rekam medis sesi {sesi_ke} berhasil ditambahkan.')
            return redirect('rekam-medis-list', booking_id=booking_id)
        except Exception as e:
            messages.error(request, f'Gagal menambah rekam medis: {str(e)}')
    
    # GET - show form
    last_sesi = RekamMedisKonseling.objects.filter(konseling=booking).order_by('-sesi_ke').first()
    next_sesi = (last_sesi.sesi_ke + 1) if last_sesi else 1
    
    context = {
        'booking': booking,
        'next_sesi': next_sesi,
        'klien_nama': booking.nama,
        'action': 'add'
    }
    return render(request, 'dashboard/rekam_medis_form.html', context)


@login_required(login_url='login')
def rekam_medis_edit_view(request, rekam_id):
    """Edit rekam medis yang sudah ada"""
    from .models import RekamMedisKonseling
    
    rekam_medis = get_object_or_404(RekamMedisKonseling, pk=rekam_id)
    booking = rekam_medis.konseling
    
    # Access control
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, 'Anda tidak memiliki akses untuk mengedit rekam medis.')
        return redirect('lihat-jadwal')
    
    if request.method == 'POST':
        try:
            rekam_medis.diagnosis_awal = request.POST.get('diagnosis_awal', '')
            rekam_medis.mood_klien = int(request.POST.get('mood_klien', 5))
            rekam_medis.risiko_bunuh_diri = request.POST.get('risiko_bunuh_diri', 'tidak_ada')
            rekam_medis.risiko_self_harm = request.POST.get('risiko_self_harm', 'tidak_ada')
            rekam_medis.catatan_konselor = request.POST.get('catatan_konselor', '')
            rekam_medis.intervensi_diberikan = request.POST.get('intervensi_diberikan', '')
            rekam_medis.progress_notes = request.POST.get('progress_notes', '')
            rekam_medis.rencana_tindak_lanjut = request.POST.get('rencana_tindak_lanjut', '')
            rekam_medis.sesi_selanjutnya = request.POST.get('sesi_selanjutnya') or None
            
            # Handle file upload
            if 'file_lampiran' in request.FILES:
                rekam_medis.file_lampiran = request.FILES['file_lampiran']
            
            rekam_medis.save()
            messages.success(request, f'Rekam medis sesi {rekam_medis.sesi_ke} berhasil diupdate.')
            return redirect('rekam-medis-detail', rekam_id=rekam_id)
        except Exception as e:
            messages.error(request, f'Gagal update rekam medis: {str(e)}')
    
    # GET - show form with existing data
    context = {
        'booking': booking,
        'rekam_medis': rekam_medis,
        'klien_nama': booking.nama,
        'action': 'edit'
    }
    return render(request, 'dashboard/rekam_medis_form.html', context)


@login_required(login_url='login')
def rekam_medis_detail_view(request, rekam_id):
    """Lihat detail satu rekam medis"""
    from .models import RekamMedisKonseling
    
    rekam_medis = get_object_or_404(RekamMedisKonseling, pk=rekam_id)
    booking = rekam_medis.konseling
    
    # Access control
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, 'Anda tidak memiliki akses ke rekam medis ini.')
        return redirect('lihat-jadwal')
    
    context = {
        'rekam_medis': rekam_medis,
        'booking': booking,
        'klien_nama': booking.nama,
    }
    return render(request, 'dashboard/rekam_medis_detail.html', context)


# 🧩 Dashboard Pengguna
@login_required(login_url='login')
def dashboard_user_view(request):
    if request.user.role != CustomUser.Role.USER:
        messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
        return redirect('dashboard_admin' if request.user.role == CustomUser.Role.ADMIN else 'login')
    
    # Tampilkan konten terpopuler (berdasarkan view count dan terbaru)
    konten_list = Konten.objects.filter(is_published=True).order_by('-view_count', '-created_at')[:4]
    
    return render(request, 'users/dashboard_user.html', {
        'nama_user': request.user.nama_lengkap,
        'email_user': request.user.email,
        'active': 'dashboard_user',
        'konten_list': konten_list,
    })


# 🧩 Halaman Home (umum)
@login_required(login_url='login')
def home_view(request):
    # 🎯 Langsung periksa role dan arahkan (redirect) ke dashboard yang benar
    if request.user.role == CustomUser.Role.ADMIN:
        return redirect('dashboard_admin')
    else:
        return redirect('dashboard_user')

@login_required(login_url='login')
def kelola_laporan_view(request):
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
        return redirect('dashboard_user')
    
    # Sort: laporan terbaru di atas, lalu urutkan urgency sebagai pengurutan sekunder
    from django.db.models import Case, When, IntegerField
    urgency_order = Case(
        When(ai_urgency='darurat', then=0),
        When(ai_urgency='tinggi', then=1),
        When(ai_urgency='sedang', then=2),
        When(ai_urgency='rendah', then=3),
        default=4,
        output_field=IntegerField(),
    )
    # Optimasi query dengan select_related dan prefetch_related
    laporan_list = (
        Laporan.objects.select_related('pelapor')
        .prefetch_related('progress', 'evidences')
        .order_by('-created_at', urgency_order)
    )
    
    return render(request, 'dashboard/kelola_laporan.html', {
        'nama_user': request.user.nama_lengkap,
        'email_user': request.user.email,
        'active_page': 'kelola-laporan',  # supaya menu sidebar aktif
        'laporan_list': laporan_list,
    })

@login_required(login_url='login')
def kelola_pengguna_view(request):
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
        return redirect('dashboard_user')
    
    # Ambil pending admins (belum disetujui)
    pending_admins = CustomUser.objects.filter(
        role=CustomUser.Role.ADMIN,
        is_approved=False,
        is_active=False
    ).order_by('-id')
    
    # Ambil semua user aktif untuk ditampilkan di tabel
    active_users = CustomUser.objects.filter(is_active=True).order_by('-id')
    
    logger.debug(f"Kelola Pengguna: Pending admins = {pending_admins.count()}, Active users = {active_users.count()}")
    
    return render(request, 'dashboard/kelola_pengguna.html', {
        'nama_user': request.user.nama_lengkap,
        'email_user': request.user.email,
        'active_page': 'kelola-pengguna',
        'pending_admins': pending_admins,
        'users': active_users,
    })


# 🧩 Approve Admin
@login_required(login_url='login')
def approve_admin_view(request, user_id):
    if request.user.role != CustomUser.Role.ADMIN or not request.user.is_superuser:
        messages.error(request, 'Hanya super admin yang dapat menyetujui admin baru.')
        return redirect('dashboard_admin')
    
    user = get_object_or_404(CustomUser, id=user_id, role=CustomUser.Role.ADMIN)
    
    # Approve admin
    user.is_approved = True
    user.is_active = True
    user.admin_approval_date = timezone.now()
    user.save()
    
    messages.success(request, f'Admin {user.nama_lengkap} ({user.email}) berhasil disetujui!')
    return redirect('kelola-pengguna')


# 🧩 Reject Admin
@login_required(login_url='login')
def reject_admin_view(request, user_id):
    if request.user.role != CustomUser.Role.ADMIN or not request.user.is_superuser:
        messages.error(request, 'Hanya super admin yang dapat menolak admin baru.')
        return redirect('dashboard_admin')
    
    user = get_object_or_404(CustomUser, id=user_id, role=CustomUser.Role.ADMIN)
    
    # Delete akun yang ditolak
    user_name = user.nama_lengkap
    user_email = user.email
    user.delete()
    
    messages.success(request, f'Pendaftaran admin {user_name} ({user_email}) ditolak dan akun dihapus.')
    return redirect('kelola-pengguna')


# 🗑️ Delete User (Admin)
@login_required(login_url='login')
@require_POST
def delete_user_view(request, user_id):
    """Delete user permanently (admin only)"""
    logger = logging.getLogger(__name__)
    
    if request.user.role != CustomUser.Role.ADMIN:
        logger.warning(f"Non-admin user {request.user.email} attempted to delete user {user_id}")
        return JsonResponse({'success': False, 'message': 'Tidak memiliki akses'}, status=403)
    
    try:
        user = get_object_or_404(CustomUser, id=user_id)
        
        # Prevent deleting yourself
        if user.id == request.user.id:
            logger.warning(f"Admin {request.user.email} attempted to delete self")
            return JsonResponse({'success': False, 'message': 'Tidak dapat menghapus akun sendiri'}, status=400)
        
        # Prevent deleting superuser
        if user.is_superuser:
            logger.warning(f"Admin {request.user.email} attempted to delete superuser {user.email}")
            return JsonResponse({'success': False, 'message': 'Tidak dapat menghapus superuser'}, status=400)
        
        user_name = user.nama_lengkap
        user_email = user.email
        user.delete()
        logger.info(f"Admin {request.user.email} successfully deleted user {user_email} (ID: {user_id})")
        
        return JsonResponse({'success': True, 'message': f'User {user_name} berhasil dihapus'})
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Gagal menghapus user: {str(e)}'}, status=500)


# 🧩 Halaman Edit Laporan (VIEW BARU)
@login_required(login_url='login')
def edit_laporan_view(request, report_id):
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
        return redirect('dashboard_user')
    # Coba ambil laporan dengan optimasi query; jika tidak ada, gunakan placeholder untuk GET
    try:
        laporan = Laporan.objects.select_related('pelapor').prefetch_related('progress', 'evidences').get(pk=report_id)
    except Laporan.DoesNotExist:
        laporan = None

    if request.method == 'POST':
        # Ambil data dari form
        new_status = request.POST.get('status')
        catatan = request.POST.get('catatan', '').strip()
        rekomendasi = request.POST.get('rekomendasi', '').strip()

        # Jika laporan belum ada, buat laporan minimal agar status dapat disimpan
        if laporan is None:
            # Buat kode sederhana (unik) berdasarkan waktu
            kode = f"AUTO-{int(timezone.now().timestamp())}"
            laporan = Laporan.objects.create(
                kode=kode,
                pelapor=None,
                jenis='- (dibuat admin sementara)',
                lokasi='-',
                deskripsi='Dibuat otomatis oleh admin saat menyimpan status.',
                link_pelaporan='',
                is_anonim=False,
                status=new_status or 'diterima',
            )

        # Simpan status lama untuk deteksi perubahan
        old_status = laporan.status
        
        # Update laporan
        laporan.status = new_status or laporan.status
        laporan.rekomendasi = rekomendasi
        laporan.save()

        # Buat progress entry agar user bisa melihat riwayat
        progress_entry = Progress.objects.create(
            laporan=laporan,
            status=new_status or laporan.status,
            catatan=catatan,
            oleh=request.user if request.user.is_authenticated else None,
        )

        # 🔔 Notifikasi ke Pelapor - Status Berubah
        if old_status != new_status and laporan.pelapor and not laporan.is_anonim:
            status_labels = {
                'diterima': 'Diterima',
                'sedang_diproses': 'Sedang Diproses',
                'selesai': 'Selesai',
                'ditutup': 'Ditutup',
            }
            status_display = status_labels.get(new_status, new_status)
            
            Notification.objects.create(
                user=laporan.pelapor,
                title=f'📝 Status Laporan {laporan.kode} Diperbarui',
                message=f'Status laporan Anda telah berubah menjadi "{status_display}". {catatan if catatan else ""}',
                type='status_laporan',
                laporan=laporan
            )
            
            # 📧 Email Notification ke Pelapor
            send_laporan_status_updated_notification(
                laporan=laporan,
                old_status=old_status,
                new_status=new_status,
                catatan=catatan
            )
        elif laporan.pelapor and not laporan.is_anonim:
            # Notifikasi progress/catatan baru tanpa perubahan status
            Notification.objects.create(
                user=laporan.pelapor,
                title=f'📌 Pembaruan Laporan {laporan.kode}',
                message=catatan if catatan else 'Admin menambahkan catatan/progress baru.',
                type='progress_laporan',
                laporan=laporan,
            )

        messages.success(request, 'Perubahan status telah disimpan.')
        return redirect('kelola-laporan')

    # Untuk GET, jika laporan tidak ada, pakai placeholder agar template tidak error
    if laporan is None:
        laporan = SimpleNamespace(kode=f"(tidak ditemukan: {report_id})", status='diterima', rekomendasi='')

    return render(request, 'dashboard/edit_laporan.html', {
        'nama_user': request.user.nama_lengkap,
        'email_user': request.user.email,
        'active_page': 'kelola-laporan',
        'laporan': laporan,
        'report_id': report_id, # untuk ditampilkan di template
    })


@login_required(login_url='login')
def admin_laporan_detail_view(request, report_id):
    """Admin-facing detail page that shows the same laporan content as the user page but within admin layout."""
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
        return redirect('dashboard_user')

    try:
        db_laporan = Laporan.objects.select_related('pelapor').prefetch_related('evidences', 'progress').get(pk=report_id)
    except Laporan.DoesNotExist:
        messages.error(request, 'Laporan tidak ditemukan.')
        return redirect('kelola-laporan')

    # build context similar to user view; include filename for display
    bukti_list = []
    for e in db_laporan.evidences.all():
        try:
            name = os.path.basename(e.file.name)
        except Exception:
            name = e.file.name
        bukti_list.append({'url': e.file.url, 'name': name})

    # get latest progress entry (most recent status update)
    latest_progress = db_laporan.progress.order_by('-tanggal').first()
    latest_update = None
    if latest_progress:
        latest_update = {
            'status': latest_progress.status,
            'catatan': latest_progress.catatan,
            'tanggal': latest_progress.tanggal.strftime('%Y-%m-%d %H:%M'),
            'oleh': latest_progress.oleh.nama_lengkap if latest_progress.oleh else 'System',
        }

    # Get pelapor responses (balasan dari pelapor)
    from .models import PelaporResponse
    pelapor_responses = db_laporan.pelapor_responses.all().order_by('tanggal')
    
    # Pisahkan bukti: bukti awal vs bukti tambahan (uploaded_by not null)
    bukti_awal = []
    bukti_tambahan = []
    for e in db_laporan.evidences.all():
        try:
            name = os.path.basename(e.file.name)
        except Exception:
            name = e.file.name
        
        bukti_data = {
            'url': e.file.url, 
            'name': name,
            'uploaded_at': e.uploaded_at.strftime('%Y-%m-%d %H:%M'),
            'keterangan': e.keterangan if e.keterangan else '',
            'uploaded_by': e.uploaded_by.nama_lengkap if e.uploaded_by else 'Pelapor Anonim'
        }
        
        if e.uploaded_by is not None or e.keterangan:  # Bukti tambahan
            bukti_tambahan.append(bukti_data)
        else:  # Bukti awal saat submit
            bukti_awal.append(bukti_data)

    pelapor_name = 'Anonim' if db_laporan.is_anonim else (db_laporan.pelapor.nama_lengkap if db_laporan.pelapor else 'Anonim')
    laporan = SimpleNamespace(
        pk=db_laporan.pk,
        kode=db_laporan.kode,
        tanggal=db_laporan.created_at.strftime('%Y-%m-%d'),
        status=db_laporan.status,
        jenis=db_laporan.jenis,
        lokasi=db_laporan.lokasi,
        deskripsi=db_laporan.deskripsi,
        link_pelaporan=db_laporan.link_pelaporan,
        # Terlapor data
        nama_terlapor=db_laporan.nama_terlapor,
        nim_nip_terlapor=db_laporan.nim_nip_terlapor,
        asal_instansi_terlapor=db_laporan.asal_instansi_terlapor,
        fakultas_terlapor=db_laporan.fakultas_terlapor,
        prodi_terlapor=db_laporan.prodi_terlapor,
        no_wa_terlapor=db_laporan.no_wa_terlapor,
        hubungan_terlapor_korban=db_laporan.hubungan_terlapor_korban,
        ciri_ciri_pelaku=db_laporan.ciri_ciri_pelaku,
        bukti_list=bukti_list,  # Semua bukti (backward compatibility)
        bukti_awal=bukti_awal,  # Bukti saat submit
        bukti_tambahan=bukti_tambahan,  # Bukti upload kemudian
        is_anonim=db_laporan.is_anonim,
        pelapor_name=pelapor_name,
        apakah_korban_langsung=db_laporan.apakah_korban_langsung,
        hubungan_pelapor_korban=db_laporan.hubungan_pelapor_korban,
        # AI Moderation fields
        ai_analyzed=db_laporan.ai_analyzed,
        ai_kategori=db_laporan.ai_kategori,
        ai_urgency=db_laporan.ai_urgency,
        ai_toxicity_score=db_laporan.ai_toxicity_score,
        ai_needs_blur=db_laporan.ai_needs_blur,
    )

    return render(request, 'dashboard/laporan_detail_admin.html', {
        'nama_user': request.user.nama_lengkap,
        'email_user': request.user.email,
        'active_page': 'kelola-laporan',
        'laporan': laporan,
        'latest_update': latest_update,
        'pelapor_responses': pelapor_responses,
    })


@login_required(login_url='login')
def delete_laporan_view(request, report_id):
    """Delete a laporan (admin only). This removes the Laporan and its related Evidence and Progress (cascade)."""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('kelola-laporan')

    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, 'Anda tidak memiliki akses untuk menghapus laporan ini.')
        return redirect('dashboard_user')

    try:
        laporan = Laporan.objects.get(pk=report_id)
    except Laporan.DoesNotExist:
        messages.error(request, 'Laporan tidak ditemukan.')
        return redirect('kelola-laporan')

    # delete cascades to Evidence and Progress due to on_delete=models.CASCADE
    laporan.delete()
    messages.success(request, 'Laporan berhasil dihapus.')
    return redirect('kelola-laporan')


# 🧩 Halaman Kelola Konten (VIEW BARU)
@login_required(login_url='login')
def kelola_konten_view(request):
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
        return redirect('dashboard_user')

    # Handle form submission untuk tambah konten
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_konten':
            judul = request.POST.get('judul')
            kategori = request.POST.get('kategori')
            deskripsi = request.POST.get('deskripsi')
            konten = request.POST.get('konten')
            penulis = request.POST.get('penulis', 'Tim Ruang Dengar')
            scheduled_date = request.POST.get('scheduled_date')
            gambar = request.FILES.get('gambar')
            media_url = request.POST.get('media_url')
            tags = request.POST.get('tags', '')
            
            # Validasi
            if judul and kategori and deskripsi and konten:
                new_konten = Konten.objects.create(
                    judul=judul,
                    kategori=kategori,
                    deskripsi=deskripsi,
                    konten=konten,
                    penulis=penulis,
                    media_url=media_url if media_url else None,
                    tags=tags,
                    is_published=True if not scheduled_date else False,  # Draft jika dijadwalkan
                    scheduled_date=scheduled_date if scheduled_date else None
                )
                
                # Upload gambar jika ada
                if gambar:
                    new_konten.gambar = gambar
                    new_konten.save()
                
                if scheduled_date:
                    messages.success(request, f'Konten "{judul}" berhasil dijadwalkan untuk {scheduled_date}!')
                else:
                    messages.success(request, f'Konten "{judul}" berhasil dipublikasikan!')
            else:
                messages.error(request, 'Semua field harus diisi!')
            
            return redirect('kelola-konten')
    
    # Ambil semua konten
    konten_list = Konten.objects.all().order_by('-created_at')
    
    return render(request, 'dashboard/kelola_konten.html', {
        'nama_user': request.user.nama_lengkap,
        'email_user': request.user.email,
        'active_page': 'kelola-konten',
        'konten_list': konten_list,
    })

@login_required(login_url='login')
def edit_konten_view(request, konten_id):
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
        return redirect('dashboard_user')
    
    konten = get_object_or_404(Konten, id=konten_id)
    
    if request.method == 'POST':
        konten.judul = request.POST.get('judul')
        konten.kategori = request.POST.get('kategori')
        konten.deskripsi = request.POST.get('deskripsi')
        konten.konten = request.POST.get('konten')
        konten.penulis = request.POST.get('penulis')
        konten.tags = request.POST.get('tags', '')
        scheduled_date = request.POST.get('scheduled_date')
        konten.scheduled_date = scheduled_date if scheduled_date else None
        
        # Update media_url
        media_url = request.POST.get('media_url')
        konten.media_url = media_url if media_url else None
        
        # Update gambar jika ada file baru
        if request.FILES.get('gambar'):
            konten.gambar = request.FILES['gambar']
        
        konten.save()
        
        messages.success(request, f'Konten "{konten.judul}" berhasil diupdate!')
        return redirect('kelola-konten')
    
    return redirect('kelola-konten')

@login_required(login_url='login')
def delete_konten_view(request, konten_id):
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
        return redirect('dashboard_user')
    
    konten = get_object_or_404(Konten, id=konten_id)
    judul = konten.judul
    konten.delete()
    
    messages.success(request, f'Konten "{judul}" berhasil dihapus!')
    return redirect('kelola-konten')

@login_required(login_url='login')
def toggle_konten_view(request, konten_id):
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
        return redirect('dashboard_user')
    
    konten = get_object_or_404(Konten, id=konten_id)
    konten.is_published = not konten.is_published
    konten.save()
    
    status = "dipublikasi" if konten.is_published else "disembunyikan"
    messages.success(request, f'Konten "{konten.judul}" berhasil {status}!')
    return redirect('kelola-konten')

# API endpoint untuk fetch konten (JSON)
@login_required(login_url='login')
def get_konten_api(request, konten_id):
    # Removed admin check - allow all authenticated users to view content
    try:
        konten = Konten.objects.get(id=konten_id)
        data = {
            'id': konten.id,
            'judul': konten.judul,
            'kategori': konten.kategori,
            'deskripsi': konten.deskripsi,
            'konten': konten.konten,
            'penulis': konten.penulis,
            'tags': konten.tags,
            'gambar': konten.gambar.url if konten.gambar else '',
            'media_url': konten.media_url or '',
            'is_published': konten.is_published,
            'scheduled_date': konten.scheduled_date.isoformat() if konten.scheduled_date else None,
        }
        return JsonResponse(data)
    except Konten.DoesNotExist:
        return JsonResponse({'error': 'Konten not found'}, status=404)

# Detail Artikel STATIS (VIEW BARU)
@login_required(login_url='login')
def artikel_detail_view(request, id):
    logger.debug(f"artikel_detail: user={request.user.email}, role={request.user.role}, is_user={request.user.role == CustomUser.Role.USER}")
    if request.user.role != CustomUser.Role.USER:
        messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
        return redirect('dashboard_admin' if request.user.role == CustomUser.Role.ADMIN else 'login')
    
    # Ambil konten dari database
    try:
        konten = Konten.objects.get(id=id, is_published=True)
        
        # Increment view count
        konten.view_count += 1
        konten.save(update_fields=['view_count'])
        
        return render(request, 'menu_users/artikel_detail.html', {
            'artikel': konten,
            'nama_user': request.user.nama_lengkap,
            'email_user': request.user.email,
            'active': 'dashboard_user',
        })
    except Konten.DoesNotExist:
        messages.error(request, 'Artikel tidak ditemukan atau belum dipublikasikan.')
        return redirect('dashboard_user')

@login_required(login_url='login')
def buat_laporan_view(request):
    logger.debug(f"buat_laporan: user={request.user.email}, role={request.user.role}, is_user={request.user.role == CustomUser.Role.USER}")
    if request.user.role != CustomUser.Role.USER:
        messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
        return redirect('dashboard_admin' if request.user.role == CustomUser.Role.ADMIN else 'login')

    # Jika form ditekan submit (POST)
    if request.method == "POST":
        # Field lama
        jenis = request.POST.get('jenis')
        tempat = request.POST.get('lokasi')
        deskripsi = request.POST.get('deskripsi', '').strip()
        kronologi_singkat = request.POST.get('kronologi_singkat', '').strip()
        link_pelaporan = request.POST.get('link_pelaporan', '').strip()
        is_anonim = True if request.POST.get('is_anonim') == 'true' or request.POST.get('is_anonim') == 'on' else False

        # Field pelapor & korban context
        apakah_korban_langsung_str = request.POST.get('apakah_korban_langsung', 'true')
        apakah_korban_langsung = True if apakah_korban_langsung_str == 'true' else False
        hubungan_pelapor_korban = request.POST.get('hubungan_pelapor_korban', '')

        # Field data korban (jika pelapor bukan korban langsung)
        nama_korban = request.POST.get('nama_korban', '')
        nim_nip_korban = request.POST.get('nim_nip_korban', '')
        status_korban = request.POST.get('status_korban', '')
        fakultas_korban = request.POST.get('fakultas_korban', '')
        prodi_korban = request.POST.get('prodi_korban', '')
        jenis_kelamin_korban = request.POST.get('jenis_kelamin_korban', '')

        # Field data terlapor (nama wajib, lainnya opsional)
        jumlah_terlapor = request.POST.get('jumlah_terlapor', '')
        nama_terlapor = request.POST.get('nama_terlapor', '')
        nim_nip_terlapor = request.POST.get('nim_nip_terlapor', '')
        asal_instansi_terlapor = request.POST.get('asal_instansi_terlapor', 'Telkom University')
        fakultas_terlapor = request.POST.get('fakultas_terlapor', '')
        prodi_terlapor = request.POST.get('prodi_terlapor', '')
        no_wa_terlapor = request.POST.get('no_wa_terlapor', '')
        hubungan_terlapor_korban = request.POST.get('hubungan_terlapor_korban', '')
        ciri_ciri_pelaku = request.POST.get('ciri_ciri_pelaku', '')

        # Ambil files
        files = request.FILES.getlist('bukti')

        # Validasi: field wajib terisi
        if not jenis or not tempat or not deskripsi or not ciri_ciri_pelaku:
            messages.error(request, 'Mohon lengkapi semua field yang wajib diisi (*).')
            return render(request, 'menu_users/buat_laporan.html', {
                'nama_user': request.user.nama_lengkap,
                'email_user': request.user.email,
                'active': 'buat-laporan',
            })
        
        # Validasi: minimal 1 evidence (file atau link)
        if not files and not link_pelaporan:
            messages.error(request, 'Minimal upload 1 bukti (foto/dokumen) atau isi link pelaporan.')
            return render(request, 'menu_users/buat_laporan.html', {
                'nama_user': request.user.nama_lengkap,
                'email_user': request.user.email,
                'active': 'buat-laporan',
            })

        # Validasi: data terlapor minimal nama terlapor
        if not nama_terlapor:
            messages.error(request, 'Nama terlapor wajib diisi.')
            return render(request, 'menu_users/buat_laporan.html', {
                'nama_user': request.user.nama_lengkap,
                'email_user': request.user.email,
                'active': 'buat-laporan',
            })

        # Buat Laporan dengan semua field baru
        laporan = Laporan.objects.create(
            kode='',
            pelapor=None if is_anonim else request.user,  # NULL jika anonim, admin tidak bisa lihat
            jenis=jenis,
            lokasi=tempat,
            deskripsi=deskripsi,
            kronologi_singkat=kronologi_singkat,
            link_pelaporan=link_pelaporan,
            is_anonim=is_anonim,
            status='diterima',
            # Pelapor & korban context
            apakah_korban_langsung=apakah_korban_langsung,
            hubungan_pelapor_korban=hubungan_pelapor_korban,
            # Data korban
            nama_korban=nama_korban,
            nim_nip_korban=nim_nip_korban,
            status_korban=status_korban,
            fakultas_korban=fakultas_korban,
            prodi_korban=prodi_korban,
            jenis_kelamin_korban=jenis_kelamin_korban,
            # Data terlapor
            jumlah_terlapor=jumlah_terlapor,
            nama_terlapor=nama_terlapor,
            nim_nip_terlapor=nim_nip_terlapor,
            asal_instansi_terlapor=asal_instansi_terlapor,
            fakultas_terlapor=fakultas_terlapor,
            prodi_terlapor=prodi_terlapor,
            no_wa_terlapor=no_wa_terlapor,
            hubungan_terlapor_korban=hubungan_terlapor_korban,
            ciri_ciri_pelaku=ciri_ciri_pelaku,
        )

        # Perbaiki kode agar unik berbentuk RPT-YYYYMMDD-0001
        laporan.kode = f"RPT-{timezone.now().strftime('%Y%m%d')}-{laporan.pk:04d}"
        
        # 🤖 AI Content Moderation
        try:
            ai_result = moderate_laporan(deskripsi, jenis)
            laporan.ai_kategori = ai_result.get('kategori')
            laporan.ai_urgency = ai_result.get('urgency')
            laporan.ai_toxicity_score = ai_result.get('toxicity_score', 0.0)
            laporan.ai_needs_blur = ai_result.get('needs_blur', False)
            laporan.ai_analyzed = ai_result.get('analyzed', False)
            
            logger.info(f"AI Moderation for {laporan.kode}: kategori={laporan.ai_kategori}, urgency={laporan.ai_urgency}")
            
            # Jika darurat, log untuk notifikasi admin
            if laporan.ai_urgency == 'darurat':
                logger.warning(f"⚠️ DARURAT: Laporan {laporan.kode} membutuhkan perhatian segera!")
        except Exception as e:
            logger.error(f"AI Moderation failed for laporan: {e}")
            # Tetap lanjutkan tanpa AI jika error
        
        laporan.save()

        # Simpan Evidence
        for f in files:
            Evidence.objects.create(laporan=laporan, file=f)

        # Buat progress awal
        Progress.objects.create(
            laporan=laporan,
            status='diterima',
            catatan='Laporan dibuat oleh pelapor.' if not is_anonim else 'Laporan anonim diterima.',
            oleh=None if is_anonim else request.user,
        )

        # 🔔 Notifikasi ke Admin - Laporan Baru
        admin_users = CustomUser.objects.filter(role=CustomUser.Role.ADMIN)
        pelapor_name = 'Anonim' if is_anonim else request.user.nama_lengkap
        
        for admin in admin_users:
            Notification.objects.create(
                user=admin,
                title='📋 Laporan Baru Masuk',
                message=f'Laporan baru dari {pelapor_name} dengan kode {laporan.kode}. Jenis: {laporan.jenis}.',
                type='laporan_baru',
                laporan=laporan
            )
        
        # � Email Notification ke Admin
        admin_emails = get_admin_emails()
        if admin_emails:
            send_laporan_created_notification(laporan, admin_emails)
        
        # 🔔 Notifikasi Darurat ke Admin (jika urgency tinggi)
        if laporan.ai_urgency == 'darurat':
            for admin in admin_users:
                Notification.objects.create(
                    user=admin,
                    title='🚨 DARURAT - Laporan Perlu Perhatian Segera',
                    message=f'Laporan {laporan.kode} memiliki tingkat urgensi DARURAT. Kategori: {laporan.ai_kategori}. Mohon segera ditindaklanjuti!',
                    type='laporan_darurat',
                    laporan=laporan
                )
            # 📧 Email Alert Urgent ke Management
            management_emails = get_management_emails()
            if management_emails:
                send_urgent_laporan_alert(laporan, management_emails)

        # Success message dan redirect
        if is_anonim:
            # Simpan ID laporan anonim ke session untuk tracking
            if 'anonim_laporans' not in request.session:
                request.session['anonim_laporans'] = []
            request.session['anonim_laporans'].append(laporan.pk)
            request.session.modified = True
            
            messages.success(request, f"Laporan anonim berhasil dikirim dengan kode {laporan.kode}.")
            return redirect(f"{reverse_lazy('status-laporan')}?id={laporan.pk}")
        else:
            messages.success(request, "Laporan Anda berhasil dikirim!")
            return redirect(f"{reverse_lazy('status-laporan')}?id={laporan.pk}")

    return render(request, 'menu_users/buat_laporan.html', {
        'nama_user': request.user.nama_lengkap,
        'email_user': request.user.email,
        'active': 'buat-laporan',
    })

@login_required(login_url='login')
def riwayat_laporan_view(request):
    logger.debug(f"riwayat_laporan: user={request.user.email}, role={request.user.role}, is_user={request.user.role == CustomUser.Role.USER}")
    if request.user.role != CustomUser.Role.USER:
        messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
        return redirect('dashboard_admin' if request.user.role == CustomUser.Role.ADMIN else 'login')
    
    # Ambil laporan milik user yang sedang login (non-anonim) - Optimasi query
    laporan_list = list(Laporan.objects.filter(pelapor=request.user).select_related('pelapor').prefetch_related('progress', 'evidences').order_by('-created_at'))
    
    # Ambil laporan anonim dari session
    anonim_ids = request.session.get('anonim_laporans', [])
    if anonim_ids:
        anonim_laporans = Laporan.objects.filter(pk__in=anonim_ids).prefetch_related('progress', 'evidences').order_by('-created_at')
        laporan_list.extend(anonim_laporans)
    
    # Sort gabungan berdasarkan created_at
    laporan_list.sort(key=lambda x: x.created_at, reverse=True)
    
    return render(request, 'menu_users/riwayat_laporan.html', {
        'nama_user': request.user.nama_lengkap,
        'email_user': request.user.email,
        'active': 'riwayat-laporan',
        'laporan_list': laporan_list,
    })

@login_required(login_url='login')
def detail_laporan_view(request, report_id):
    if request.user.role != CustomUser.Role.USER:
        messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
        return redirect('dashboard_admin' if request.user.role == CustomUser.Role.ADMIN else 'login')
    
    # Coba ambil laporan dari DB dengan optimasi query; jika tidak ditemukan, tampilkan halaman not-found
    try:
        db_laporan = Laporan.objects.select_related('pelapor').prefetch_related('evidences', 'progress').get(pk=report_id)
    except Laporan.DoesNotExist:
        return render(request, "menu_users/laporan_not_found.html", {
            'nama_user': request.user.nama_lengkap,
            'email_user': request.user.email,
            'active': 'riwayat-laporan',
        })

    # Siapkan konteks yang diharapkan template
    bukti_url = ''
    evidences = list(db_laporan.evidences.all()) if hasattr(db_laporan, 'evidences') else []
    if evidences:
        # ambil file pertama untuk template lama yang menampilkan satu bukti
        bukti_url = evidences[0].file.url

    laporan = {
        'kode': db_laporan.kode,
        'tanggal': db_laporan.created_at.strftime('%Y-%m-%d'),
        'status': db_laporan.status,
        'jenis': db_laporan.jenis,
        'lokasi': db_laporan.lokasi,
        'deskripsi': db_laporan.deskripsi,
        'link_pelaporan': db_laporan.link_pelaporan,
        'bukti': bukti_url,
        # Pelapor context
        'apakah_korban_langsung': getattr(db_laporan, 'apakah_korban_langsung', False),
        'hubungan_pelapor_korban': getattr(db_laporan, 'hubungan_pelapor_korban', ''),
        # Terlapor fields
        'nama_terlapor': getattr(db_laporan, 'nama_terlapor', ''),
        'nim_nip_terlapor': getattr(db_laporan, 'nim_nip_terlapor', ''),
        'asal_instansi_terlapor': getattr(db_laporan, 'asal_instansi_terlapor', ''),
        'ciri_ciri_pelaku': getattr(db_laporan, 'ciri_ciri_pelaku', ''),
    }

    return render(request, "menu_users/laporan_detail.html", {
        'nama_user': request.user.nama_lengkap,
        'email_user': request.user.email,
        'active': 'riwayat-laporan',
        'laporan': laporan,
    })

@login_required(login_url='login')
def booking_konseling_view(request):
    # Only allow USER role to access this view
    logger.debug(f"booking_konseling: user={request.user.email}, role={request.user.role}, is_user={request.user.role == CustomUser.Role.USER}")
    if request.user.role != CustomUser.Role.USER:
        messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
        return redirect('dashboard_admin' if request.user.role == CustomUser.Role.ADMIN else 'login')
    
    # Handle booking form submission
    if request.method == 'POST':
        tanggal = request.POST.get('tanggal')
        waktu = request.POST.get('waktu')
        konselor_input = request.POST.get('konselor')
        konselor = None
        nama = request.POST.get('nama') or request.user.nama_lengkap
        topik = request.POST.get('topik', '')
        jenis = request.POST.get('jenis', '')

        # Basic validation and parsing
        try:
            tanggal_obj = datetime.strptime(tanggal, '%Y-%m-%d').date()
            waktu_obj = datetime.strptime(waktu, '%H:%M').time()
        except Exception:
            messages.error(request, 'Format tanggal atau waktu tidak valid.')
            return redirect('booking-konseling')

        # Validate required fields
        if not all([tanggal, waktu, konselor_input, jenis]):
            errors = []
            if not tanggal: errors.append('Tanggal')
            if not waktu: errors.append('Waktu')
            if not konselor_input: errors.append('Konselor')
            if not jenis: errors.append('Jenis Konseling')
            messages.error(request, f'❌ Field wajib belum diisi: {", ".join(errors)}')
            logger.debug(f"Booking validation failed: tanggal={tanggal}, waktu={waktu}, konselor={konselor_input}, jenis={jenis}")
            return redirect('booking-konseling')
        
        try:
            # Get counselor object
            counselor = Counselor.objects.get(pk=konselor_input)
            
            # Check for conflicts
            conflict = Booking.objects.filter(
                tanggal=tanggal_obj,
                waktu=waktu_obj,
                konselor_fk=counselor,
                status='terjadwal'
            ).exists()
            
            if conflict:
                messages.error(request, f'❌ Jadwal bentrok! Konselor {counselor.name} sudah memiliki jadwal pada {tanggal} pukul {waktu}. Silakan pilih waktu lain.')
                return redirect('booking-konseling')
            
            # Create booking (sama seperti admin)
            booking = Booking.objects.create(
                user=request.user,
                tanggal=tanggal_obj,
                waktu=waktu_obj,
                konselor=counselor.name,
                konselor_fk=counselor,
                nama=request.user.nama_lengkap,
                topik=topik,
                jenis=jenis,
                status='terjadwal'
            )
            
            # 🔔 Notifikasi ke Admin - Booking Baru
            admin_users = CustomUser.objects.filter(role=CustomUser.Role.ADMIN)
            for admin in admin_users:
                Notification.objects.create(
                    user=admin,
                    title='📅 Booking Konseling Baru',
                    message=f'Booking baru dari {request.user.nama_lengkap}. Jenis: {jenis}, Konselor: {counselor.name}, Tanggal: {tanggal_obj.strftime("%d/%m/%Y")} pukul {waktu_obj.strftime("%H:%M")}.',
                    type='booking_baru',
                    booking=booking
                )
            
            # 📧 Email Notification ke Counselor & Pelapor
            send_booking_created_notification(booking)
            
            logger.debug(f"User Booking created: ID={booking.id}, user_id={booking.user.id}, nama={booking.nama}")
            messages.success(request, 'Booking berhasil dibuat.')
            return redirect('booking-konseling')
            
        except Counselor.DoesNotExist:
            messages.error(request, 'Konselor tidak ditemukan.')
            return redirect('booking-konseling')
        except Exception as e:
            messages.error(request, f'Gagal membuat booking: {str(e)}')
            return redirect('booking-konseling')

    # GET: show booking form and current user's bookings
    bookings = Booking.objects.filter(user=request.user).order_by('-tanggal', '-waktu')
    logger.debug(f"User View: user={request.user.id}, bookings count={bookings.count()}")
    for b in bookings:
        logger.debug(f"Booking ID={b.id}, tanggal={b.tanggal}, user_id={b.user.id}, nama={b.nama}")
    counselors = Counselor.objects.all()
    return render(request, 'menu_users/booking_konseling.html', {
        'nama_user': request.user.nama_lengkap,
        'email_user': request.user.email,
        'active': 'booking-konseling',
        'bookings': bookings,
        'counselors': counselors,
    })

@login_required(login_url='login')
def status_laporan_view(request):
    if request.user.role != CustomUser.Role.USER:
        messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
        return redirect('dashboard_admin' if request.user.role == CustomUser.Role.ADMIN else 'login')
    
    # Handle POST: Upload bukti tambahan atau kirim balasan
    if request.method == 'POST':
        report_id = request.POST.get('laporan_id')
        action = request.POST.get('action')
        
        if not report_id:
            messages.error(request, 'ID Laporan tidak valid.')
            return redirect('riwayat_laporan')
        
        try:
            laporan_obj = Laporan.objects.get(pk=report_id)
            
            # Validasi akses
            anonim_ids = request.session.get('anonim_laporans', [])
            if laporan_obj.pelapor != request.user and laporan_obj.pk not in anonim_ids:
                messages.error(request, 'Anda tidak memiliki akses ke laporan ini.')
                return redirect('riwayat_laporan')
            
            if action == 'upload_bukti':
                # Upload bukti tambahan
                files = request.FILES.getlist('bukti_tambahan')
                keterangan = request.POST.get('keterangan', '')
                
                if not files:
                    messages.error(request, 'Mohon pilih file yang akan diupload.')
                else:
                    for f in files:
                        Evidence.objects.create(
                            laporan=laporan_obj, 
                            file=f,
                            uploaded_by=None if laporan_obj.is_anonim else request.user,
                            keterangan=keterangan
                        )
                    # 🔔 Notifikasi ke Admin - Bukti tambahan dari pelapor
                    admin_users = CustomUser.objects.filter(role=CustomUser.Role.ADMIN)
                    uploader = 'Pelapor Anonim' if laporan_obj.is_anonim else request.user.nama_lengkap
                    for admin in admin_users:
                        Notification.objects.create(
                            user=admin,
                            title='📎 Bukti Tambahan Diupload',
                            message=f'{len(files)} bukti baru diunggah oleh {uploader} untuk laporan {laporan_obj.kode}.',
                            type='bukti_baru',
                            laporan=laporan_obj
                        )
                    messages.success(request, f'{len(files)} bukti tambahan berhasil diupload!')
                
            elif action == 'kirim_balasan':
                # Kirim balasan ke admin
                pesan = request.POST.get('pesan', '').strip()
                
                if not pesan:
                    messages.error(request, 'Pesan tidak boleh kosong.')
                else:
                    from .models import PelaporResponse
                    PelaporResponse.objects.create(
                        laporan=laporan_obj,
                        pesan=pesan
                    )
                    # 🔔 Notifikasi ke Admin - Balasan pelapor
                    admin_users = CustomUser.objects.filter(role=CustomUser.Role.ADMIN)
                    pengirim = 'Pelapor Anonim' if laporan_obj.is_anonim else request.user.nama_lengkap
                    for admin in admin_users:
                        Notification.objects.create(
                            user=admin,
                            title='💬 Balasan Baru dari Pelapor',
                            message=f'{pengirim} mengirim balasan untuk laporan {laporan_obj.kode}: {pesan[:120]}',
                            type='balasan_pelapor',
                            laporan=laporan_obj
                        )
                    messages.success(request, 'Balasan Anda berhasil dikirim ke admin!')
            
            return redirect(f"{reverse_lazy('status-laporan')}?id={report_id}")
            
        except Laporan.DoesNotExist:
            messages.error(request, 'Laporan tidak ditemukan.')
            return redirect('riwayat_laporan')
    
    # If an id query param is provided, try to load sample data for that report.
    report_id = request.GET.get('id')
    laporan = {}
    riwayat = []
    # sample static data (mirror of detail_laporan_view sample)
    sample_data = {
        '1': {
            'kode': '#RPT-20231120-001',
            'tanggal_dibuat': '2023-11-20',
            'status': 'verifikasi_awal',
            'jenis': 'Kekerasan',
            'lokasi': 'Ruang Kelas B-203',
            'deskripsi': 'Terjadi tindakan kekerasan fisik antar siswa di dalam kelas pada saat jam istirahat.',
            'bukti': 'images/bukti1.jpg',
            'is_anonim': False,
        },
        '2': {
            'kode': '#RPT-20231118-002',
            'tanggal_dibuat': '2023-11-18',
            'status': 'diterima',
            'jenis': 'Pelecehan',
            'lokasi': 'Koridor Gedung A',
            'deskripsi': 'Contoh deskripsi 2.',
            'bukti': '',
            'is_anonim': True,
        }
    }

    # Prefer real DB data if available
    if report_id:
        try:
            db_laporan = Laporan.objects.select_related('pelapor').prefetch_related('evidences', 'progress').get(pk=report_id)
            
            # Validasi akses: hanya owner (non-anonim) atau yang punya di session (anonim) bisa akses
            anonim_ids = request.session.get('anonim_laporans', [])
            if db_laporan.pelapor != request.user and db_laporan.pk not in anonim_ids:
                messages.error(request, 'Anda tidak memiliki akses ke laporan ini.')
                return redirect('riwayat_laporan')
            
            laporan = {
                'id': db_laporan.id,
                'kode': db_laporan.kode,
                'tanggal_dibuat': db_laporan.created_at.strftime('%Y-%m-%d'),
                'status': db_laporan.status,
                'tahap_resmi': db_laporan.get_tahap_resmi(),
                'tahap_label': db_laporan.get_tahap_label(),
                'jenis': db_laporan.jenis,
                'lokasi': db_laporan.lokasi,
                'deskripsi': db_laporan.deskripsi,
                'link_pelaporan': db_laporan.link_pelaporan,
                'bukti': [e.file.url for e in db_laporan.evidences.all()],
                'is_anonim': db_laporan.is_anonim,
                # Tanggal-tanggal untuk setiap sub-status (jika ada)
                'tanggal_verifikasi': None,
                'tanggal_wawancara_pelapor': None,
                'tanggal_pengumpulan_bukti': None,
                'tanggal_wawancara_terlapor': None,
                'tanggal_analisis': None,
                'tanggal_rapat_pemutusan': None,
                'tanggal_rekomendasi': None,
                'tanggal_pelaksanaan': None,
                'tanggal_selesai': None,
                # Catatan untuk setiap sub-status (jika ada)
                'catatan_verifikasi': None,
                'catatan_wawancara_pelapor': None,
                'catatan_pengumpulan': None,
                'catatan_wawancara_terlapor': None,
                'catatan_analisis': None,
                'catatan_rapat_pemutusan': None,
                'catatan_rekomendasi': None,
                'catatan_pelaksanaan': None,
                'catatan_penutupan': None,
            }
            # Build riwayat dari Progress
            riwayat = []
            for p in db_laporan.progress.order_by('tanggal').all():
                riwayat.append({'judul': p.status, 'deskripsi': p.catatan, 'tanggal': p.tanggal.strftime('%Y-%m-%d %H:%M')})
                
                # Map progress ke field tanggal & catatan yang sesuai
                if 'verifikasi' in p.status.lower():
                    laporan['tanggal_verifikasi'] = p.tanggal.strftime('%Y-%m-%d %H:%M')
                    laporan['catatan_verifikasi'] = p.catatan
                elif 'wawancara pelapor' in p.status.lower():
                    laporan['tanggal_wawancara_pelapor'] = p.tanggal.strftime('%Y-%m-%d %H:%M')
                    laporan['catatan_wawancara_pelapor'] = p.catatan
                elif 'bukti' in p.status.lower() or 'pengumpulan' in p.status.lower():
                    laporan['tanggal_pengumpulan_bukti'] = p.tanggal.strftime('%Y-%m-%d %H:%M')
                    laporan['catatan_pengumpulan'] = p.catatan
                elif 'wawancara terlapor' in p.status.lower():
                    laporan['tanggal_wawancara_terlapor'] = p.tanggal.strftime('%Y-%m-%d %H:%M')
                    laporan['catatan_wawancara_terlapor'] = p.catatan
                elif 'analisis' in p.status.lower() or 'kronologi' in p.status.lower():
                    laporan['tanggal_analisis'] = p.tanggal.strftime('%Y-%m-%d %H:%M')
                    laporan['catatan_analisis'] = p.catatan
                elif 'rapat' in p.status.lower():
                    laporan['tanggal_rapat_pemutusan'] = p.tanggal.strftime('%Y-%m-%d %H:%M')
                    laporan['catatan_rapat_pemutusan'] = p.catatan
                elif 'rekomendasi' in p.status.lower():
                    laporan['tanggal_rekomendasi'] = p.tanggal.strftime('%Y-%m-%d %H:%M')
                    laporan['catatan_rekomendasi'] = p.catatan
                elif 'pelaksanaan' in p.status.lower():
                    laporan['tanggal_pelaksanaan'] = p.tanggal.strftime('%Y-%m-%d %H:%M')
                    laporan['catatan_pelaksanaan'] = p.catatan
                elif 'ditutup' in p.status.lower() or 'selesai' in p.status.lower():
                    laporan['tanggal_selesai'] = p.tanggal.strftime('%Y-%m-%d %H:%M')
                    laporan['catatan_penutupan'] = p.catatan
        except Laporan.DoesNotExist:
            # Fallback to sample data
            if report_id in sample_data:
                laporan = sample_data[report_id]
                laporan['tahap_resmi'] = Laporan.TAHAP_MAPPING.get(laporan.get('status', 'diterima'), 1)
                laporan['tahap_label'] = Laporan.TAHAP_LABELS.get(laporan['tahap_resmi'], 'Pelaporan')
                riwayat = [
                    {'judul': 'Laporan Diterima', 'deskripsi': 'Laporan tercatat di sistem', 'tanggal': laporan.get('tanggal_dibuat')},
                ]
    else:
        # no report_id: keep empty/defaults
        pass

    # Ambil balasan pelapor jika ada
    pelapor_responses = []
    if report_id and 'id' in laporan:
        from .models import PelaporResponse
        try:
            laporan_obj = Laporan.objects.get(pk=report_id)
            pelapor_responses = laporan_obj.pelapor_responses.all().order_by('tanggal')
        except:
            pass

    return render(request, 'menu_users/status_laporan.html', {
        'nama_user': request.user.nama_lengkap,
        'email_user': request.user.email,
        'active': 'riwayat-laporan',
        'laporan': laporan,
        'riwayat': riwayat,
        'pelapor_responses': pelapor_responses,
    })

@login_required(login_url='login')
def laporan_terkirim_view(request):
    if request.user.role != CustomUser.Role.USER:
        messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
        return redirect('dashboard_admin' if request.user.role == CustomUser.Role.ADMIN else 'login')
    
    return render(request, 'menu_users/laporan_terkirim.html', {
        'nama_user': request.user.nama_lengkap,
        'email_user': request.user.email,
        'active': 'buat-laporan',
    })


@login_required(login_url='login')
def edit_profile_view(request):
    """Edit profile for both admin and user"""
    from .forms import EditProfileForm, ChangePasswordForm
    
    profile_form = EditProfileForm(instance=request.user)
    password_form = ChangePasswordForm(user=request.user)
    
    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = EditProfileForm(request.POST, request.FILES, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                request.user.refresh_from_db()
                messages.success(request, 'Profile berhasil diperbarui!')
                return redirect('edit-profile')
            else:
                logger.warning('Edit profile errors for %s: %s', request.user.email, profile_form.errors)
                messages.error(request, 'Profil gagal diperbarui. Mohon periksa kembali input Anda.')
        
        elif 'change_password' in request.POST:
            password_form = ChangePasswordForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                new_password = password_form.cleaned_data['new_password1']
                request.user.set_password(new_password)
                request.user.save(update_fields=['password'])
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Password berhasil diubah!')
                return redirect('edit-profile')
            else:
                messages.error(request, 'Gagal mengubah password. Mohon periksa kembali input Anda.')
    
    # Determine template based on role
    if request.user.role == CustomUser.Role.ADMIN:
        template = 'dashboard/edit_profile.html'
        context = {
            'nama_user': request.user.nama_lengkap,
            'email_user': request.user.email,
            'active_page': 'edit-profile',
            'profile_form': profile_form,
            'password_form': password_form,
        }
    else:
        template = 'menu_users/edit_profile.html'
        context = {
            'nama_user': request.user.nama_lengkap,
            'email_user': request.user.email,
            'active': 'edit-profile',
            'profile_form': profile_form,
            'password_form': password_form,
        }
    
    return render(request, template, context)


# 🔔 ========== NOTIFICATION SYSTEM ==========

@login_required(login_url='login')
def notification_list_view(request):
    """Display all notifications for the logged-in user"""
    notifications = request.user.notifications.all().order_by('-created_at')
    unread_count = notifications.filter(is_read=False).count()
    
    # Determine template based on role
    if request.user.role == CustomUser.Role.ADMIN:
        template = 'dashboard/notifikasi.html'
        context = {
            'nama_user': request.user.nama_lengkap,
            'email_user': request.user.email,
            'active_page': 'notifikasi',
            'notifications': notifications,
            'unread_count': unread_count,
        }
    else:
        template = 'menu_users/notifikasi.html'
        context = {
            'nama_user': request.user.nama_lengkap,
            'email_user': request.user.email,
            'active': 'notifikasi',
            'notifications': notifications,
            'unread_count': unread_count,
        }
    
    return render(request, template, context)


@login_required(login_url='login')
def mark_notification_read_view(request, notification_id):
    """Mark a single notification as read"""
    if request.method == 'POST':
        try:
            notification = Notification.objects.get(pk=notification_id, user=request.user)
            notification.is_read = True
            notification.save()
            messages.success(request, 'Notifikasi ditandai sebagai sudah dibaca.')
        except Notification.DoesNotExist:
            messages.error(request, 'Notifikasi tidak ditemukan.')
    
    return redirect('notifikasi')


@login_required(login_url='login')
def mark_all_notifications_read_view(request):
    """Mark all user notifications as read"""
    if request.method == 'POST':
        updated = request.user.notifications.filter(is_read=False).update(is_read=True)
        messages.success(request, f'{updated} notifikasi ditandai sebagai sudah dibaca.')
    
    return redirect('notifikasi')


def kebijakan_privasi_view(request):
    """Halaman kebijakan privasi dan kerahasiaan"""
    if request.user.is_authenticated:
        context = {
            'nama_user': request.user.nama_lengkap,
            'email_user': request.user.email,
        }
    else:
        context = {}
    return render(request, 'menu_users/kebijakan_privasi.html', context)


def bantuan_view(request):
    """Halaman bantuan dan kontak"""
    if request.user.is_authenticated:
        context = {
            'nama_user': request.user.nama_lengkap,
            'email_user': request.user.email,
        }
    else:
        context = {}
    return render(request, 'menu_users/bantuan.html', context)


# 🔐 FORGOT PASSWORD & RESET PASSWORD VIEWS
def forgot_password_view(request):
    """View untuk halaman lupa password - user input email"""
    from .forms import ForgotPasswordForm
    from .email_utils import send_notification_email
    import secrets
    from django.utils import timezone
    
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            try:
                email = form.cleaned_data['email']
                user = CustomUser.objects.get(email=email)
                
                # Generate reset token
                reset_token = secrets.token_urlsafe(32)
                user.password_reset_token = reset_token
                user.password_reset_token_created_at = timezone.now()
                user.save()
                
                # Buat reset URL
                reset_url = request.build_absolute_uri(f"/reset-password/?token={reset_token}&email={user.email}")
                
                logger.info(f"🔐 Generating reset password for user: {user.email}")
                logger.info(f"📧 Reset URL: {reset_url}")
                
                # Kirim email dengan reset link
                context = {
                    'user': user,
                    'reset_url': reset_url,
                    'token_valid_hours': 24
                }
                
                logger.info(f"📤 Attempting to send password reset email to {user.email}...")
                result = send_notification_email(
                    subject='Reset Password Akun Ruang Dengar',
                    recipient_list=[user.email],
                    template_name='emails/password_reset.html',
                    context=context,
                    fail_silently=False
                )
                logger.info(f"✅ Email sent successfully! Result: {result}")
                
                messages.success(
                    request, 
                    'Email reset password telah dikirim. Silakan cek inbox atau folder spam Anda. Link berlaku selama 24 jam.'
                )
                return redirect('login')
            
            except Exception as e:
                logger.error(f"❌ Error in forgot_password_view: {str(e)}", exc_info=True)
                messages.error(request, f'Terjadi kesalahan: {str(e)}')
        else:
            logger.warning(f"Invalid form submission for forgot password. Errors: {form.errors}")
    else:
        form = ForgotPasswordForm()
    
    return render(request, 'users/forgot_password.html', {'form': form})


def reset_password_view(request):
    """View untuk halaman reset password - user input password baru"""
    from .forms import ResetPasswordForm
    from django.utils import timezone
    from datetime import timedelta
    
    token = request.GET.get('token')
    email = request.GET.get('email')
    
    # Validasi token dan email
    try:
        user = CustomUser.objects.get(email=email, password_reset_token=token)
    except CustomUser.DoesNotExist:
        messages.error(request, 'Link reset password tidak valid atau email tidak ditemukan.')
        return redirect('login')
    
    # Cek apakah token sudah expired (24 jam)
    if user.password_reset_token_created_at:
        token_age = timezone.now() - user.password_reset_token_created_at
        if token_age > timedelta(hours=24):
            messages.error(request, 'Link reset password sudah expired. Silakan minta link baru.')
            return redirect('forgot-password')
    
    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password1']
            user.set_password(new_password)
            user.password_reset_token = None
            user.password_reset_token_created_at = None
            user.save()
            
            messages.success(request, 'Password berhasil direset! Silakan login dengan password baru Anda.')
            return redirect('login')
    else:
        form = ResetPasswordForm()
    
    context = {
        'form': form,
        'token': token,
        'email': email,
    }
    return render(request, 'users/reset_password.html', context)