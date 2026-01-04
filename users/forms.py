from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser
import re

# Pilihan Program Studi per Fakultas (Telkom University Purwokerto)
PRODI_CHOICES = [
    ('', '-- Pilih Program Studi --'),
    # Fakultas Teknik Elektro
    ('S1 Teknik Telekomunikasi', 'S1 Teknik Telekomunikasi'),
    ('S1 Teknik Elektro', 'S1 Teknik Elektro'),
    ('S1 Teknik Biomedis', 'S1 Teknik Biomedis'),
    ('S1 Teknologi Pangan', 'S1 Teknologi Pangan'),
    # Fakultas Rekayasa Industri
    ('S1 Teknik Industri', 'S1 Teknik Industri'),
    ('S1 Sistem Informasi', 'S1 Sistem Informasi'),
    ('S1 Digital Supply Chain', 'S1 Digital Supply Chain'),
    # Fakultas Informatika
    ('S1 Informatika', 'S1 Informatika'),
    ('S1 Rekayasa Perangkat Lunak', 'S1 Rekayasa Perangkat Lunak'),
    ('S1 Data Sains', 'S1 Data Sains'),
    # Fakultas Ekonomi dan Bisnis
    ('S1 Digital Business', 'S1 Digital Business'),
    # Fakultas Industri Kreatif
    ('S1 Desain Komunikasi Visual', 'S1 Desain Komunikasi Visual'),
    ('S1 Desain Produk', 'S1 Desain Produk'),
    # Fakultas Ilmu Terapan
    ('D3 Teknik Telekomunikasi', 'D3 Teknik Telekomunikasi'),
]

def validate_password_strength(password):
    """Validasi password harus mengandung huruf dan angka"""
    if not re.search(r'[a-zA-Z]', password):
        raise forms.ValidationError('Password harus mengandung huruf (a-z, A-Z)')
    if not re.search(r'[0-9]', password):
        raise forms.ValidationError('Password harus mengandung angka (0-9)')


# --- Form Registrasi Pengguna ---
class CustomUserCreationForm(UserCreationForm):
    prodi = forms.ChoiceField(
        choices=PRODI_CHOICES,
        label="Program Studi",
        widget=forms.Select(attrs={'id': 'id_prodi'})
    )
    
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('nama_lengkap', 'nim', 'email', 'fakultas', 'prodi', 'status_pengguna', 'usia', 'no_whatsapp')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nama_lengkap'].label = "Nama Lengkap"
        self.fields['nim'].label = "NIM"
        self.fields['email'].label = "Email"
        self.fields['fakultas'].label = "Fakultas"
        self.fields['status_pengguna'].label = "Status"
        self.fields['usia'].label = "Usia"
        self.fields['no_whatsapp'].label = "Nomor WhatsApp"
        self.fields['password1'].label = "Password"
        self.fields['password2'].label = "Konfirmasi Password"

        self.fields['email'].widget.attrs.update({'placeholder': 'contoh@email.com'})
        self.fields['nim'].widget.attrs.update({'placeholder': 'Contoh: 1301190123'})
        self.fields['fakultas'].widget.attrs.update({'id': 'id_fakultas'})
        self.fields['usia'].widget.attrs.update({'placeholder': 'Contoh: 20', 'min': '17', 'max': '100'})
        self.fields['no_whatsapp'].widget.attrs.update({'placeholder': 'Contoh: 081234567890'})
        self.fields['password1'].widget.attrs.update({'placeholder': 'Minimal 8 karakter (huruf + angka)'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'Ulangi password'})
    
    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if password1:
            validate_password_strength(password1)
        return password1


    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = CustomUser.Role.USER  # Set role otomatis
        user.is_profile_complete = True  # Manual registration sudah lengkap
        if commit:
            user.save()
        return user

