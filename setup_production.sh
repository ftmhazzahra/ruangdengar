#!/bin/bash
# ==========================================
# RUANG DENGAR - Production Deployment Script
# ==========================================
# Usage: bash setup_production.sh

set -e  # Exit on error

echo "=========================================="
echo "🚀 Ruang Dengar - Production Setup"
echo "=========================================="
echo ""

# 1. Check if .env exists
if [ ! -f .env ]; then
    echo "❌ ERROR: .env file not found!"
    echo "Please create .env from .env.production.example"
    exit 1
fi

echo "✅ .env file found"

# 2. Check if virtual environment activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ ERROR: Virtual environment not activated!"
    echo "Please activate your virtual environment first:"
    echo "  source venv/bin/activate"
    exit 1
fi

echo "✅ Virtual environment activated: $VIRTUAL_ENV"

# 3. Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install -r requirements.txt --quiet

# 4. Set environment
export DJANGO_ENV=production

# 5. Run migrations
echo ""
echo "🗄️  Running database migrations..."
python manage.py migrate

# 6. Create logs directory
echo ""
echo "📁 Creating logs directory..."
mkdir -p logs
chmod 755 logs

# 7. Collect static files
echo ""
echo "📂 Collecting static files..."
python manage.py collectstatic --noinput

# 8. Check configuration
echo ""
echo "✅ Running Django checks..."
python manage.py check

# 9. Success message
echo ""
echo "=========================================="
echo "✅ Production setup completed!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Create superuser: python manage.py createsuperuser"
echo "2. Start gunicorn: gunicorn ruangdengar.wsgi:application --workers 4 --bind 0.0.0.0:8000"
echo "3. Setup nginx reverse proxy (see DEPLOYMENT_CHECKLIST.md)"
echo "4. Setup SSL certificate with Let's Encrypt"
echo ""
echo "Or follow complete guide: cat DEPLOYMENT_CHECKLIST.md"
