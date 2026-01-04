# Troubleshooting Error 500 di Production

## 1. Cek Error Logs di VPS

```bash
# SSH ke VPS
ssh root@157.66.34.207

# Cek Gunicorn logs
journalctl -u gunicorn -n 100 --no-pager

# Cek Nginx error logs
tail -100 /var/log/nginx/error.log

# Cek aplikasi logs (jika ada)
tail -100 /var/www/ruangdengar/logs/django.log 2>/dev/null || echo "No Django log file"
```

## 2. Verify Environment Variables

```bash
# Cek file .env
cat /var/www/ruangdengar/.env

# Harus ada:
# DJANGO_ENV=production
# DB_PASSWORD yang benar
# Semua email configuration
```

## 3. Verify Database Connection

```bash
cd /var/www/ruangdengar
source venv/bin/activate

# Test koneksi database
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ruangdengar.settings')
import django
django.setup()
from django.db import connection
try:
    connection.ensure_connection()
    print('✓ Database connection OK')
except Exception as e:
    print(f'✗ Database error: {e}')
"
```

## 4. Test Django Settings

```bash
cd /var/www/ruangdengar
source venv/bin/activate

# Cek environment
python -c "
import os
print(f'DJANGO_ENV: {os.environ.get(\"DJANGO_ENV\", \"NOT SET\")}')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ruangdengar.settings')
import django
django.setup()
from django.conf import settings
print(f'DEBUG: {settings.DEBUG}')
print(f'ENVIRONMENT: {settings.ENVIRONMENT}')
print(f'ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}')
print(f'DATABASE: {settings.DATABASES[\"default\"][\"ENGINE\"]}')
"
```

## 5. Test URLs & Views

```bash
cd /var/www/ruangdengar
source venv/bin/activate

# Cek URL resolve
python manage.py shell
>>> from django.urls import reverse
>>> reverse('dashboard_admin')
>>> reverse('lengkapi_profil')
```

## 6. Restart Services

```bash
# Restart Gunicorn
systemctl restart gunicorn

# Restart Nginx
systemctl restart nginx

# Check status
systemctl status gunicorn
systemctl status nginx
```

## 7. Collect Static Files

```bash
cd /var/www/ruangdengar
source venv/bin/activate
export DJANGO_ENV=production
python manage.py collectstatic --noinput
```

## 8. Create Superuser (if not exists)

```bash
cd /var/www/ruangdengar
source venv/bin/activate
export DJANGO_ENV=production
python manage.py createsuperuser
```

## 9. Run Database Migrations

```bash
cd /var/www/ruangdengar
source venv/bin/activate
export DJANGO_ENV=production
python manage.py migrate
```

## Common Error 500 Causes

### "no such table"
- Database not migrated
- **Fix:** `python manage.py migrate`

### "connection refused" 
- PostgreSQL not running or wrong credentials
- **Fix:** Check `.env` file DB credentials

### "Module not found"
- Package missing
- **Fix:** `pip install -r requirements.txt`

### "Permission denied"
- File permissions wrong
- **Fix:** `chown -R root:www-data /var/www/ruangdengar && chmod -R 755 /var/www/ruangdengar`

### "NAME is not defined" / Import errors
- Python syntax error or import issue
- **Fix:** `python manage.py check` to validate

### Static files 404
- collectstatic not run or Nginx config wrong
- **Fix:** `python manage.py collectstatic --noinput` and check Nginx config

## Advanced: Enable Debug Temporarily

⚠️ **ONLY FOR TESTING**, disable after!

Edit `.env`:
```
DJANGO_ENV=development
DEBUG=True
```

Then you'll see full error traceback in browser. After fixing, set back to production.

## After Fixing

```bash
# Test again
curl -I https://ruangdengar.cloud

# Check in browser
https://ruangdengar.cloud/login/
https://ruangdengar.cloud/admin/

# Monitor logs
tail -f /var/log/nginx/access.log
journalctl -u gunicorn -f
```

---

Laporkan output dari command-command di atas jika masih error!
