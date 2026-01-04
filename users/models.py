from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

# Manager kustom untuk model user kita
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        """
        Membuat dan menyimpan user baru dengan email dan password.
        """
        if not email:
            raise ValueError('Email harus diisi')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Membuat dan menyimpan superuser baru.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', CustomUser.Role.ADMIN)  # 🧩 Tambahkan role otomatis

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser harus memiliki is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser harus memiliki is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


# Model User Kustom
class CustomUser(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        USER = 'user', 'User'
    
    class Fakultas(models.TextChoices):
        FTE = 'Fakultas Teknik Elektro', 'Fakultas Teknik Elektro'
        FRI = 'Fakultas Rekayasa Industri', 'Fakultas Rekayasa Industri'
        FIF = 'Fakultas Informatika', 'Fakultas Informatika'
        FEB = 'Fakultas Ekonomi dan Bisnis', 'Fakultas Ekonomi dan Bisnis'
        FIK = 'Fakultas Industri Kreatif', 'Fakultas Industri Kreatif'
        FIT = 'Fakultas Ilmu Terapan', 'Fakultas Ilmu Terapan'
    
    class StatusPengguna(models.TextChoices):
        MAHASISWA = 'Mahasiswa', 'Mahasiswa'
        DOSEN = 'Dosen', 'Dosen'
        TENAGA_PENUNJANG = 'Tenaga Penunjang Akademik', 'Tenaga Penunjang Akademik'

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.USER,
    )

    email = models.EmailField('Email', unique=True)
    email_verified = models.BooleanField(default=False, help_text='Apakah email sudah diverifikasi')
    email_verification_token = models.CharField(max_length=64, blank=True, null=True, help_text='Token verifikasi email')
    email_verification_sent_at = models.DateTimeField(blank=True, null=True, help_text='Waktu token verifikasi dikirim')
    password_reset_token = models.CharField(max_length=64, blank=True, null=True, help_text='Token reset password')
    password_reset_token_created_at = models.DateTimeField(blank=True, null=True, help_text='Waktu token reset password dibuat')
    nama_lengkap = models.CharField('Nama', max_length=255)
    username = models.CharField('Username', max_length=150, unique=True, null=True, blank=True)
    nidn = models.CharField('NIDN', max_length=50, blank=True, null=True)
    nim = models.CharField('NIM', max_length=50, blank=True, null=True)
    prodi = models.CharField('Prodi', max_length=100, blank=True, null=True)
    fakultas = models.CharField('Fakultas', max_length=100, choices=Fakultas.choices, blank=True, null=True)
    status_pengguna = models.CharField('Status', max_length=50, choices=StatusPengguna.choices, blank=True, null=True)
    usia = models.PositiveIntegerField('Usia', blank=True, null=True)
    no_whatsapp = models.CharField('Nomor WhatsApp', max_length=20, blank=True, null=True)
    email_pribadi = models.EmailField('Email Pribadi', blank=True, null=True)
    is_profile_complete = models.BooleanField(default=False, help_text='Apakah profil sudah lengkap (untuk Google OAuth)')
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True, help_text='Foto profil pengguna')
    
    # Data pribadi (hanya untuk user, tidak terlihat oleh admin jika anonim)
    nomor_telepon = models.CharField('Nomor Telepon', max_length=20, blank=True, null=True, help_text='Nomor telepon pribadi')
    alamat = models.TextField('Alamat', blank=True, null=True, help_text='Alamat tempat tinggal')
    nomor_telepon_kerabat = models.CharField('Nomor Telepon Kerabat/Orangtua', max_length=20, blank=True, null=True, help_text='Nomor yang dapat dihubungi dalam keadaan darurat')

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True, help_text='Untuk admin: apakah sudah disetujui oleh super admin')
    admin_approval_date = models.DateTimeField(null=True, blank=True, help_text='Tanggal admin disetujui')

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nama_lengkap', 'username']

    def __str__(self):
        return f"{self.nama_lengkap} ({self.role})"


