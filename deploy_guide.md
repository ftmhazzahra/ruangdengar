# Panduan Deployment Ruang Dengar ke VPS

## Domain: ruangdengar.cloud
## IP VPS: 157.66.34.207
## OS: Ubuntu 22.04

---

## 1. Konfigurasi DNS (Di Registrar Domain)

Login ke dashboard domain registrar Anda dan tambahkan DNS records berikut:

```
Type: A
Name: @
Value: 157.66.34.207

Type: A
Name: www
Value: 157.66.34.207
```

**Tunggu propagasi DNS (5 menit - 48 jam)**

Cek dengan: `ping ruangdengar.cloud`

---

## 2. Login ke VPS

```bash
ssh root@157.66.34.207
# Password: Tracer2025-ruangdengar!
```

**PENTING: Ganti password default setelah login pertama!**
```bash
passwd
```

---

## 3. Update Sistem & Install Dependencies

```bash
# Update sistem
apt update && apt upgrade -y

# Install dependencies
apt install -y python3-pip python3-venv nginx postgresql postgresql-contrib supervisor git

# Install certbot untuk SSL
apt install -y certbot python3-certbot-nginx
```

---

## 4. Setup PostgreSQL Database

```bash
# Login sebagai postgres
sudo -u postgres psql

# Di dalam psql, jalankan:
CREATE DATABASE ruangdengar_db;
CREATE USER ruangdengar_user WITH PASSWORD 'GantiPasswordIniDenganPasswordKuat123!';
ALTER ROLE ruangdengar_user SET client_encoding TO 'utf8';
ALTER ROLE ruangdengar_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE ruangdengar_user SET timezone TO 'Asia/Jakarta';
GRANT ALL PRIVILEGES ON DATABASE ruangdengar_db TO ruangdengar_user;
\q
```

---

## 5. Upload Project ke VPS

### Option A: Menggunakan Git (Recommended)
```bash
cd /var/www/
git clone https://github.com/your-username/ruangdengar.git
cd ruangdengar
```

### Option B: Upload manual via SCP (dari komputer lokal)
```bash
# Di komputer lokal (PowerShell/CMD)
scp -r "c:\Downloads\RUANG-DENGAR1-main\RUANG-DENGAR1-main\ruangdengar - Copy" root@157.66.34.207:/var/www/ruangdengar
```

---

## 6. Setup Python Virtual Environment

```bash
cd /var/www/ruangdengar
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn psycopg2-binary
```

---

## 7. Konfigurasi Environment Variables

Buat file `.env` untuk production:

```bash
nano /var/www/ruangdengar/.env
```

Isi dengan:
```env
# PENTING: Set environment ke production
DJANGO_ENV=production

SECRET_KEY=django-insecure-9sci)w)lft+h*!ft=h(na-+(p@_37$0m6tzly&*osb$(=c4qc9

# Database PostgreSQL
DB_ENGINE=django.db.backends.postgresql
DB_NAME=ruangdengar_db
DB_USER=ruangdengar_user
DB_PASSWORD=GantiPasswordIniDenganPasswordKuat123!
DB_HOST=localhost
DB_PORT=5432

# Email Settings (sesuaikan dengan email provider Anda)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@ruangdengar.cloud
```

**PENTING: Generate SECRET_KEY baru untuk production!**
```bash
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

---

## 8. Migrate Database & Collect Static Files

```bash
source venv/bin/activate
cd /var/www/ruangdengar

# Migrasi database
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Buat superuser
python manage.py createsuperuser
```

---

## 9. Konfigurasi Gunicorn

Buat file systemd service:

```bash
nano /etc/systemd/system/gunicorn.service
```

Isi dengan:
```ini
[Unit]
Description=gunicorn daemon for ruangdengar
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=/var/www/ruangdengar
EnvironmentFile=/var/www/ruangdengar/.env
ExecStart=/var/www/ruangdengar/venv/bin/gunicorn \
          --workers 3 \
          --bind unix:/var/www/ruangdengar/gunicorn.sock \
          ruangdengar.wsgi:application

