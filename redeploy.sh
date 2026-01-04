#!/bin/bash
# ==========================================
# RUANG DENGAR - Quick Redeploy Script
# ==========================================
# For servers that already have the app running
# Usage: bash redeploy.sh

set -e

echo "=========================================="
echo "🔄 RUANG DENGAR - Quick Redeploy"
echo "=========================================="
echo ""

# Configuration
PROJECT_DIR="/path/to/ruangdengar"  # EDIT THIS
VENV_DIR="$PROJECT_DIR/venv"
SERVICE_NAME="ruangdengar"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
   echo "⚠️  Warning: Not running as root. Some commands may require sudo."
fi

echo "📁 Project directory: $PROJECT_DIR"
echo ""

# Step 1: Pull latest code
echo -e "${BLUE}Step 1: Pulling latest code from Git...${NC}"
cd "$PROJECT_DIR"
git pull origin main
echo -e "${GREEN}✅ Code updated${NC}"

# Step 2: Activate venv and install dependencies
echo ""
echo -e "${BLUE}Step 2: Installing dependencies...${NC}"
source "$VENV_DIR/bin/activate"
pip install -r requirements.txt --quiet
echo -e "${GREEN}✅ Dependencies installed${NC}"

# Step 3: Run migrations
echo ""
echo -e "${BLUE}Step 3: Running database migrations...${NC}"
export DJANGO_ENV=production
python manage.py migrate
echo -e "${GREEN}✅ Migrations completed${NC}"

# Step 4: Collect static files
echo ""
echo -e "${BLUE}Step 4: Collecting static files...${NC}"
python manage.py collectstatic --noinput
echo -e "${GREEN}✅ Static files collected${NC}"

# Step 5: Reload Gunicorn
echo ""
echo -e "${BLUE}Step 5: Restarting Gunicorn service...${NC}"
sudo systemctl restart "$SERVICE_NAME"
sleep 2
echo -e "${GREEN}✅ Gunicorn restarted${NC}"

# Step 6: Reload Nginx
echo ""
echo -e "${BLUE}Step 6: Reloading Nginx...${NC}"
sudo systemctl reload nginx
echo -e "${GREEN}✅ Nginx reloaded${NC}"

# Step 7: Verify
echo ""
echo -e "${BLUE}Step 7: Verifying services...${NC}"
GUNICORN_STATUS=$(sudo systemctl is-active "$SERVICE_NAME")
NGINX_STATUS=$(sudo systemctl is-active nginx)

if [ "$GUNICORN_STATUS" = "active" ] && [ "$NGINX_STATUS" = "active" ]; then
    echo -e "${GREEN}✅ All services running${NC}"
else
    echo -e "${YELLOW}⚠️  Check service status:${NC}"
    sudo systemctl status "$SERVICE_NAME"
    sudo systemctl status nginx
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✅ Redeploy completed!${NC}"
echo "=========================================="
echo ""
echo "🔍 Check logs:"
echo "  tail -f /var/log/gunicorn/ruangdengar_error.log"
echo "  tail -f /var/log/nginx/ruangdengar_error.log"
echo ""
echo "🧪 Test application:"
echo "  curl https://your-domain.com"
echo ""