# Models for laporan
class Laporan(models.Model):
    # Status mengikuti 5 Tahapan Resmi PPKPT + Detail Sub-Status
    STATUS_CHOICES = [
        # 1. PELAPORAN
        ('diterima', '🔵 Laporan Diterima'),
        ('verifikasi_awal', '⏳ Verifikasi Awal'),
        
        # 2. TINDAK LANJUT AWAL
        ('wawancara_pelapor', '🗣️ Wawancara Pelapor'),
        ('pengumpulan_bukti', '📁 Pengumpulan Bukti Tambahan'),
        
        # 3. PEMERIKSAAN
        ('wawancara_terlapor', '⏳ Wawancara Terlapor'),
        ('analisis_kronologi', '🔍 Pemeriksaan Kronologi & Analisis Bukti'),
        ('rapat_pemutusan', '🧩 Rapat Pemutusan Kasus'),
        
        # 4. PENANGANAN
        ('rekomendasi', '📌 Rekomendasi Tindak Lanjut'),
        
        # 5. TINDAK LANJUT
        ('pelaksanaan', '🚀 Pelaksanaan Tindak Lanjut'),
        ('ditutup', '✔ Kasus Ditutup'),
        
        # STATUS KHUSUS
        ('ditolak', '❌ Ditolak'),
    ]
    
    # Mapping status ke tahapan resmi PPKPT
    TAHAP_MAPPING = {
        'diterima': 1,
        'verifikasi_awal': 1,
        'wawancara_pelapor': 2,
        'pengumpulan_bukti': 2,
        'wawancara_terlapor': 3,
        'analisis_kronologi': 3,
        'rapat_pemutusan': 3,
        'rekomendasi': 4,
        'pelaksanaan': 5,
        'ditutup': 5,
        'ditolak': 0,  # Tidak termasuk tahapan normal
    }
    
    TAHAP_LABELS = {
        1: 'Pelaporan',
        2: 'Tindak Lanjut Awal',
        3: 'Pemeriksaan',
        4: 'Penanganan',
        5: 'Tindak Lanjut',
    }

    kode = models.CharField(max_length=64, unique=True, blank=True)
    
    def get_tahap_resmi(self):
        """Mengembalikan nomor tahapan resmi PPKPT (1-5)"""
        return self.TAHAP_MAPPING.get(self.status, 0)
    
    def get_tahap_label(self):
        """Mengembalikan label tahapan resmi PPKPT"""
        tahap = self.get_tahap_resmi()
        return self.TAHAP_LABELS.get(tahap, 'Tidak Teridentifikasi')
    
    def get_status_display_with_emoji(self):
        """Mengembalikan status dengan emoji"""
        for value, label in self.STATUS_CHOICES:
            if value == self.status:
                return label
        return self.get_status_display()
    
    def is_tahap_complete(self, tahap_number):
        """Cek apakah tahap tertentu sudah selesai"""
        current_tahap = self.get_tahap_resmi()
        if self.status == 'ditolak':
            return False
        return current_tahap > tahap_number or (current_tahap == tahap_number and self.status in ['ditutup'])
    
    # Data Pelapor
    pelapor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    is_anonim = models.BooleanField(default=False, help_text='Rahasiakan identitas dari terlapor')
    apakah_korban_langsung = models.BooleanField(default=True, help_text='Apakah pelapor adalah korban langsung')
    hubungan_pelapor_korban = models.CharField(max_length=255, blank=True, null=True, help_text='Jika bukan korban langsung, hubungan dengan korban')
    
    # Data Korban (jika berbeda dengan pelapor)
    nama_korban = models.CharField('Nama Korban', max_length=255, blank=True, null=True)
    nim_nip_korban = models.CharField('NIM/NIP/NIK Korban', max_length=50, blank=True, null=True)
    status_korban = models.CharField('Status Korban', max_length=50, blank=True, null=True)
    fakultas_korban = models.CharField('Fakultas Korban', max_length=100, blank=True, null=True)
    prodi_korban = models.CharField('Prodi Korban', max_length=100, blank=True, null=True)
    jenis_kelamin_korban = models.CharField('Jenis Kelamin Korban', max_length=20, choices=[('Laki-laki', 'Laki-laki'), ('Perempuan', 'Perempuan')], blank=True, null=True)
    
    # Data Terlapor
    jumlah_terlapor = models.CharField('Jumlah Terlapor', max_length=255, blank=True, null=True, help_text='Jika lebih dari 1, pisahkan dengan koma')
    nama_terlapor = models.CharField('Nama Terlapor', max_length=255, default='Tidak Diketahui')
    nim_nip_terlapor = models.CharField('NIM/NIP/NIK Terlapor', max_length=50, default='')
    asal_instansi_terlapor = models.CharField('Asal Instansi Terlapor', max_length=255, default='Telkom University')
    fakultas_terlapor = models.CharField('Fakultas Terlapor', max_length=100, default='')
    prodi_terlapor = models.CharField('Prodi Terlapor', max_length=100, default='')
    no_wa_terlapor = models.CharField('No WhatsApp Terlapor', max_length=20, default='')
    hubungan_terlapor_korban = models.CharField('Hubungan Terlapor dengan Korban', max_length=255, default='')
    ciri_ciri_pelaku = models.TextField('Ciri-ciri Pelaku (Deskripsi Fisik)', help_text='Deskripsi fisik, pakaian, tanda khusus, dll')
    
    # Deskripsi Masalah (sesuai 6 kategori PPKPT resmi)
    JENIS_KEKERASAN_CHOICES = [
        ('Kekerasan Fisik', 'Kekerasan Fisik'),
        ('Kekerasan Psikis', 'Kekerasan Psikis'),
        ('Kekerasan Fisik dan Psikis', 'Kekerasan Fisik dan Psikis'),
        ('Perundungan (Bullying)', 'Perundungan (Bullying)'),
        ('Kekerasan Seksual', 'Kekerasan Seksual'),
        ('Diskriminasi dan Intoleransi', 'Diskriminasi dan Intoleransi'),
        ('Kebijakan yang Mengandung Kekerasan', 'Kebijakan yang Mengandung Kekerasan'),
        ('Lainnya', 'Lainnya'),
    ]
    jenis = models.CharField('Jenis Dugaan Kekerasan', max_length=120, choices=JENIS_KEKERASAN_CHOICES, default='Kekerasan Seksual')
    kronologi_singkat = models.TextField('Kronologi Singkat', help_text='Ringkasan singkat kejadian', blank=True, default='')
    deskripsi = models.TextField('Deskripsi Lengkap', help_text='Ceritakan kronologi lengkap kejadian')
    lokasi = models.CharField('Tempat Kejadian', max_length=255, default='')
    link_pelaporan = models.URLField('Link Kronologi Lengkap', max_length=1000, blank=True, help_text='Link Google Drive/OneDrive untuk kronologi lengkap')
    
    # Status & Rekomendasi
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='diterima')
    rekomendasi = models.TextField(blank=True)
    
    # AI Content Moderation Fields
    ai_kategori = models.CharField(max_length=100, blank=True, null=True, help_text="Kategori otomatis dari AI")
    ai_urgency = models.CharField(max_length=20, blank=True, null=True, choices=[
        ('darurat', 'Darurat'),
        ('tinggi', 'Tinggi'),
        ('sedang', 'Sedang'),
        ('rendah', 'Rendah'),
    ], help_text="Tingkat urgensi dari AI")
    ai_toxicity_score = models.FloatField(blank=True, null=True, help_text="Skor toksisitas (0-1)")
    ai_needs_blur = models.BooleanField(default=False, help_text="Apakah konten perlu di-blur")
    ai_analyzed = models.BooleanField(default=False, help_text="Sudah dianalisis AI atau belum")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.kode} - {self.jenis}"


