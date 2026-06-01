# ============================================================================
# Stage 1 — Tailwind CSS build
# Compiles static/tailwind/input.css → static/css/tailwind.css (minified).
# The compiled file is copied into Stage 2; node_modules never reach prod.
# ============================================================================
FROM node:20-alpine AS tailwind-build

WORKDIR /build/static/tailwind

# Copy only the files needed for the npm install + build step.
# This layer is cached as long as package.json, config, and input.css don't change.
COPY static/tailwind/package.json static/tailwind/package-lock.json ./
RUN npm ci --prefer-offline

COPY static/tailwind/tailwind.config.js ./
COPY static/tailwind/input.css ./
# Templates must be present so Tailwind's content scan purges unused classes.
COPY templates/ /build/templates/

RUN npx tailwindcss -i input.css -o ../css/tailwind.css --minify


# ============================================================================
# Stage 2 — Python / Gunicorn runtime
# Non-root user `app`. Entrypoint: migrate → collectstatic → gunicorn.
# ============================================================================
FROM python:3.13-slim AS runtime

# Build-arg for embedding git SHA in the health endpoint response.
ARG GIT_SHA=unknown
ENV GIT_SHA=${GIT_SHA}

# System deps: curl for HEALTHCHECK; libpq for psycopg; build-essential for
# any compiled Python wheels (e.g. snowflake-connector C extensions).
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    build-essential \
    libpq-dev \
  && rm -rf /var/lib/apt/lists/*

# Create a non-root user.
RUN groupadd --gid 1001 app \
 && useradd --uid 1001 --gid app --create-home --home-dir /home/app --shell /bin/bash app \
 && chown app:app /home/app

WORKDIR /app

# Copy Python package descriptor and install deps via pip (no uv in container —
# pip is simpler and the image is built once, not synced repeatedly).
COPY pyproject.toml ./
# Hatchling needs a README to satisfy the build; create a minimal placeholder.
COPY README.md ./
RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir .

# Copy compiled Tailwind CSS from Stage 1.
COPY --from=tailwind-build /build/static/css ./static/css

# Copy application source.
COPY manage.py ./
COPY uk_grid_site/ ./uk_grid_site/
COPY apps/ ./apps/
COPY templates/ ./templates/
COPY static/ ./static/

# collectstatic writes into staticfiles/ — this dir must be writable by app user.
RUN mkdir -p staticfiles && chown -R app:app /app

USER app

# Collect static assets (requires SECRET_KEY to be available; passed at build
# or via --build-arg; a dummy value is fine for collectstatic).
ENV DJANGO_SECRET_KEY=collectstatic-placeholder-not-used-at-runtime
ENV DATABASE_URL=sqlite://:memory:
RUN python manage.py collectstatic --noinput

# Reset env vars — real values come from env_file at runtime.
ENV DJANGO_SECRET_KEY=""
ENV DATABASE_URL=""

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Entrypoint: migrate then start gunicorn.
# migrate --noinput is idempotent; running it on startup means zero-downtime
# deploys work without a separate migration job in Phase 1.
ENTRYPOINT ["/bin/sh", "-c", \
  "python manage.py migrate --noinput && \
   gunicorn uk_grid_site.wsgi:application \
     --bind 0.0.0.0:8000 \
     --workers 3 \
     --access-logfile - \
     --error-logfile -"]
