#!/bin/bash
# ==========================================
# RUANG DENGAR - Development Setup Script
# ==========================================
# Usage: bash setup_dev.sh

set -e

echo "=========================================="
echo "💻 Ruang Dengar - Development Setup"
echo "=========================================="
echo ""

# 1. Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "✅ Virtual environment ready"

# 2. Activate virtual environment
echo ""
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# 3. Install dependencies
echo ""
echo "📥 Installing dependencies..."
pip install -r requirements.txt --quiet

echo "✅ Dependencies installed"

# 4. Create .env if not exists
if [ ! -f .env ]; then
    echo ""
    echo "📝 Creating .env file..."
    cat > .env << 'EOF'
DJANGO_ENV=development
DEBUG=True
SECRET_KEY=dev-secret-key-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1
EOF
    echo "✅ .env created (for development only)"
fi

# 5. Run migrations
echo ""
echo "🗄️  Running migrations..."
python manage.py migrate

# 6. Create superuser prompt
echo ""
echo "👤 Create superuser account for /admin:"
python manage.py createsuperuser

# 7. Success message
echo ""
echo "=========================================="
echo "✅ Development setup completed!"
echo "=========================================="
echo ""
echo "To start development server:"
echo "  python manage.py runserver"
echo ""
echo "Then access:"
echo "  - Main site: http://localhost:8000"
echo "  - Admin: http://localhost:8000/admin"