class Evidence(models.Model):
    laporan = models.ForeignKey(Laporan, related_name='evidences', on_delete=models.CASCADE)
    file = models.FileField(upload_to='evidence/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, help_text='Siapa yang upload (admin atau pelapor)')
    keterangan = models.CharField(max_length=255, blank=True, help_text='Keterangan bukti tambahan')

    def __str__(self):
        return f"Evidence for {self.laporan.kode}"


class Progress(models.Model):
    laporan = models.ForeignKey(Laporan, related_name='progress', on_delete=models.CASCADE)
    status = models.CharField(max_length=64)
    catatan = models.TextField(blank=True)
    oleh = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    tanggal = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.laporan.kode} - {self.status} @ {self.tanggal}"


class PelaporResponse(models.Model):
    """Model untuk balasan/komentar pelapor ke admin mengenai progress laporan"""
    laporan = models.ForeignKey(Laporan, related_name='pelapor_responses', on_delete=models.CASCADE)
    progress = models.ForeignKey(Progress, null=True, blank=True, on_delete=models.SET_NULL, help_text='Progress yang dibalas (opsional)')
    pesan = models.TextField(help_text='Pesan/balasan dari pelapor')
    tanggal = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['tanggal']
    
    def __str__(self):
        return f"Response for {self.laporan.kode} @ {self.tanggal}"


