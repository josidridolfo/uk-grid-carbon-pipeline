#!/usr/bin/env bash
# ===========================================================================
# droplet-bootstrap.sh
# ===========================================================================
# Idempotent bootstrap for the DigitalOcean droplet that hosts
# energy-project.ridol.fo.
#
# Installs Docker engine, nginx (host-level reverse proxy), and certbot
# (Let's Encrypt SSL with automatic renewal), then provisions the nginx site
# config and SSL cert for energy-project.ridol.fo. Safe to re-run — every
# step checks state before acting.
#
# HOW TO USE
#   1. Point your Porkbun A record `energy-project.ridol.fo` at this droplet's
#      public IP. Wait for DNS to propagate (`dig energy-project.ridol.fo`).
#   2. Copy this repo to the droplet (e.g. /opt/energy-project) via git clone
#      or rsync.
#   3. Run as root: `sudo bash infra/droplet-bootstrap.sh`
#
# WHAT IT DOES
#   * apt update + install: ca-certificates, curl, gnupg, ufw, nginx, certbot,
#     python3-certbot-nginx, plus Docker engine + Compose plugin from
#     Docker's official apt repo.
#   * Enables docker.service + nginx.service via systemd.
#   * Drops infra/nginx/energy-project.ridol.fo.conf to
#     /etc/nginx/sites-available/, symlinks to sites-enabled/, reloads nginx.
#   * Opens UFW ports 22 (SSH), 80 (HTTP), 443 (HTTPS).
#   * Runs `certbot --nginx -d energy-project.ridol.fo` to provision the
#     Let's Encrypt cert. Detects existing cert and skips re-issue.
#   * Verifies `certbot.timer` is enabled (handles auto-renewal — no custom
#     script needed; certbot's systemd timer ships with the package).
#
# AUTOMATED CERT RENEWAL
#   Handled by certbot's systemd timer (`systemctl status certbot.timer`).
#   It runs twice a day, only renews when ≤30 days from expiry, and reloads
#   nginx automatically. No cron job required.
#
# IDEMPOTENCY
#   * apt-get install actions are skipped if package already present.
#   * Docker repo + gpg key drop are guarded with -f checks.
#   * UFW rules use `allow` (idempotent — repeats are no-ops).
#   * nginx symlink creation is `ln -sf`.
#   * certbot certificate-only command checks for an existing cert before
#     attempting issuance.
# ===========================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DOMAIN="${DOMAIN:-energy-project.ridol.fo}"
NGINX_SITE_CONF="energy-project.ridol.fo.conf"
LE_EMAIL="${LE_EMAIL:-}"    # set this to your email to receive expiry notices
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NGINX_SOURCE_CONF="$REPO_ROOT/infra/nginx/$NGINX_SITE_CONF"

# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------
if [[ "$EUID" -ne 0 ]]; then
    echo "Error: run as root (sudo bash $0)" >&2
    exit 1
fi

if [[ ! -f "$NGINX_SOURCE_CONF" ]]; then
    echo "Error: $NGINX_SOURCE_CONF not found. Are you running from the repo?" >&2
    exit 1
fi

echo "==> energy-project droplet bootstrap"
echo "    domain:        $DOMAIN"
echo "    nginx conf:    $NGINX_SOURCE_CONF"
echo "    LE email:      ${LE_EMAIL:-<unset, will use --register-unsafely-without-email>}"
echo

# ---------------------------------------------------------------------------
# apt + base packages
# ---------------------------------------------------------------------------
echo "==> [1/6] apt update + base packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
    ca-certificates \
    curl \
    gnupg \
    ufw \
    nginx \
    certbot \
    python3-certbot-nginx

# ---------------------------------------------------------------------------
# Docker engine + Compose plugin (official apt repo)
# ---------------------------------------------------------------------------
echo "==> [2/6] Docker engine + Compose plugin"
if ! command -v docker >/dev/null 2>&1; then
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    # shellcheck disable=SC1091
    . /etc/os-release
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $VERSION_CODENAME stable" \
        > /etc/apt/sources.list.d/docker.list

    apt-get update -qq
    apt-get install -y -qq \
        docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    systemctl enable --now docker
else
    echo "    docker already installed: $(docker --version)"
fi

# ---------------------------------------------------------------------------
# Firewall
# ---------------------------------------------------------------------------
echo "==> [3/6] UFW (firewall) — allow 22, 80, 443"
ufw allow 22/tcp   >/dev/null
ufw allow 80/tcp   >/dev/null
ufw allow 443/tcp  >/dev/null
# Only enable UFW if not already active — `ufw --force enable` does the right thing.
ufw status | grep -q "Status: active" || ufw --force enable

# ---------------------------------------------------------------------------
# nginx site config
# ---------------------------------------------------------------------------
echo "==> [4/6] nginx site config for $DOMAIN"
install -m 0644 "$NGINX_SOURCE_CONF" "/etc/nginx/sites-available/$NGINX_SITE_CONF"
ln -sf "/etc/nginx/sites-available/$NGINX_SITE_CONF" "/etc/nginx/sites-enabled/$NGINX_SITE_CONF"

# Strip the default nginx welcome site so $DOMAIN isn't shadowed.
if [[ -f /etc/nginx/sites-enabled/default ]]; then
    rm -f /etc/nginx/sites-enabled/default
fi

nginx -t
systemctl reload nginx

# ---------------------------------------------------------------------------
# SSL via certbot (idempotent — skips if cert already exists)
# ---------------------------------------------------------------------------
echo "==> [5/6] Let's Encrypt SSL"
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

# ---------------------------------------------------------------------------
# Auto-renewal — certbot.timer ships with the certbot package; just verify.
# ---------------------------------------------------------------------------
echo "==> [6/6] verifying certbot.timer is enabled"
systemctl enable --now certbot.timer
systemctl status certbot.timer --no-pager | head -3

echo
echo "✓ Bootstrap complete."
echo "  Next: copy/clone the repo to /opt/energy-project, populate /opt/energy-project/.env,"
echo "  then run: cd /opt/energy-project && docker compose -f web/docker-compose.yml up -d --build"
