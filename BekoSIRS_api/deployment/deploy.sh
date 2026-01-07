#!/bin/bash
# BekoSIRS Backend Deployment Script
# Usage: ./deploy.sh [production|staging]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-production}
APP_DIR="/var/www/bekosirs/BekoSIRS_api"
VENV_DIR="/var/www/bekosirs/venv"
USER="bekosirs"
LOG_DIR="/var/log/bekosirs"

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}BekoSIRS Backend Deployment - ${ENVIRONMENT}${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Check if running as correct user
if [ "$(whoami)" != "$USER" ] && [ "$(whoami)" != "root" ]; then
    echo -e "${RED}Error: Must run as $USER or root${NC}"
    exit 1
fi

# Step 1: Pull latest code
echo -e "\n${YELLOW}[1/10] Pulling latest code...${NC}"
cd $APP_DIR
git pull origin main

# Step 2: Activate virtual environment
echo -e "\n${YELLOW}[2/10] Activating virtual environment...${NC}"
source $VENV_DIR/bin/activate

# Step 3: Install/update dependencies
echo -e "\n${YELLOW}[3/10] Installing dependencies...${NC}"
pip install -r requirements.txt --quiet

# Step 4: Collect static files
echo -e "\n${YELLOW}[4/10] Collecting static files...${NC}"
python manage.py collectstatic --noinput

# Step 5: Run database migrations
echo -e "\n${YELLOW}[5/10] Running database migrations...${NC}"
python manage.py migrate --noinput

# Step 6: Check deployment settings
echo -e "\n${YELLOW}[6/10] Checking deployment configuration...${NC}"
python manage.py check --deploy --fail-level WARNING

# Step 7: Clear cache
echo -e "\n${YELLOW}[7/10] Clearing cache...${NC}"
python manage.py shell << EOF
from django.core.cache import cache
cache.clear()
print("Cache cleared successfully")
EOF

# Step 8: Restart Gunicorn
echo -e "\n${YELLOW}[8/10] Restarting Gunicorn...${NC}"
sudo systemctl restart bekosirs

# Step 9: Wait for service to start
echo -e "\n${YELLOW}[9/10] Waiting for service to start...${NC}"
sleep 3

# Step 10: Check service status
echo -e "\n${YELLOW}[10/10] Checking service status...${NC}"
if sudo systemctl is-active --quiet bekosirs; then
    echo -e "${GREEN}✓ BekoSIRS service is running${NC}"
else
    echo -e "${RED}✗ BekoSIRS service failed to start${NC}"
    echo -e "${YELLOW}Checking logs:${NC}"
    sudo journalctl -u bekosirs -n 20 --no-pager
    exit 1
fi

# Health check
echo -e "\n${YELLOW}Performing health check...${NC}"
HEALTH_URL="http://localhost:8000/api/v1/"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ "$HTTP_STATUS" -eq 200 ] || [ "$HTTP_STATUS" -eq 301 ]; then
    echo -e "${GREEN}✓ Health check passed (HTTP $HTTP_STATUS)${NC}"
else
    echo -e "${RED}✗ Health check failed (HTTP $HTTP_STATUS)${NC}"
    exit 1
fi

echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Deployment completed successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Show recent logs
echo -e "\n${YELLOW}Recent logs:${NC}"
sudo journalctl -u bekosirs -n 10 --no-pager

echo -e "\n${YELLOW}Useful commands:${NC}"
echo -e "  View logs:     sudo journalctl -u bekosirs -f"
echo -e "  Restart:       sudo systemctl restart bekosirs"
echo -e "  Status:        sudo systemctl status bekosirs"
