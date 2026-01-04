#!/bin/bash
# ==========================================
# RUANG DENGAR - PostgreSQL Setup Script
# ==========================================
# Run this as root or with sudo
# Usage: sudo bash setup_postgres.sh

set -e

echo "=========================================="
echo "🐘 PostgreSQL Database Setup"
echo "=========================================="
echo ""

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL is not installed!"
    echo "Install with: sudo apt-get install postgresql postgresql-contrib"
    exit 1
fi

echo "✅ PostgreSQL found"

# 1. Get database configuration from .env
if [ ! -f .env ]; then
    echo "❌ ERROR: .env file not found!"
    echo "Create it from .env.production.example first"
    exit 1
fi

# Load .env variables
export $(cat .env | grep -v '#' | xargs)

echo ""
echo "Using configuration from .env:"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo ""

# 2. Create database
echo "🔨 Creating database '$DB_NAME'..."
sudo -u postgres createdb "$DB_NAME" 2>/dev/null || echo "  (Database already exists)"

# 3. Create user
echo "👤 Creating user '$DB_USER'..."
sudo -u postgres createuser "$DB_USER" 2>/dev/null || echo "  (User already exists)"

# 4. Set password
echo "🔐 Setting password for '$DB_USER'..."
sudo -u postgres psql << EOF
ALTER USER $DB_USER PASSWORD '$DB_PASSWORD';
EOF

# 5. Grant privileges
echo "🔑 Granting privileges..."
sudo -u postgres psql << EOF
ALTER ROLE $DB_USER CREATEDB;
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF

# 6. Test connection
echo ""
echo "🧪 Testing connection..."
PGPASSWORD="$DB_PASSWORD" psql -h localhost -U "$DB_USER" -d "$DB_NAME" -c "\dt" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Connection test passed!"
else
    echo "⚠️  Connection test failed"
    echo "Check credentials and PostgreSQL is running:"
    echo "  sudo systemctl start postgresql"
fi

echo ""
echo "=========================================="
echo "✅ PostgreSQL setup completed!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Verify connection: PGPASSWORD=your_password psql -h localhost -U $DB_USER -d $DB_NAME"
echo "2. Run migrations: DJANGO_ENV=production python manage.py migrate"
echo "3. Create superuser: DJANGO_ENV=production python manage.py createsuperuser"
