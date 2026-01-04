# 🚀 QUICK START GUIDE - PRODUCTION DEPLOYMENT

**Time needed:** ~40 minutes  
**Status:** All code fixes completed ✅

---

## 📋 PRE-DEPLOYMENT CHECKLIST

- [ ] All fixes reviewed (check `DEPLOYMENT_SUMMARY.md`)
- [ ] Server ready (Ubuntu/Debian with sudo access)
- [ ] PostgreSQL installed on server
- [ ] Domain DNS pointing to server IP
- [ ] Email account ready (Gmail with App Password)

---

## ⚡ QUICK DEPLOYMENT - 5 MAIN STEPS

### **STEP 1: Server Preparation (SSH into VPS)**

```bash
# Login to VPS
ssh root@your-server-ip

# Update system
apt-get update && apt-get upgrade -y

# Install required packages
apt-get install -y python3 python3-venv python3-pip postgresql nginx certbot python3-certbot-nginx git

# Create project user
useradd -m -s /bin/bash www-data
cd /home/www-data

# Clone project
git clone <your-repo-url> ruangdengar
cd ruangdengar
```

### **STEP 2: Setup Environment Variables**

```bash
# Copy template
cp .env.production.example .env

# Edit with your values
nano .env
```

**Fill these REQUIRED fields:**
```
SECRET_KEY=<generate-new-one>
DB_NAME=ruangdengar_db
DB_USER=ruangdengar_user
DB_PASSWORD=<strong-password>
DB_HOST=localhost
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=<gmail-app-password>
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
SITE_URL=https://your-domain.com
```

**Generate SECRET_KEY:**
```bash
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### **STEP 3: Setup Python & Database**

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup PostgreSQL database
sudo bash setup_postgres.sh

# Run migrations
export DJANGO_ENV=production
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Create superuser
python manage.py createsuperuser
```

### **STEP 4: Setup Gunicorn**

```bash
# Create logs directory for gunicorn
sudo mkdir -p /var/log/gunicorn
sudo chown www-data:www-data /var/log/gunicorn

# Copy systemd service file
sudo cp ruangdengar.service /etc/systemd/system/

# EDIT THE FILE - replace /path/to/project and /path/to/venv:
sudo nano /etc/systemd/system/ruangdengar.service

# Enable and start service
sudo systemctl enable ruangdengar
sudo systemctl start ruangdengar
sudo systemctl status ruangdengar
```

### **STEP 5: Setup Nginx & SSL**

```bash
# Copy nginx config
sudo cp nginx_ruangdengar.conf /etc/nginx/sites-available/ruangdengar

# EDIT THE FILE - replace /path/to/project:
sudo nano /etc/nginx/sites-available/ruangdengar

# Enable site
sudo ln -s /etc/nginx/sites-available/ruangdengar /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Test nginx config
sudo nginx -t

# Get SSL certificate
sudo certbot certonly --standalone -d your-domain.com -d www.your-domain.com

# Reload nginx
sudo systemctl enable nginx
sudo systemctl restart nginx

# Auto-renew SSL
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

---

## ✅ VERIFICATION

After all steps, verify:

```bash
# Check Gunicorn running
sudo systemctl status ruangdengar

# Check Nginx running
sudo systemctl status nginx

# Check logs
sudo tail -f /var/log/gunicorn/ruangdengar_error.log
sudo tail -f /var/log/nginx/ruangdengar_error.log

# Test Django
curl http://localhost:8000
curl http://unix:/tmp/ruangdengar.sock
```

Visit in browser:
- `https://your-domain.com` - Main site
- `https://your-domain.com/admin` - Admin panel

---

## 🐛 TROUBLESHOOTING

### **503 Bad Gateway**
```bash
# Check if Gunicorn is running
sudo systemctl status ruangdengar

# Check socket exists
ls -la /tmp/ruangdengar.sock

# Restart
sudo systemctl restart ruangdengar
```

### **Database Connection Error**
```bash
# Test PostgreSQL connection
PGPASSWORD=<password> psql -h localhost -U ruangdengar_user -d ruangdengar_db

# Check Django migrations
DJANGO_ENV=production python manage.py showmigrations
```

### **Email Not Sending**
```bash
# Test SMTP credentials
python3 -c "
import smtplib
smtp = smtplib.SMTP('smtp.gmail.com', 587)
smtp.starttls()
smtp.login('your-email@gmail.com', 'your-app-password')
print('✅ Email credentials OK')
"
```

### **Static Files Not Loading**
```bash
# Verify static files exist
ls -la staticfiles/

# Verify nginx permissions
sudo chown -R www-data:www-data staticfiles/
```

---

## 📊 DEPLOYMENT CHECKLIST - MARK AS YOU COMPLETE

**Server Setup:**
- [ ] SSH access to VPS
- [ ] System packages installed
- [ ] www-data user created
- [ ] Project cloned from Git

**Python & Database:**
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] PostgreSQL database created
- [ ] .env file configured with all variables
- [ ] Django migrations run successfully
- [ ] Static files collected
- [ ] Superuser created

**Gunicorn:**
- [ ] ruangdengar.service file placed in /etc/systemd/system/
- [ ] Paths edited in service file
- [ ] Gunicorn socket created and running
- [ ] Log directories with correct permissions

**Nginx:**
- [ ] nginx_ruangdengar.conf placed in /etc/nginx/sites-available/
- [ ] Symlink created in /etc/nginx/sites-enabled/
- [ ] Nginx config tested (nginx -t passes)
- [ ] Nginx reloaded

**SSL Certificate:**
- [ ] Certificate obtained from Let's Encrypt
- [ ] HTTPS working
- [ ] HTTP redirects to HTTPS
- [ ] Certbot auto-renewal enabled

**Testing:**
- [ ] Site accessible at https://your-domain.com
- [ ] Admin accessible at https://your-domain.com/admin
- [ ] Email sends successfully
- [ ] Media files upload works
- [ ] Logs are being written

---

## 📞 SUPPORT DOCS

- `DEPLOYMENT_CHECKLIST.md` - Full detailed guide
- `DEPLOYMENT_SUMMARY.md` - What was fixed
- `.env.production.example` - All environment variables explained
- `nginx_ruangdengar.conf` - Nginx configuration template
- `ruangdengar.service` - Gunicorn systemd service
- `setup_postgres.sh` - PostgreSQL setup automation
- `setup_production.sh` - Production setup automation

---

## 🎯 COMMON COMMANDS

```bash
# SSH into server
ssh root@your-server-ip

# View Gunicorn logs
sudo journalctl -u ruangdengar -f

# View Nginx logs  
sudo tail -f /var/log/nginx/ruangdengar_error.log

# Restart services
sudo systemctl restart ruangdengar
sudo systemctl restart nginx

# Check service status
sudo systemctl status gunicorn
sudo systemctl status nginx

# Tail Django logs
tail -f logs/django.log

# Run Django management command
DJANGO_ENV=production python manage.py <command>
```

---

## ⚠️ IMPORTANT NOTES

1. **BACKUP DATABASE** regularly before any updates
2. **TEST** all changes in staging before production
3. **MONITOR** logs after deployment: `tail -f logs/django.log`
4. **UPDATE** packages monthly: `pip install --upgrade -r requirements.txt`
5. **SECURE** your .env file - add to .gitignore!

---

## 📅 NEXT STEPS

1. Follow the 5 main steps above
2. Verify everything works
3. Setup automated backups
4. Monitor logs for errors
5. Setup uptime monitoring
6. Configure email notifications

---

**Ready to deploy!** 🚀

Start with STEP 1 and work through each section.  
Estimated time: 40 minutes for complete setup.
