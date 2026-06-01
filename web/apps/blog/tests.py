"""
TDD tests for apps.blog — loader, views, and markdown rendering.

Run with: cd web && pytest apps/blog/tests.py -v

Tests are ordered from unit (loader) through integration (views) following
the TDD progression: write tests first, then implement.
"""

import textwrap
from datetime import date
from pathlib import Path

import pytest
from django.template.loader import render_to_string
from django.test import Client


# ---------------------------------------------------------------------------
# Loader tests — unit level (no HTTP, no DB)
# ---------------------------------------------------------------------------


def test_loader_parses_frontmatter_and_body():
    """
    _parse_post_string() must return a Post with all frontmatter fields
    populated and the markdown body preserved as a string.
    """
    from apps.blog.loader import _parse_post_string

    raw = textwrap.dedent("""\
        ---
        title: Test Post Title
        slug: test-post-title
        published_at: 2026-05-01
        description: A short description for the index card.
        tags: [methodology, infrastructure]
        ---

        ## Hello

        This is the body.
    """)

    post = _parse_post_string(raw)

    assert post.title == "Test Post Title"
    assert post.slug == "test-post-title"
    assert post.published_at == date(2026, 5, 1)
    assert post.description == "A short description for the index card."
    assert "methodology" in post.tags
    assert "infrastructure" in post.tags
    assert "## Hello" in post.body
    assert "This is the body." in post.body


def test_loader_reads_all_posts_from_content_dir():
    """
    load_posts() must read *.md files from web/content/blog/,
    return at least 2 Post objects, sorted newest-first by published_at.
    """
    from apps.blog.loader import load_posts

    posts = load_posts()

    assert len(posts) >= 2
    # Sorted newest first
    dates = [p.published_at for p in posts]
    assert dates == sorted(dates, reverse=True)


def test_loader_post_slug_unique():
    """Every post loaded from disk must have a unique slug."""
    from apps.blog.loader import load_posts

    posts = load_posts()
    slugs = [p.slug for p in posts]
    assert len(slugs) == len(set(slugs)), "Duplicate slugs found in content/blog/"


def test_loader_tags_default_to_empty_list():
    """
    A post with no tags key in frontmatter must have tags defaulting to [].
    """
    from apps.blog.loader import _parse_post_string

    raw = textwrap.dedent("""\
        ---
        title: No Tags
        slug: no-tags
        published_at: 2026-01-01
        description: A post with no tags.
        ---

        Body here.
    """)

    post = _parse_post_string(raw)
    assert post.tags == []


# ---------------------------------------------------------------------------
# View tests — HTTP level (requires @pytest.mark.django_db)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_blog_index_returns_200_and_lists_posts(client):
    """
    GET /blog/ must return 200 and include both post titles in the HTML body.
    """
    response = client.get("/blog/")
    assert response.status_code == 200
    content = response.content.decode()
    # Both post titles must appear somewhere in the page
    assert "Building a UK grid carbon intelligence platform" in content
    assert "Carbon Intensity API and the NESO DNO GeoJSON" in content


@pytest.mark.django_db
def test_blog_index_uses_correct_template(client):
    """Blog index must render blog/index.html."""
    response = client.get("/blog/")
    assert response.status_code == 200
    template_names = [t.name for t in response.templates]
    assert "blog/index.html" in template_names


@pytest.mark.django_db
def test_blog_detail_returns_200_for_existing_slug(client):
    """GET /blog/<known-slug>/ must return 200 and include the post title."""
    response = client.get("/blog/building-uk-grid-carbon-intelligence-phase-1/")
    assert response.status_code == 200
    content = response.content.decode()
    assert "Building a UK grid carbon intelligence platform" in content


@pytest.mark.django_db
def test_blog_detail_returns_404_for_unknown_slug(client):
    """GET /blog/<nonexistent-slug>/ must return 404."""
    response = client.get("/blog/nonexistent-slug-that-does-not-exist/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_blog_detail_uses_correct_template(client):
    """Blog detail must render blog/detail.html."""
    response = client.get("/blog/building-uk-grid-carbon-intelligence-phase-1/")
    assert response.status_code == 200
    template_names = [t.name for t in response.templates]
    assert "blog/detail.html" in template_names


@pytest.mark.django_db
def test_blog_detail_markdown_renders_code_blocks(client):
    """
    Markdown fenced code blocks must be rendered as <pre><code> HTML.
    The post content includes code snippets, so this verifies markdown
    is actually processed (not shown raw).
    """
    response = client.get("/blog/building-uk-grid-carbon-intelligence-phase-1/")
    assert response.status_code == 200
    content = response.content.decode()
    assert "<pre>" in content or "<code>" in content


@pytest.mark.django_db
def test_blog_index_pagination_context(client):
    """Blog index view must expose a page_obj in context for pagination."""
    response = client.get("/blog/")
    assert response.status_code == 200
    assert "page_obj" in response.context


# ---------------------------------------------------------------------------
# Component tests — post_meta.html
# ---------------------------------------------------------------------------


def test_post_meta_renders_date():
    """post_meta.html must render the published_at date."""
    html = render_to_string(
        "components/post_meta.html",
        {"published_at": date(2026, 5, 31), "tags": []},
    )
    assert "2026" in html
    assert "May" in html or "05" in html or "31" in html


def test_post_meta_renders_tags():
    """post_meta.html must render each tag as a badge."""
    html = render_to_string(
        "components/post_meta.html",
        {"published_at": date(2026, 5, 31), "tags": ["methodology", "dbt"]},
    )
    assert "methodology" in html
    assert "dbt" in html


def test_post_meta_data_testid():
    """post_meta.html must include data-testid='post-meta'."""
    html = render_to_string(
        "components/post_meta.html",
        {"published_at": date(2026, 5, 31), "tags": []},
    )
    assert 'data-testid="post-meta"' in html


def test_post_meta_no_tags_renders_no_badge_elements():
    """With an empty tags list, no badge spans should appear."""
    html = render_to_string(
        "components/post_meta.html",
        {"published_at": date(2026, 5, 31), "tags": []},
    )
    # badge component uses data-testid="badge" — none should be present
    assert 'data-testid="badge"' not in html
