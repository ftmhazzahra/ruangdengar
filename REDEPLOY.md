# 🔄 QUICK REDEPLOY - EXISTING DEPLOYMENT

> Untuk aplikasi yang sudah running, perubahan code sudah dilakukan

---

## ⚡ REDEPLOY DALAM 5 LANGKAH (10 MENIT)

### **STEP 1: SSH ke VPS**
```bash
ssh root@your-server-ip
cd /path/to/ruangdengar
```

### **STEP 2: Pull Latest Code**
```bash
git pull origin main
```

### **STEP 3: Activate Venv & Install Dependencies**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### **STEP 4: Run Migrations & Collect Static**
```bash
export DJANGO_ENV=production
python manage.py migrate
python manage.py collectstatic --noinput
```

### **STEP 5: Restart Services**
```bash
sudo systemctl restart ruangdengar
sudo systemctl reload nginx
```

---

## ✅ VERIFICATION (1 MENIT)

```bash
# Check Gunicorn running
sudo systemctl status ruangdengar

# Check Nginx running  
sudo systemctl status nginx

# Test website
curl https://your-domain.com

# Check logs for errors
tail -f logs/django.log
```

---

## 🚀 AUTOMATED REDEPLOY

Atau gunakan script:

```bash
# SSH to server
ssh root@your-server-ip
cd /path/to/ruangdengar

# Copy script
wget https://raw.githubusercontent.com/your-repo/redeploy.sh

# Make executable
chmod +x redeploy.sh

# Run redeploy
bash redeploy.sh
```

---

## 📊 WHAT CHANGED (FIXES)

Jika ada masalah, ini yang sudah diperbaiki:

1. **SECRET_KEY** - Sekarang dari environment variable (bukan hardcoded)
2. **Print Statements** - Diganti dengan proper logging
3. **Database Config** - Tidak default ke localhost
4. **Email Config** - Tidak hardcoded
5. **Static Files** - WhiteNoise middleware ditambah
6. **Security Headers** - HTTPS + HSTS configured
7. **Logging** - Proper logger setup dengan rotation

---

## ⚠️ PENTING!

Sebelum redeploy, pastikan:

- [ ] `.env` file sudah ada dengan semua required variables
- [ ] Database still working
- [ ] PostgreSQL running: `sudo systemctl status postgresql`
- [ ] Backups updated
- [ ] SSL certificate valid

---

## 🐛 TROUBLESHOOTING

### 503 Bad Gateway
```bash
# Restart gunicorn
sudo systemctl restart ruangdengar

# Check if socket exists
ls -la /tmp/ruangdengar.sock
```

### Migration Error
```bash
# Check migration status
python manage.py showmigrations

# Rollback last migration if needed
python manage.py migrate users 0001  # etc
```

### Static Files 404
```bash
# Recollect static files
python manage.py collectstatic --clear --noinput

# Check permissions
sudo chown -R www-data:www-data staticfiles/
```

### Email Not Sending
```bash
# Check .env has email credentials
grep EMAIL_ .env

# Test SMTP
python3 -c "
import smtplib
s = smtplib.SMTP('smtp.gmail.com', 587)
s.starttls()
s.login('email@gmail.com', 'app-password')
print('✅ OK')
"
```

---

## 📋 REDEPLOY CHECKLIST

- [ ] Git code pulled
- [ ] Dependencies installed
- [ ] Migrations run successfully
- [ ] Static files collected
- [ ] Gunicorn restarted
- [ ] Nginx reloaded
- [ ] Services verified running
- [ ] Website accessible
- [ ] No errors in logs
- [ ] All features working

---

**Total time:** ~10 minutes  
**Downtime:** ~30 seconds (during service restart)  
**Rollback:** `git revert HEAD` if needed

