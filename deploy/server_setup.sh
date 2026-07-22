#!/usr/bin/env bash
# Run this as root on the VPS (Ubuntu 24.04): fresh install of the Elkaed platform.
# Usage: bash server_setup.sh
set -euo pipefail

REPO_URL="https://github.com/mow-1/Elkaed"
APP_DIR="/opt/elkaed"
DOMAIN="elkaed.cloud"
WWW_DOMAIN="www.elkaed.cloud"
CERTBOT_EMAIL="mody.mostafa2018@gmail.com"

echo "==> Wiping any existing deployment state"
if command -v docker >/dev/null 2>&1; then
    docker ps -aq | xargs -r docker stop
    docker ps -aq | xargs -r docker rm
    docker system prune -af --volumes || true
fi
rm -rf "$APP_DIR"
rm -f /etc/nginx/sites-enabled/elkaed /etc/nginx/sites-available/elkaed

echo "==> Installing prerequisites"
apt-get update
apt-get install -y ca-certificates curl gnupg nginx certbot python3-certbot-nginx git ufw

# Docker
if ! command -v docker >/dev/null 2>&1; then
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

# Node.js 20 (for building the frontend)
if ! command -v node >/dev/null 2>&1; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
fi

echo "==> Firewall"
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "==> Cloning repository"
git clone "$REPO_URL" "$APP_DIR"
cd "$APP_DIR"

echo "==> Generating production secrets"
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")

cp deploy/env.prod.example .env.prod
sed -i "s#^SECRET_KEY=.*#SECRET_KEY=${SECRET_KEY}#" .env.prod
sed -i "s#^DB_PASSWORD=.*#DB_PASSWORD=${DB_PASSWORD}#" .env.prod

echo "==> Building frontend"
cd frontend
echo "VITE_API_URL=https://${DOMAIN}" > .env
npm ci
npm run build
cd "$APP_DIR"

echo "==> Building and starting containers"
docker compose --env-file .env.prod up -d --build

echo "==> Waiting for backend to become healthy"
for i in $(seq 1 30); do
    if docker compose exec -T backend python manage.py migrate --check >/dev/null 2>&1; then
        break
    fi
    sleep 2
done

echo "==> Creating test accounts"
docker compose exec -T backend python manage.py shell <<'PYEOF'
from apps.users.models import User
from apps.attendance.models import CenterGroup

if not User.objects.filter(phone='201000000000').exists():
    User.objects.create_superuser(phone='201000000000', password='Admin@12345',
                                   first_name='Admin', last_name='Test', email='admin@elkaed.local')

if not User.objects.filter(phone='201111111111').exists():
    User.objects.create_user(phone='201111111111', password='Student@123',
                              first_name='Test', last_name='Online Student',
                              email='student@elkaed.local', role='student',
                              student_type='online', academic_year='3rd')

group, _ = CenterGroup.objects.get_or_create(
    name_ar='Test Group', academic_year='3rd',
    defaults={'schedule_description': 'Sat & Tue 4-6 PM'})

if not User.objects.filter(phone='201222222222').exists():
    User.objects.create_user(phone='201222222222', password='Student@123',
                              first_name='Test', last_name='Center Student',
                              email='center.student@elkaed.local', role='student',
                              student_type='center', academic_year='3rd', group=group)
print("Test accounts ready")
PYEOF

echo "==> Configuring Nginx"
cp deploy/nginx.conf /etc/nginx/sites-available/elkaed
ln -sf /etc/nginx/sites-available/elkaed /etc/nginx/sites-enabled/elkaed
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo "==> Checking DNS before requesting a certificate"
SERVER_IP=$(curl -s https://api.ipify.org)
DOMAIN_IP=$(getent hosts "$DOMAIN" | awk '{print $1}' || true)

if [ "$DOMAIN_IP" = "$SERVER_IP" ]; then
    echo "==> DNS matches ($DOMAIN_IP) — requesting Let's Encrypt certificate"
    certbot --nginx -d "$DOMAIN" -d "$WWW_DOMAIN" --non-interactive --agree-tos -m "$CERTBOT_EMAIL" --redirect || \
        echo "Certbot failed — check DNS/domain and re-run: certbot --nginx -d $DOMAIN -d $WWW_DOMAIN"
else
    echo "==> DNS for $DOMAIN resolves to '${DOMAIN_IP:-<none>}', server is $SERVER_IP — skipping HTTPS cert."
    echo "    Point your DNS A record at $SERVER_IP, then run:"
    echo "    certbot --nginx -d $DOMAIN -d $WWW_DOMAIN"
fi

echo ""
echo "==================================================="
echo "Done. Site should be reachable at:"
echo "  http://$SERVER_IP/ (or https://$DOMAIN/ once DNS+cert are set up)"
echo ""
echo "Test accounts:"
echo "  Admin:           01000000000 / Admin@12345"
echo "  Online student:  01111111111 / Student@123"
echo "  Center student:  01222222222 / Student@123"
echo "==================================================="
