#!/bin/bash

# Script Deployment Otomatis untuk Ruang Dengar
# Jalankan di VPS setelah login SSH

set -e  # Exit on error

echo "========================================="
echo "Ruang Dengar - Deployment Script"
echo "Domain: ruangdengar.cloud"
echo "========================================="

# Warna untuk output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Variabel
PROJECT_DIR="/var/www/ruangdengar"
VENV_DIR="$PROJECT_DIR/venv"
DB_NAME="ruangdengar_db"
DB_USER="ruangdengar_user"

# Function untuk print dengan warna
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

# Cek apakah dijalankan sebagai root
if [ "$EUID" -ne 0 ]; then 
    print_error "Script ini harus dijalankan sebagai root (sudo)"
    exit 1
fi

print_info "Step 1/12: Update sistem..."
apt update && apt upgrade -y
print_success "Sistem berhasil diupdate"

print_info "Step 2/12: Install dependencies..."
apt install -y python3-pip python3-venv nginx postgresql postgresql-contrib supervisor git certbot python3-certbot-nginx
print_success "Dependencies berhasil diinstall"

print_info "Step 3/12: Setup PostgreSQL..."
# Cek apakah database sudah ada
if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw $DB_NAME; then
    print_info "Database sudah ada, skip..."
else
    print_info "Masukkan password untuk database user '$DB_USER':"
    read -s DB_PASSWORD
    
    sudo -u postgres psql <<EOF
CREATE DATABASE $DB_NAME;
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
ALTER ROLE $DB_USER SET client_encoding TO 'utf8';
ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';
ALTER ROLE $DB_USER SET timezone TO 'Asia/Jakarta';
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF
    print_success "Database PostgreSQL berhasil dibuat"
fi

print_info "Step 4/12: Membuat direktori project..."
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR
print_success "Direktori project dibuat"

print_info "Step 5/12: Setup Virtual Environment..."
python3 -m venv $VENV_DIR
source $VENV_DIR/bin/activate
pip install --upgrade pip
print_success "Virtual environment berhasil dibuat"

print_info "Step 6/12: Install Python packages..."
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    pip install -r requirements.txt
    pip install gunicorn psycopg2-binary python-dotenv
    print_success "Python packages berhasil diinstall"
else
    print_error "File requirements.txt tidak ditemukan. Upload project terlebih dahulu!"
    exit 1
fi

print_info "Step 7/12: Setup environment variables..."
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cat > $PROJECT_DIR/.env <<EOF
SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DEBUG=False
ALLOWED_HOSTS=ruangdengar.cloud,www.ruangdengar.cloud,157.66.34.207

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_HOST=localhost
DB_PORT=5432

# Email (sesuaikan dengan provider Anda)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@ruangdengar.cloud
EOF
    print_success "File .env berhasil dibuat"
    print_info "PENTING: Edit file .env untuk konfigurasi email!"
else
    print_info "File .env sudah ada, skip..."
fi

print_info "Step 8/12: Migrasi database..."
python manage.py migrate
print_success "Database berhasil dimigrasi"

print_info "Step 9/12: Collect static files..."
python manage.py collectstatic --noinput
print_success "Static files berhasil dikumpulkan"

print_info "Step 10/12: Setup Gunicorn service..."
cat > /etc/systemd/system/gunicorn.service <<EOF
[Unit]
Description=gunicorn daemon for ruangdengar
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=$PROJECT_DIR
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=$VENV_DIR/bin/gunicorn \
          --workers 3 \
          --bind unix:$PROJECT_DIR/gunicorn.sock \
          ruangdengar.wsgi:application

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl start gunicorn
systemctl enable gunicorn
print_success "Gunicorn service berhasil dikonfigurasi"

print_info "Step 11/12: Setup Nginx..."
cat > /etc/nginx/sites-available/ruangdengar <<EOF
server {
    listen 80;
    server_name ruangdengar.cloud www.ruangdengar.cloud;

    client_max_body_size 50M;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        alias $PROJECT_DIR/static/;
    }
    
    location /media/ {
        alias $PROJECT_DIR/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:$PROJECT_DIR/gunicorn.sock;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header Host \$host;
        proxy_redirect off;
    }
}
EOF

ln -sf /etc/nginx/sites-available/ruangdengar /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx
print_success "Nginx berhasil dikonfigurasi"

print_info "Step 12/12: Set permissions..."
chown -R root:www-data $PROJECT_DIR
chmod -R 755 $PROJECT_DIR
chmod -R 775 $PROJECT_DIR/media
chmod -R 775 $PROJECT_DIR/static
print_success "Permissions berhasil diset"

echo ""
echo "========================================="
print_success "Deployment Selesai!"
echo "========================================="
echo ""
echo "Langkah selanjutnya:"
echo "1. Buat superuser: cd $PROJECT_DIR && source venv/bin/activate && python manage.py createsuperuser"
echo "2. Edit konfigurasi email di: $PROJECT_DIR/.env"
echo "3. Setup SSL: certbot --nginx -d ruangdengar.cloud -d www.ruangdengar.cloud"
echo "4. Setup firewall: ufw allow OpenSSH && ufw allow 'Nginx Full' && ufw enable"
echo ""
echo "Cek status:"
echo "- Gunicorn: systemctl status gunicorn"
echo "- Nginx: systemctl status nginx"
echo ""
echo "Website: http://ruangdengar.cloud"
echo "Admin: http://ruangdengar.cloud/admin"
echo ""
print_info "Jangan lupa setup SSL dengan certbot untuk HTTPS!"
echo "========================================="
