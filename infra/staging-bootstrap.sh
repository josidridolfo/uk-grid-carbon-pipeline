#!/usr/bin/env bash
# ============================================================================
# staging-bootstrap.sh
# ============================================================================
# Idempotent setup for the staging environment on the existing droplet.
# Assumes infra/droplet-bootstrap.sh has already been run (Docker, nginx,
# certbot, ufw all installed). This script adds:
#
#   - nginx site config for staging.energy-project.ridol.fo
#   - Let's Encrypt SSL cert for the staging hostname
#   - a stubbed /opt/energy-project/web/.env.staging if one doesn't exist
#
# Pre-requisites BEFORE running this:
#   1. DNS: at Porkbun, point staging.energy-project.ridol.fo at the droplet
#      (CNAME → energy-project.ridol.fo OR A record → droplet IP).
#      Wait for propagation: `dig +short staging.energy-project.ridol.fo`
#      must return the droplet IP.
#   2. infra/droplet-bootstrap.sh has already run successfully.
#
# AFTER this script completes:
#   1. Edit /opt/energy-project/web/.env.staging — populate
#      DJANGO_SECRET_KEY, POSTGRES_PASSWORD, DATABASE_URL, SNOWFLAKE_PASSWORD.
#   2. Trigger the deploy workflow:
#        gh workflow run deploy.yml --ref main
#      OR push any commit to main — the staging job runs first, prod gated.
#
# HOW TO RUN
#   sudo bash infra/staging-bootstrap.sh
#
# REQUIRED ROLE: root
#
# IDEMPOTENCY
#   - certbot detects existing certs and skips re-issuance
#   - nginx site config is `install -m 0644` (overwrites; safe)
#   - The .env.staging stub is created only if it doesn't already exist
# ============================================================================

set -euo pipefail

DOMAIN="${DOMAIN:-staging.energy-project.ridol.fo}"
NGINX_SITE_CONF="staging.energy-project.ridol.fo.conf"
LE_EMAIL="${LE_EMAIL:-}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NGINX_SOURCE_CONF="$REPO_ROOT/infra/nginx/$NGINX_SITE_CONF"
ENV_STAGING_PATH="$REPO_ROOT/web/.env.staging"

# ----------------------------------------------------------------------------
# Pre-flight
# ----------------------------------------------------------------------------
if [[ "$EUID" -ne 0 ]]; then
    echo "Error: run as root (sudo bash $0)" >&2
    exit 1
fi

if [[ ! -f "$NGINX_SOURCE_CONF" ]]; then
    echo "Error: $NGINX_SOURCE_CONF not found. Are you running from the repo?" >&2
    exit 1
fi

if ! command -v nginx >/dev/null 2>&1; then
    echo "Error: nginx not installed. Run infra/droplet-bootstrap.sh first." >&2
    exit 1
fi

if ! command -v certbot >/dev/null 2>&1; then
    echo "Error: certbot not installed. Run infra/droplet-bootstrap.sh first." >&2
    exit 1
fi

echo "==> staging environment bootstrap"
echo "    domain:        $DOMAIN"
echo "    nginx conf:    $NGINX_SOURCE_CONF"
echo "    LE email:      ${LE_EMAIL:-<unset>}"
echo

# ----------------------------------------------------------------------------
# DNS sanity check
# ----------------------------------------------------------------------------
echo "==> [1/4] DNS sanity check"
DROPLET_IP=$(curl -fsS ifconfig.me 2>/dev/null || echo "unknown")
RESOLVED_IP=$(dig +short "$DOMAIN" | tail -n1)
echo "    droplet public IP:       $DROPLET_IP"
echo "    $DOMAIN → $RESOLVED_IP"
if [[ -z "$RESOLVED_IP" ]]; then
    echo "    WARNING: DNS hasn't propagated yet. certbot will fail." >&2
    echo "    Add the Porkbun record + wait, then re-run this script." >&2
    exit 1
fi

# ----------------------------------------------------------------------------
# nginx site
# ----------------------------------------------------------------------------
echo "==> [2/4] nginx site config for $DOMAIN"
install -m 0644 "$NGINX_SOURCE_CONF" "/etc/nginx/sites-available/$NGINX_SITE_CONF"
ln -sf "/etc/nginx/sites-available/$NGINX_SITE_CONF" "/etc/nginx/sites-enabled/$NGINX_SITE_CONF"

nginx -t
if systemctl is-active --quiet nginx; then
    systemctl reload nginx
else
    systemctl enable --now nginx
fi

# ----------------------------------------------------------------------------
# SSL
# ----------------------------------------------------------------------------
echo "==> [3/4] Let's Encrypt SSL"
if certbot certificates 2>/dev/null | grep -q "Domains: $DOMAIN"; then
    echo "    cert for $DOMAIN already exists; skipping issuance"
else
    if [[ -n "$LE_EMAIL" ]]; then
        certbot --nginx --non-interactive --agree-tos --email "$LE_EMAIL" \
            -d "$DOMAIN" --redirect
    else
        certbot --nginx --non-interactive --agree-tos \
            --register-unsafely-without-email \
            -d "$DOMAIN" --redirect
    fi
fi

# ----------------------------------------------------------------------------
# .env.staging stub
# ----------------------------------------------------------------------------
echo "==> [4/4] .env.staging stub"
if [[ -f "$ENV_STAGING_PATH" ]]; then
    echo "    $ENV_STAGING_PATH already exists; leaving as-is"
else
    cp "$REPO_ROOT/web/.env.staging.example" "$ENV_STAGING_PATH"
    chmod 600 "$ENV_STAGING_PATH"
    echo "    stubbed $ENV_STAGING_PATH from .env.staging.example"
    echo "    NEXT STEP: edit this file and fill in DJANGO_SECRET_KEY,"
    echo "    POSTGRES_PASSWORD, DATABASE_URL, SNOWFLAKE_PASSWORD."
fi

echo
echo "✓ staging bootstrap complete."
echo "  Next:"
echo "    1. nano $ENV_STAGING_PATH  # fill in the secret values"
echo "    2. gh workflow run deploy.yml --ref main  # OR: push any commit to main"
echo "    3. Visit https://$DOMAIN/ once the deploy finishes"
