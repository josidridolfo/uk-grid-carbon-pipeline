"""
Django settings for energy-project.ridol.fo (uk_grid_site).

All secrets and environment-specific values are read from environment variables
via django-environ. In production the .env file lives at /opt/energy-project/.env
on the Hetzner droplet. Locally, create web/.env from web/.env.example.

django-environ docs: https://django-environ.readthedocs.io/
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# django-environ setup
# ---------------------------------------------------------------------------
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    DJANGO_CSRF_TRUSTED_ORIGINS=(list, []),
)

# Read .env if present (local dev). Production passes env vars directly.
environ.Env.read_env(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Core security
# ---------------------------------------------------------------------------
# Required — raises ImproperlyConfigured if not set.
SECRET_KEY = env("DJANGO_SECRET_KEY")

DEBUG = env.bool("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    # Third-party
    "django_htmx",
    "markdownify.apps.MarkdownifyConfig",
    # Local
    "apps.core.apps.CoreConfig",
    "apps.blog.apps.BlogConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "uk_grid_site.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "uk_grid_site.wsgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# DATABASE_URL must be set; e.g. postgres://uk_grid_user:pass@db:5432/uk_grid_web
DATABASES = {
    "default": env.db("DATABASE_URL"),
}

# ---------------------------------------------------------------------------
# Cache — LocMemCache for Phase 1. Redis added in a later phase.
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "energy-project-default",
    }
}

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Whitenoise serves compressed static files efficiently without extra nginx config.
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ---------------------------------------------------------------------------
# Internationalisation (minimal — UK-centric project)
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-gb"
TIME_ZONE = "UTC"
USE_I18N = False
USE_TZ = True

# ---------------------------------------------------------------------------
# Default primary key type
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Markdownify — safe markdown rendering for blog posts
# Whitelist is intentionally narrow: structural HTML only.
# Scripts, iframes, and style attributes are never allowed.
# ---------------------------------------------------------------------------
MARKDOWNIFY = {
    "default": {
        "WHITELIST_TAGS": [
            "a",
            "abbr",
            "acronym",
            "b",
            "blockquote",
            "br",
            "code",
            "em",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "hr",
            "i",
            "li",
            "ol",
            "p",
            "pre",
            "strong",
            "table",
            "tbody",
            "td",
            "th",
            "thead",
            "tr",
            "ul",
        ],
        "WHITELIST_ATTRS": {
            "a": ["href", "title", "rel"],
            "abbr": ["title"],
            "acronym": ["title"],
            "td": ["align"],
            "th": ["align"],
            "code": ["class"],         # codehilite adds language classes
            "pre": ["class"],
        },
        "WHITELIST_PROTOCOLS": ["http", "https", "mailto"],
        "BLEACH": True,
        "MARKDOWN_EXTENSIONS": [
            "fenced_code",
            "tables",
            "codehilite",
            "toc",
        ],
        "MARKDOWN_EXTENSION_CONFIGS": {
            "codehilite": {
                "css_class": "highlight",
                "guess_lang": False,
            },
            "toc": {
                "permalink": True,
            },
        },
        "STRIP": False,
    }
}

# ---------------------------------------------------------------------------
# Snowflake connection config
# Used by apps/core/snowflake.py at request time, NOT at import time.
# Role must be REPORTER (read-only on ANALYTICS_MARTS). Never TRANSFORMER here.
# Phase 2 wires the actual queries; Phase 1c only sets up the config dict.
# All fields default to None so settings imports don't crash when Snowflake
# env vars are absent (e.g. during dbt parse or local frontend-only dev).
# ---------------------------------------------------------------------------
SNOWFLAKE_CONFIG = {
    "account": env.str("SNOWFLAKE_ACCOUNT", default=None),
    "user": env.str("SNOWFLAKE_USER", default=None),
    "password": env.str("SNOWFLAKE_PASSWORD", default=None),
    "role": env.str("SNOWFLAKE_ROLE", default="REPORTER"),
    "warehouse": env.str("SNOWFLAKE_WAREHOUSE", default="ENERGY_WH"),
    "database": env.str("SNOWFLAKE_DATABASE", default="UK_GRID"),
    # Schema is the dbt base schema + '_MARTS', e.g. ANALYTICS_MARTS
    "schema": env.str("SNOWFLAKE_DBT_SCHEMA", default="ANALYTICS") + "_MARTS",
}