[Install]
WantedBy=multi-user.target
```

Aktifkan dan jalankan:
```bash
systemctl daemon-reload
systemctl start gunicorn
systemctl enable gunicorn
systemctl status gunicorn
```

---

## 10. Konfigurasi Nginx

```bash
nano /etc/nginx/sites-available/ruangdengar
```

Isi dengan:
```nginx
server {
    listen 80;
    server_name ruangdengar.cloud www.ruangdengar.cloud;

    client_max_body_size 50M;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        alias /var/www/ruangdengar/static/;
    }
    
    location /media/ {
        alias /var/www/ruangdengar/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/ruangdengar/gunicorn.sock;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $host;
        proxy_redirect off;
    }
}
```

Aktifkan konfigurasi:
```bash
ln -s /etc/nginx/sites-available/ruangdengar /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

---

## 11. Setup SSL Certificate (HTTPS)

```bash
certbot --nginx -d ruangdengar.cloud -d www.ruangdengar.cloud
```

Ikuti instruksi interaktif. Pilih opsi untuk redirect HTTP ke HTTPS.

Auto-renewal sudah aktif secara default. Tes dengan:
```bash
certbot renew --dry-run
```

---

## 12. Set Permissions

```bash
chown -R root:www-data /var/www/ruangdengar
chmod -R 755 /var/www/ruangdengar
chmod -R 775 /var/www/ruangdengar/media
chmod -R 775 /var/www/ruangdengar/static
```

---

## 13. Testing

1. **Cek DNS:**
   ```bash
   ping ruangdengar.cloud
   ```

2. **Cek Nginx:**
   ```bash
   systemctl status nginx
   ```

3. **Cek Gunicorn:**
   ```bash
   systemctl status gunicorn
   ```

4. **Akses di browser:**
   - http://ruangdengar.cloud (akan redirect ke HTTPS)
   - https://ruangdengar.cloud
   - https://www.ruangdengar.cloud

5. **Admin panel:**
   - https://ruangdengar.cloud/admin

---

## 14. Monitoring & Maintenance

### Lihat log error:
```bash
# Nginx error log
tail -f /var/log/nginx/error.log

# Gunicorn log
journalctl -u gunicorn -f

# Django log (jika dikonfigurasi)
tail -f /var/www/ruangdengar/logs/django.log
```

### Restart services setelah update:
```bash
systemctl restart gunicorn
systemctl restart nginx
```

### Update aplikasi:
```bash
cd /var/www/ruangdengar
git pull  # atau upload file baru via SCP
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
systemctl restart gunicorn
```

---

## 15. Firewall (Optional tapi Recommended)

```bash
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable
ufw status
```

---

## Troubleshooting

### Error: Bad Gateway (502)
```bash
# Cek status gunicorn
systemctl status gunicorn
journalctl -u gunicorn -n 50

# Restart gunicorn
systemctl restart gunicorn
```

### Error: Static files tidak muncul
```bash
python manage.py collectstatic --noinput
chown -R root:www-data /var/www/ruangdengar/static
chmod -R 755 /var/www/ruangdengar/static
```

### Error: Permission denied untuk media upload
```bash
chmod -R 775 /var/www/ruangdengar/media
chown -R root:www-data /var/www/ruangdengar/media
```

---

## Checklist Deployment

- [ ] DNS A record sudah diset
- [ ] VPS bisa diakses via SSH
- [ ] Password default sudah diganti
- [ ] PostgreSQL database sudah dibuat
- [ ] Project sudah diupload ke VPS
- [ ] Virtual environment sudah dibuat
- [ ] Dependencies sudah diinstall
- [ ] File .env sudah dikonfigurasi
- [ ] Database migration sudah dijalankan
- [ ] Static files sudah dikumpulkan
- [ ] Superuser sudah dibuat
- [ ] Gunicorn service sudah running
- [ ] Nginx sudah dikonfigurasi
- [ ] SSL certificate sudah diinstall
- [ ] Website bisa diakses via HTTPS
- [ ] Admin panel bisa diakses
- [ ] Firewall sudah dikonfigurasi

---

**Selamat! Website Anda sudah live di https://ruangdengar.cloud 🎉**