# --- Form Registrasi Admin ---
class AdminUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('nama_lengkap', 'username', 'nidn', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nama_lengkap'].label = "Nama"
        self.fields['username'].label = "Username"
        self.fields['nidn'].label = "NIDN"
        self.fields['email'].label = "Email"
        self.fields['password1'].label = "Password"
        self.fields['password2'].label = "Konfirmasi Password"

        self.fields['email'].widget.attrs.update({'placeholder': 'contoh@email.com'})
        self.fields['password1'].widget.attrs.update({'placeholder': 'Minimal 8 karakter (huruf + angka)'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'Minimal 8 karakter (huruf + angka)'})
    
    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if password1:
            validate_password_strength(password1)
        return password1


    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = CustomUser.Role.ADMIN  # Set role otomatis
        user.is_staff = True  # Admin harus bisa login ke admin site
        if commit:
            user.save()
        return user

# --- Form Login ---
class CustomAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label='Email Kampus',
        widget=forms.EmailInput(attrs={'placeholder': 'contoh.email@gmail.com', 'autofocus': True})
    )
    password = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Minimal 8 karakter', 'autocomplete': 'current-password'})
    )
    remember_me = forms.BooleanField(
        label='Remember me',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


# --- Form Edit Profile ---
class EditProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = (
            'nama_lengkap', 'email', 'nim', 'nidn', 'prodi', 'fakultas', 
            'status_pengguna', 'usia', 'no_whatsapp', 'email_pribadi', 'profile_picture',
            'nomor_telepon', 'alamat', 'nomor_telepon_kerabat'
        )
        widgets = {
            'nama_lengkap': forms.TextInput(attrs={'readonly': 'readonly', 'style': 'background-color: #f3f4f6; cursor: not-allowed;'}),
            'email': forms.EmailInput(attrs={'readonly': 'readonly', 'style': 'background-color: #f3f4f6; cursor: not-allowed;'}),
            'nim': forms.TextInput(attrs={'readonly': 'readonly', 'style': 'background-color: #f3f4f6; cursor: not-allowed;'}),
            'nidn': forms.TextInput(attrs={'readonly': 'readonly', 'style': 'background-color: #f3f4f6; cursor: not-allowed;'}),
            'alamat': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Masukkan alamat lengkap'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        readonly_fields = ['nama_lengkap', 'email', 'nim', 'nidn', 'fakultas', 'prodi', 'status_pengguna', 'usia', 'no_whatsapp']

        # Readonly fields
        self.fields['nama_lengkap'].label = "Nama Lengkap"
        self.fields['nama_lengkap'].help_text = "⚠️ Nama lengkap tidak dapat diubah"
        self.fields['nama_lengkap'].required = False
        self.fields['nama_lengkap'].widget.attrs.update({'disabled': 'disabled', 'style': 'background-color: #f3f4f6; cursor: not-allowed;'})
        
        self.fields['email'].label = "Email Kampus"
        self.fields['email'].help_text = "⚠️ Email tidak dapat diubah"
        self.fields['email'].required = False
        self.fields['email'].widget.attrs.update({'disabled': 'disabled', 'style': 'background-color: #f3f4f6; cursor: not-allowed;'})
        
        # NIM/NIDN fields (readonly, tapi bisa kosong untuk non-mahasiswa)
        self.fields['nim'].label = "NIM"
        self.fields['nim'].help_text = "⚠️ NIM tidak dapat diubah (khusus Mahasiswa)"
        self.fields['nim'].required = False
        self.fields['nim'].widget.attrs.update({'disabled': 'disabled', 'style': 'background-color: #f3f4f6; cursor: not-allowed;'})
        
        self.fields['nidn'].label = "NIDN"
        self.fields['nidn'].help_text = "⚠️ NIDN tidak dapat diubah (khusus Dosen)"
        self.fields['nidn'].required = False
        self.fields['nidn'].widget.attrs.update({'disabled': 'disabled', 'style': 'background-color: #f3f4f6; cursor: not-allowed;'})
        
        # Editable fields
        self.fields['prodi'].label = "Program Studi"
        self.fields['prodi'].widget.attrs.update({'placeholder': 'Contoh: Teknik Informatika'})
        self.fields['prodi'].required = False
        self.fields['prodi'].widget.attrs.update({'disabled': 'disabled', 'style': 'background-color: #f3f4f6; cursor: not-allowed;'})
        
        self.fields['fakultas'].label = "Fakultas"
        self.fields['fakultas'].required = False
        self.fields['fakultas'].choices = [('', '-- Pilih Fakultas --')] + list(self.fields['fakultas'].choices)
        self.fields['fakultas'].widget.attrs.update({'disabled': 'disabled', 'style': 'background-color: #f3f4f6; cursor: not-allowed;'})
        
        self.fields['status_pengguna'].label = "Status"
        self.fields['status_pengguna'].required = False
        self.fields['status_pengguna'].choices = [('', '-- Pilih Status --')] + list(self.fields['status_pengguna'].choices)
        self.fields['status_pengguna'].widget.attrs.update({'disabled': 'disabled', 'style': 'background-color: #f3f4f6; cursor: not-allowed;'})
        
        self.fields['usia'].label = "Usia"
        self.fields['usia'].widget.attrs.update({'placeholder': 'Contoh: 20', 'type': 'number', 'min': '17', 'max': '100'})
        self.fields['usia'].required = False
        self.fields['usia'].widget.attrs.update({'disabled': 'disabled', 'style': 'background-color: #f3f4f6; cursor: not-allowed;'})
        
        self.fields['no_whatsapp'].label = "Nomor WhatsApp"
        self.fields['no_whatsapp'].widget.attrs.update({'placeholder': '08xxxxxxxxxx'})
        self.fields['no_whatsapp'].help_text = "Nomor WhatsApp untuk komunikasi"
        self.fields['no_whatsapp'].required = False
        self.fields['no_whatsapp'].widget.attrs.update({'disabled': 'disabled', 'style': 'background-color: #f3f4f6; cursor: not-allowed;'})

        self.fields['email_pribadi'].label = "Email Pribadi"
        self.fields['email_pribadi'].required = False
        self.fields['email_pribadi'].widget.attrs.update({'placeholder': 'contoh@gmail.com'})
        
        self.fields['profile_picture'].label = "Foto Profile"
        self.fields['profile_picture'].help_text = "Upload foto profile (Max 2MB, format: JPG, PNG)"
        self.fields['profile_picture'].required = False
        
        self.fields['nomor_telepon'].label = "Nomor Telepon Pribadi"
        self.fields['nomor_telepon'].widget.attrs.update({'placeholder': '08xxxxxxxxxx'})
        self.fields['nomor_telepon'].required = False
        
        self.fields['alamat'].label = "Alamat Lengkap"
        self.fields['alamat'].required = False
        
        self.fields['nomor_telepon_kerabat'].label = "Nomor Telepon Kerabat/Orangtua"
        self.fields['nomor_telepon_kerabat'].widget.attrs.update({'placeholder': '08xxxxxxxxxx (Darurat)'})
        self.fields['nomor_telepon_kerabat'].help_text = "Nomor yang dapat dihubungi dalam keadaan darurat"
        self.fields['nomor_telepon_kerabat'].required = False

        self.readonly_fields = readonly_fields

    def clean(self):
        cleaned_data = super().clean()
        # Pastikan field yang dibuat disabled tidak memicu validasi dan tidak berubah
        if hasattr(self, 'readonly_fields'):
            for field in self.readonly_fields:
                cleaned_data[field] = getattr(self.instance, field)
        return cleaned_data


# --- Form Change Password ---
class ChangePasswordForm(forms.Form):
    old_password = forms.CharField(
        label='Password Lama',
        widget=forms.PasswordInput(attrs={'placeholder': 'Masukkan password lama'})
    )
    new_password1 = forms.CharField(
        label='Password Baru',
        widget=forms.PasswordInput(attrs={'placeholder': 'Minimal 8 karakter'})
    )
    new_password2 = forms.CharField(
        label='Konfirmasi Password Baru',
        widget=forms.PasswordInput(attrs={'placeholder': 'Ulangi password baru'})
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')
        if not self.user.check_password(old_password):
            raise forms.ValidationError('Password lama salah')
        return old_password
    
    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')
        
        if new_password1 and new_password2:
            if new_password1 != new_password2:
                raise forms.ValidationError('Password baru tidak cocok')
            if len(new_password1) < 8:
                raise forms.ValidationError('Password minimal 8 karakter')
            # Validasi kekuatan password
            validate_password_strength(new_password1)
        
        return cleaned_data


# --- Form Lupa Password ---
class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        label='Email Terdaftar',
        widget=forms.EmailInput(attrs={
            'placeholder': 'Masukkan email Anda',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
        })
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('Email ini tidak terdaftar di sistem.')
        return email


# --- Form Reset Password ---
class ResetPasswordForm(forms.Form):
    new_password1 = forms.CharField(
        label='Password Baru',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Minimal 8 karakter (huruf + angka)',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
        })
    )
    new_password2 = forms.CharField(
        label='Konfirmasi Password Baru',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Ulangi password baru',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
        })
    )
    
    def clean_new_password1(self):
        new_password1 = self.cleaned_data.get('new_password1')
        if new_password1:
            validate_password_strength(new_password1)
        return new_password1
    
    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')
        
        if new_password1 and new_password2:
            if new_password1 != new_password2:
                raise forms.ValidationError('Password baru tidak cocok')
            if len(new_password1) < 8:
                raise forms.ValidationError('Password minimal 8 karakter')
        
        return cleaned_data

