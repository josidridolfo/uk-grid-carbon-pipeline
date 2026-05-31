---
name: hosting-decision
description: Hetzner CX22 + Caddy + Docker Compose chosen for energy-project.ridol.fo; Fly.io/Railway/Render rejected
metadata:
  type: project
---

Hosting: Hetzner CX22 (4GB RAM, 2 vCPU, ~$5/mo) + Caddy as reverse proxy + Docker Compose. Custom subdomain `energy-project.ridol.fo` via CNAME record on `ridol.fo` pointing to Hetzner IPv4. Caddy auto-provisions Let's Encrypt SSL.

Secrets on server: `.env` file on the Hetzner box only, referenced by `docker-compose.yml` via `env_file`. Never committed to git. Listed in `.gitignore` and `.dockerignore`. Snowflake private key mounted as read-only bind mount.

Key rotation story: generate new RSA key pair, upload public key to Snowflake (`ALTER USER`), update `.env` on server, `docker compose up -d` to restart.

**Why:** No cold starts (unlike Render free tier). No managed-platform pricing jumps (Fly/Railway paid tiers start at $15+). Full server control simplifies Docker Compose bind mounts for the key file. Caddy makes SSL trivial. $5/mo fits hobby project budget.

**How to apply:** Do not suggest Fly.io, Railway, Render, or DigitalOcean App Platform for this project. The deploy workflow is: push to git, SSH to Hetzner, `git pull && docker compose up -d --build`.

Related: [[dashboard-stack]], [[data-access-pattern]]