class Booking(models.Model):
    STATUS_CHOICES = [
        ('terjadwal', 'Terjadwal'),
        ('selesai', 'Selesai'),
        ('dibatalkan', 'Dibatalkan'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='bookings', on_delete=models.CASCADE)
    tanggal = models.DateField()
    waktu = models.TimeField()
    konselor = models.CharField(max_length=255)
    konselor_fk = models.ForeignKey('Counselor', null=True, blank=True, on_delete=models.SET_NULL, related_name='bookings')
    nama = models.CharField(max_length=255)
    topik = models.TextField(blank=True)
    jenis = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='terjadwal')
    alasan_pembatalan = models.TextField(blank=True, null=True)
    lokasi_konseling = models.CharField(max_length=255, default='REK-407', help_text='Ruangan konseling')
    catatan_admin = models.TextField(blank=True, null=True, help_text='Catatan dari admin untuk mahasiswa')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-tanggal', '-waktu']

    def __str__(self):
        return f"Booking {self.user} on {self.tanggal} {self.waktu} ({self.status})"


class RekamMedisKonseling(models.Model):
    """Model untuk rekam medis konseling (hanya bisa diakses konselor & admin)"""
    
    class RisikoBunuhDiri(models.TextChoices):
        RENDAH = 'rendah', 'Rendah'
        SEDANG = 'sedang', 'Sedang'
        TINGGI = 'tinggi', 'Tinggi'
        TIDAK_ADA = 'tidak_ada', 'Tidak Ada'
    
    class RisikoSelfHarm(models.TextChoices):
        RENDAH = 'rendah', 'Rendah'
        SEDANG = 'sedang', 'Sedang'
        TINGGI = 'tinggi', 'Tinggi'
        TIDAK_ADA = 'tidak_ada', 'Tidak Ada'
    
    # Relasi ke booking konseling
    konseling = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='rekam_medis')
    
    # Informasi sesi
    sesi_ke = models.PositiveIntegerField(default=1, help_text='Sesi keberapa')
    tanggal_sesi = models.DateTimeField(auto_now_add=True)
    
    # Assessment klien
    diagnosis_awal = models.CharField(max_length=500, blank=True, help_text='Diagnosis awal (jika ada)')
    mood_klien = models.PositiveIntegerField(
        default=5, 
        help_text='Skala mood 1-10 (1=sangat buruk, 10=sangat baik)',
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    risiko_bunuh_diri = models.CharField(
        max_length=20, 
        choices=RisikoBunuhDiri.choices, 
        default=RisikoBunuhDiri.TIDAK_ADA,
        help_text='Assessment risiko bunuh diri'
    )
    risiko_self_harm = models.CharField(
        max_length=20, 
        choices=RisikoSelfHarm.choices, 
        default=RisikoSelfHarm.TIDAK_ADA,
        help_text='Assessment risiko self-harm'
    )
    
    # Catatan sesi
    catatan_konselor = models.TextField(
        help_text='Catatan lengkap konselor tentang sesi (CONFIDENTIAL - tidak bisa dilihat klien)'
    )
    intervensi_diberikan = models.TextField(
        blank=True, 
        help_text='Teknik/intervensi yang digunakan (CBT, mindfulness, dll)'
    )
    progress_notes = models.TextField(
        blank=True, 
        help_text='Catatan progress/perkembangan klien'
    )
    
    # Rencana tindak lanjut
    rencana_tindak_lanjut = models.TextField(
        blank=True, 
        help_text='Rencana untuk sesi berikutnya atau rujukan'
    )
    sesi_selanjutnya = models.DateField(
        null=True, 
        blank=True, 
        help_text='Tanggal rencana sesi berikutnya'
    )
    
    # Lampiran (opsional)
    file_lampiran = models.FileField(
        upload_to='rekam_medis/', 
        blank=True, 
        null=True, 
        help_text='File pendukung (assessment form, dll)'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='rekam_medis_created',
        help_text='Konselor yang membuat rekam medis'
    )
    
    class Meta:
        ordering = ['-tanggal_sesi']
        verbose_name = 'Rekam Medis Konseling'
        verbose_name_plural = 'Rekam Medis Konseling'
    
    def __str__(self):
        return f"Rekam Medis - {self.konseling.nama} (Sesi {self.sesi_ke}) - {self.tanggal_sesi.strftime('%d %b %Y')}"


class Counselor(models.Model):
    name = models.CharField(max_length=255)
    title = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.name}{(' - ' + self.title) if self.title else ''}"


