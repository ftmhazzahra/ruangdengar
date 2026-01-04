# Quick Deployment Commands untuk Ruang Dengar

## 1. SETUP DNS DOMAIN (Di Registrar)
```
Type: A
Name: @
Value: 157.66.34.207

Type: A  
Name: www
Value: 157.66.34.207
```

---

## 2. LOGIN & UPLOAD PROJECT KE VPS

### Login SSH:
```bash
ssh root@157.66.34.207
# Password: Tracer2025-ruangdengar!
```

### Upload project dari Windows (di PowerShell lokal):
```powershell
# Compress dulu (optional, lebih cepat)
Compress-Archive -Path "c:\Downloads\RUANG-DENGAR1-main\RUANG-DENGAR1-main\ruangdengar - Copy\*" -DestinationPath "c:\Downloads\ruangdengar.zip"

# Upload via SCP
scp "c:\Downloads\ruangdengar.zip" root@157.66.34.207:/tmp/

# Atau upload langsung folder (lebih lama)
scp -r "c:\Downloads\RUANG-DENGAR1-main\RUANG-DENGAR1-main\ruangdengar - Copy\*" root@157.66.34.207:/var/www/ruangdengar/
```

---

## 3. DI VPS - Extract & Deploy

```bash
# Jika upload zip
cd /tmp
apt install -y unzip
unzip ruangdengar.zip -d /var/www/ruangdengar

# Set permission & jalankan deployment script
cd /var/www/ruangdengar
chmod +x deploy.sh
./deploy.sh
```

---

## 4. MANUAL COMMANDS (Jika tidak pakai script)

```bash
# Update sistem
apt update && apt upgrade -y

# Install dependencies
apt install -y python3-pip python3-venv nginx postgresql postgresql-contrib git certbot python3-certbot-nginx

# Setup Database
sudo -u postgres psql
```

Di PostgreSQL console:
```sql
CREATE DATABASE ruangdengar_db;
CREATE USER ruangdengar_user WITH PASSWORD 'PasswordKuat123!';
ALTER ROLE ruangdengar_user SET client_encoding TO 'utf8';
ALTER ROLE ruangdengar_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE ruangdengar_user SET timezone TO 'Asia/Jakarta';
GRANT ALL PRIVILEGES ON DATABASE ruangdengar_db TO ruangdengar_user;
\q
```

Lanjut setup aplikasi:
```bash
# Setup Python environment
cd /var/www/ruangdengar
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn psycopg2-binary

# Buat file .env
nano .env
# Isi sesuai dengan contoh di deploy_guide.md

# Migrasi & collect static
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser

# Setup Gunicorn service
nano /etc/systemd/system/gunicorn.service
# Copy isi dari deploy_guide.md

systemctl daemon-reload
systemctl start gunicorn
systemctl enable gunicorn

# Setup Nginx
nano /etc/nginx/sites-available/ruangdengar
# Copy isi dari deploy_guide.md

ln -s /etc/nginx/sites-available/ruangdengar /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

# Setup SSL
certbot --nginx -d ruangdengar.cloud -d www.ruangdengar.cloud

# Set permissions
chown -R root:www-data /var/www/ruangdengar
chmod -R 755 /var/www/ruangdengar
chmod -R 775 /var/www/ruangdengar/media
chmod -R 775 /var/www/ruangdengar/static

# Setup firewall
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable
```

---

## 5. TESTING

```bash
# Cek services
systemctl status gunicorn
systemctl status nginx
systemctl status postgresql

# Cek logs jika error
journalctl -u gunicorn -n 50
tail -f /var/log/nginx/error.log

# Test DNS
ping ruangdengar.cloud
```

Browser:
- https://ruangdengar.cloud
- https://ruangdengar.cloud/admin

---

## 6. MAINTENANCE COMMANDS

### Restart services:
```bash
systemctl restart gunicorn
systemctl restart nginx
```

### Update aplikasi:
```bash
cd /var/www/ruangdengar
source venv/bin/activate
git pull  # atau upload file baru
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
systemctl restart gunicorn
```

### View logs:
```bash
# Gunicorn
journalctl -u gunicorn -f

# Nginx
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/access.log
```

### Backup database:
```bash
sudo -u postgres pg_dump ruangdengar_db > backup_$(date +%Y%m%d).sql
```

### Restore database:
```bash
sudo -u postgres psql ruangdengar_db < backup_20240101.sql
```

---

## TROUBLESHOOTING

### 502 Bad Gateway:
```bash
systemctl status gunicorn
journalctl -u gunicorn -n 50
systemctl restart gunicorn
```

### Static files tidak muncul:
```bash
python manage.py collectstatic --noinput
chmod -R 755 /var/www/ruangdengar/static
systemctl restart nginx
```

### Permission denied upload media:
```bash
chmod -R 775 /var/www/ruangdengar/media
chown -R root:www-data /var/www/ruangdengar/media
```

### Domain belum bisa diakses:
```bash
# Cek DNS propagation
ping ruangdengar.cloud
nslookup ruangdengar.cloud

# Cek Nginx config
nginx -t

# Cek firewall
ufw status
```
