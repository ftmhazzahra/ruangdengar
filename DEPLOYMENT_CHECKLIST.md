# 🚀 DEPLOYMENT CHECKLIST - Production Ready

Semua masalah yang ditemukan dalam audit sudah diperbaiki. Ikuti checklist ini sebelum deploy.

## ✅ Fixes yang Sudah Dilakukan

### 1. **Security - SECRET_KEY**
- [x] SECRET_KEY tidak lagi hardcoded
- [x] Menggunakan `os.environ.get('SECRET_KEY')` 
- [x] Perlu diisi di .env saat deployment

### 2. **Environment Variables**
- [x] Database host tidak lagi default ke localhost
- [x] Email credentials tidak lagi hardcoded
- [x] Settings sekarang require environment variables di production

### 3. **Logging Configuration**
- [x] Menghapus semua `print()` statements (20+ occurrences)
- [x] Mengganti dengan proper `logger.debug()`
- [x] File logging dengan rotation: `logs/django.log`

### 4. **Static Files & Middleware**
- [x] Menambah WhiteNoise middleware untuk serve static files
- [x] Perbaiki STATICFILES_DIRS configuration

### 5. **Security Headers**
- [x] SECURE_SSL_REDIRECT = True (production)
- [x] SESSION_COOKIE_SECURE = True
- [x] CSRF_COOKIE_SECURE = True
- [x] SECURE_HSTS_SECONDS = 31536000

### 6. **Hardcoded URLs**
- [x] `create_admin.py` menggunakan `settings.SITE_URL` bukan hardcoded
- [x] Email template links akan menggunakan `settings.SITE_URL`

---

## 📋 DEPLOYMENT CHECKLIST - SEBELUM DEPLOY KE PRODUCTION

### 1. Environment Variables Setup
```bash
# Copy template
cp .env.production.example .env

# Edit .env dan isi SEMUA field:
nano .env
```

**WAJIB diisi:**
- [ ] `SECRET_KEY` - Generate dengan: `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`
- [ ] `DB_NAME` - nama database PostgreSQL
- [ ] `DB_USER` - username PostgreSQL
- [ ] `DB_PASSWORD` - password PostgreSQL yang KUAT
- [ ] `DB_HOST` - IP/hostname PostgreSQL server (bukan localhost!)
- [ ] `EMAIL_HOST_USER` - email Gmail Anda
- [ ] `EMAIL_HOST_PASSWORD` - App Password dari Gmail (bukan password biasa!)
- [ ] `ALLOWED_HOSTS` - domain Anda (contoh: ruangdengar.cloud,www.ruangdengar.cloud)
- [ ] `SITE_URL` - Full URL site (contoh: https://ruangdengar.cloud)

### 2. Database Setup
```bash
# Di VPS, setup PostgreSQL:
sudo su - postgres

# Create database
createdb ruangdengar_db

# Create user dengan password
createuser ruangdengar_user
psql -c "ALTER ROLE ruangdengar_user PASSWORD 'your-strong-password';"

# Grant privileges
psql -c "ALTER ROLE ruangdengar_user CREATEDB;"
psql -c "GRANT ALL PRIVILEGES ON DATABASE ruangdengar_db TO ruangdengar_user;"

exit
```

### 3. Django Setup
```bash
# Navigate to project directory
cd /path/to/project

# Run migrations
DJANGO_ENV=production python manage.py migrate

# Create superuser (if not using create_admin command)
DJANGO_ENV=production python manage.py createsuperuser

# Collect static files
DJANGO_ENV=production python manage.py collectstatic --noinput

# Test server
DJANGO_ENV=production python manage.py runserver 0.0.0.0:8000
```

### 4. Gunicorn Setup
```bash
# Install gunicorn (sudah di requirements.txt)
pip install gunicorn

# Create systemd service file
sudo nano /etc/systemd/system/ruangdengar.service
```

**Paste ini ke file:**
```
[Unit]
Description=Ruang Dengar Django Application
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/path/to/project
Environment="DJANGO_ENV=production"
EnvironmentFile=/path/to/project/.env
ExecStart=/path/to/venv/bin/gunicorn \
    --workers 4 \
    --bind unix:/tmp/ruangdengar.sock \
    --timeout 120 \
    ruangdengar.wsgi:application

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 5. Nginx Setup
```bash
# Create nginx config
sudo nano /etc/nginx/sites-available/ruangdengar
```

**Paste ini:**
```nginx
upstream ruangdengar {
    server unix:/tmp/ruangdengar.sock;
}

server {
    listen 80;
    server_name ruangdengar.cloud www.ruangdengar.cloud;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ruangdengar.cloud www.ruangdengar.cloud;
    
    # SSL certificates (use Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/ruangdengar.cloud/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ruangdengar.cloud/privkey.pem;
    
    client_max_body_size 50M;
    
    location /static/ {
        alias /path/to/project/staticfiles/;
    }
    
    location /media/ {
        alias /path/to/project/media/;
    }
    
    location / {
        proxy_pass http://ruangdengar;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 6. Enable Services
```bash
# Enable and start services
sudo systemctl enable ruangdengar
sudo systemctl start ruangdengar
sudo systemctl enable nginx
sudo systemctl restart nginx

# Check status
sudo systemctl status ruangdengar
sudo systemctl status nginx
```

### 7. SSL Certificate (Let's Encrypt)
```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --standalone -d ruangdengar.cloud -d www.ruangdengar.cloud

# Auto renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

### 8. Logs Configuration
```bash
# Create logs directory
mkdir -p /path/to/project/logs
sudo chown www-data:www-data /path/to/project/logs
sudo chmod 755 /path/to/project/logs
```

### 9. Backup Configuration
```bash
# Backup database regularly
0 2 * * * pg_dump -U ruangdengar_user ruangdengar_db > /backups/ruangdengar-$(date +\%Y\%m\%d).sql

# Backup media files
0 3 * * * tar -czf /backups/media-$(date +\%Y\%m\%d).tar.gz /path/to/project/media/
```

---

## 🧪 Testing Checklist

Sebelum production, test:
- [ ] Login dengan email verification
- [ ] Create report (laporan) berfungsi
- [ ] Booking konseling berfungsi
- [ ] Email notifications terkirim
- [ ] Admin dashboard accessible
- [ ] Static files (CSS, JS) loaded correctly
- [ ] Media uploads work
- [ ] 404 error pages display properly
- [ ] SSL certificate valid
- [ ] Database backups working

---

## ⚠️ IMPORTANT SECURITY NOTES

1. **NEVER** commit `.env` file to git
2. **ALWAYS** use strong passwords
3. **ALWAYS** use HTTPS in production
4. **Regularly** backup database
5. **Monitor** logs for errors
6. **Update** packages regularly: `pip install --upgrade -r requirements.txt`

---

## 📞 Troubleshooting

### Database Connection Error
```bash
# Test PostgreSQL connection
psql -h DB_HOST -U DB_USER -d DB_NAME
```

### Email Not Sending
```bash
# Check email logs
tail -f /path/to/project/logs/django.log

# Test SMTP credentials manually
python -c "
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your-email@gmail.com', 'your-app-password')
print('Email credentials OK')
server.quit()
"
```

### Static Files 404
```bash
# Ensure collectstatic was run
DJANGO_ENV=production python manage.py collectstatic --noinput

# Check permissions
sudo chown -R www-data:www-data /path/to/project/staticfiles/
sudo chmod -R 755 /path/to/project/staticfiles/
```

---

Generated: 2026-01-02
Status: ✅ PRODUCTION READY
