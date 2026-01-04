# Cara Menjalankan Ruang Dengar di Local (Windows)

## Opsi 1: Tanpa Environment Variable (Otomatis Development Mode)

Secara default, aplikasi akan berjalan dalam mode development dengan `DEBUG=True`.

```powershell
# Aktifkan virtual environment
.\myenv\Scripts\Activate.ps1

# Jalankan server
python manage.py runserver

# Akses di browser
# http://127.0.0.1:8000
```

---

## Opsi 2: Dengan Environment Variable (Recommended)

### Set environment variable untuk development:

**PowerShell:**
```powershell
$env:DJANGO_ENV = "development"
python manage.py runserver
```

**CMD:**
```cmd
set DJANGO_ENV=development
python manage.py runserver
```

---

## Konfigurasi Mode

### Development Mode (Default):
- ✅ DEBUG = True
- ✅ ALLOWED_HOSTS = ['*']
- ✅ Menggunakan SQLite database (db.sqlite3)
- ✅ Tidak perlu konfigurasi khusus
- ✅ Error ditampilkan di browser

### Production Mode:
- ❌ DEBUG = False
- ❌ ALLOWED_HOSTS = domain tertentu
- ⚠️ Memerlukan PostgreSQL
- ⚠️ Memerlukan konfigurasi .env
- ⚠️ Harus dijalankan dengan Gunicorn/uWSGI

---

## Testing di Local

```powershell
# Aktifkan virtual environment
.\myenv\Scripts\Activate.ps1

# Migrate database (jika belum)
python manage.py migrate

# Buat superuser (jika belum)
python manage.py createsuperuser

# Jalankan server
python manage.py runserver

# Buka browser
# http://127.0.0.1:8000
# http://127.0.0.1:8000/admin
```

---

## Troubleshooting

### Error: DisallowedHost at /
**Penyebab:** `DEBUG=False` tapi hostname tidak ada di `ALLOWED_HOSTS`

**Solusi:**
```powershell
# Pastikan DJANGO_ENV = development atau tidak diset
$env:DJANGO_ENV = "development"
python manage.py runserver
```

### Error: No module named 'xxx'
**Penyebab:** Package belum diinstall

**Solusi:**
```powershell
.\myenv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Error: Database locked
**Penyebab:** SQLite database sedang digunakan

**Solusi:**
- Tutup semua proses Python yang berjalan
- Atau hapus file `db.sqlite3-journal` jika ada

---

## Perbedaan Local vs Production

| Aspek | Local Development | Production (VPS) |
|-------|------------------|------------------|
| Environment | `DJANGO_ENV=development` | `DJANGO_ENV=production` |
| DEBUG | True | False |
| Database | SQLite | PostgreSQL |
| Server | Django dev server | Gunicorn + Nginx |
| HTTPS | Tidak | Ya (SSL Certificate) |
| Static Files | Django serve | Nginx serve |
| Error Display | Full traceback | Friendly error page |

---

## Sebelum Deploy ke Production

Pastikan test dulu di local:
1. ✅ Semua fitur berfungsi
2. ✅ Tidak ada error di console
3. ✅ Database migration berhasil
4. ✅ Static files loading dengan baik
5. ✅ Email configuration sudah ditest
6. ✅ Semua forms validation berfungsi

Baru kemudian deploy ke VPS mengikuti [deploy_guide.md](deploy_guide.md)