class Konten(models.Model):
    """Model untuk konten edukasi/artikel"""
    
    class Kategori(models.TextChoices):
        KESADARAN = 'kesadaran', 'Kesadaran'
        PENCEGAHAN = 'pencegahan', 'Pencegahan'
        DUKUNGAN = 'dukungan', 'Dukungan'
        INFORMASI = 'informasi', 'Informasi'
    
    judul = models.CharField(max_length=255)
    kategori = models.CharField(max_length=20, choices=Kategori.choices, default=Kategori.INFORMASI)
    deskripsi = models.TextField(help_text="Deskripsi singkat untuk card")
    konten = models.TextField(help_text="Isi artikel lengkap")
    gambar = models.ImageField(upload_to='konten/', blank=True, null=True)
    media_url = models.URLField(max_length=500, blank=True, null=True, help_text="Link ke PDF, YouTube, atau media eksternal lainnya")
    penulis = models.CharField(max_length=255, default="Tim Ruang Dengar")
    tags = models.CharField(max_length=500, blank=True, help_text="Tags dipisah koma, contoh: bullying,kekerasan fisik,pelecehan")
    view_count = models.IntegerField(default=0, help_text="Jumlah kali artikel dibuka")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=True)
    scheduled_date = models.DateTimeField(null=True, blank=True, help_text="Tanggal publikasi terjadwal")
    
    class Meta:
        verbose_name = "Konten"
        verbose_name_plural = "Konten"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.judul


# Model Notification
class Notification(models.Model):
    TYPE_CHOICES = [
        ('laporan_baru', 'Laporan Baru'),
        ('booking_baru', 'Booking Baru'),
        ('laporan_darurat', 'Laporan Darurat'),
        ('status_laporan', 'Update Status Laporan'),
        ('jadwal_berubah', 'Perubahan Jadwal'),
        ('jadwal_dibatalkan', 'Jadwal Dibatalkan'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Optional: link to related object
    laporan = models.ForeignKey(Laporan, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    booking = models.ForeignKey('Booking', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notifikasi'
        verbose_name_plural = 'Notifikasi'
    
    def __str__(self):
        return f"{self.user.nama_lengkap} - {self.title}"

