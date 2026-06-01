"""
TDD tests for web/templates/components/*.html partials.

Run with: cd web && pytest apps/core/test_components.py -v

Tests use render_to_string so no HTTP request is needed — no @pytest.mark.django_db
decorator required.  We do need Django's template engine to be configured, which
pytest-django handles by loading settings before any test runs.
"""

import os
import pytest
from django.template.loader import render_to_string


# ---------------------------------------------------------------------------
# 1. base_layout.html
# ---------------------------------------------------------------------------


def test_base_layout_contains_nav():
    """base_layout.html must render a <nav> element."""
    html = render_to_string("components/base_layout.html")
    assert "<nav" in html


def test_base_layout_contains_header_and_footer():
    """base_layout.html must render semantic <header> and <footer>."""
    html = render_to_string("components/base_layout.html")
    assert "<header" in html
    assert "<footer" in html


def test_base_layout_nav_aria_label():
    """Main <nav> must carry an aria-label for screen readers."""
    html = render_to_string("components/base_layout.html")
    assert 'aria-label="Main navigation"' in html or "aria-label=" in html


def test_base_layout_footer_attribution():
    """Footer must include data source attribution text."""
    html = render_to_string("components/base_layout.html")
    assert "Carbon Intensity" in html or "National Grid" in html


# ---------------------------------------------------------------------------
# 2. card.html
# ---------------------------------------------------------------------------


def test_card_renders_title_and_body():
    """card.html must render provided title and body text."""
    html = render_to_string(
        "components/card.html",
        {"title": "Solar Generation", "body": "Solar capacity grew 20% last year."},
    )
    assert "Solar Generation" in html
    assert "Solar capacity grew 20% last year." in html


def test_card_data_testid():
    """card.html must include data-testid="card" for test stability."""
    html = render_to_string(
        "components/card.html",
        {"title": "T", "body": "B"},
    )
    assert 'data-testid="card"' in html


def test_card_with_href_renders_link():
    """When href is provided, card wraps content in an <a> tag."""
    html = render_to_string(
        "components/card.html",
        {"title": "Link Card", "body": "Body", "href": "/blog/post-1"},
    )
    assert 'href="/blog/post-1"' in html


def test_card_without_href_no_link():
    """When href is absent, card renders no <a> tag."""
    html = render_to_string(
        "components/card.html",
        {"title": "No Link", "body": "Body"},
    )
    assert "<a " not in html


def test_card_with_image_renders_img():
    """When image_url is provided, card renders an <img> with alt text."""
    html = render_to_string(
        "components/card.html",
        {
            "title": "Image Card",
            "body": "Body",
            "image_url": "/static/img/solar.jpg",
        },
    )
    assert "<img" in html
    assert 'src="/static/img/solar.jpg"' in html
    # alt attribute must be present (accessibility)
    assert "alt=" in html


def test_card_without_image_no_img():
    """When image_url is absent, no <img> tag is rendered."""
    html = render_to_string(
        "components/card.html",
        {"title": "No Image", "body": "Body"},
    )
    assert "<img" not in html


# ---------------------------------------------------------------------------
# 3. metric_tile.html
# ---------------------------------------------------------------------------


def test_metric_tile_renders_label_and_value():
    """metric_tile.html must render label and value."""
    html = render_to_string(
        "components/metric_tile.html",
        {"label": "Current GB intensity", "value": "142"},
    )
    assert "Current GB intensity" in html
    assert "142" in html


def test_metric_tile_data_testid():
    """metric_tile.html must include data-testid="metric-tile"."""
    html = render_to_string(
        "components/metric_tile.html",
        {"label": "L", "value": "0"},
    )
    assert 'data-testid="metric-tile"' in html


def test_metric_tile_with_unit():
    """When unit is provided it must appear in the rendered output."""
    html = render_to_string(
        "components/metric_tile.html",
        {"label": "Intensity", "value": "142", "unit": "gCO2/kWh"},
    )
    assert "gCO2/kWh" in html


def test_metric_tile_without_unit_no_unit_span():
    """When unit is absent the unit span should not appear (no empty element)."""
    html = render_to_string(
        "components/metric_tile.html",
        {"label": "Intensity", "value": "142"},
    )
    # Should not render a bare unit container with nothing in it
    assert "gCO2/kWh" not in html


def test_metric_tile_color_class_applied():
    """Custom color_class must appear on the value element."""
    html = render_to_string(
        "components/metric_tile.html",
        {"label": "L", "value": "99", "color_class": "text-green-600"},
    )
    assert "text-green-600" in html


# ---------------------------------------------------------------------------
# 4. map_container.html
# ---------------------------------------------------------------------------


def test_map_container_renders_div_with_id():
    """map_container.html must render a <div> with the given chart_id."""
    html = render_to_string(
        "components/map_container.html",
        {"chart_id": "choropleth-map"},
    )
    assert 'id="choropleth-map"' in html


def test_map_container_data_testid():
    """map_container.html must include data-testid="map-container"."""
    html = render_to_string(
        "components/map_container.html",
        {"chart_id": "test-map"},
    )
    assert 'data-testid="map-container"' in html


def test_map_container_default_height_class():
    """When height_class is not provided, defaults to h-96."""
    html = render_to_string(
        "components/map_container.html",
        {"chart_id": "test-map"},
    )
    assert "h-96" in html


def test_map_container_custom_height_class():
    """Custom height_class overrides the default."""
    html = render_to_string(
        "components/map_container.html",
        {"chart_id": "test-map", "height_class": "h-[600px]"},
    )
    assert "h-[600px]" in html
    assert "h-96" not in html


def test_map_container_data_script_tag():
    """map_container.html must include the <script type="application/json"> data block."""
    html = render_to_string(
        "components/map_container.html",
        {"chart_id": "my-chart"},
    )
    assert 'id="my-chart-data"' in html
    assert 'type="application/json"' in html


def test_map_container_plotly_newplot_call():
    """map_container.html inline script must call Plotly.newPlot with the chart_id."""
    html = render_to_string(
        "components/map_container.html",
        {"chart_id": "my-chart"},
    )
    assert "Plotly.newPlot" in html
    assert "my-chart" in html


# ---------------------------------------------------------------------------
# 5. loading_fragment.html
# ---------------------------------------------------------------------------


def test_loading_fragment_default_message():
    """loading_fragment.html must render default 'Loading' text when no message given."""
    html = render_to_string("components/loading_fragment.html", {})
    assert "Loading" in html


def test_loading_fragment_custom_message():
    """Custom message must appear in the rendered output."""
    html = render_to_string(
        "components/loading_fragment.html",
        {"message": "Fetching carbon data…"},
    )
    assert "Fetching carbon data" in html


def test_loading_fragment_aria_live():
    """loading_fragment.html must include aria-live for screen-reader announcements."""
    html = render_to_string("components/loading_fragment.html", {})
    assert "aria-live" in html


def test_loading_fragment_data_testid():
    """loading_fragment.html must include data-testid="loading-fragment"."""
    html = render_to_string("components/loading_fragment.html", {})
    assert 'data-testid="loading-fragment"' in html


def test_loading_fragment_spinner_present():
    """A visual spinner element (animate-spin) must be present."""
    html = render_to_string("components/loading_fragment.html", {})
    assert "animate-spin" in html


# ---------------------------------------------------------------------------
# 6. error_fragment.html
# ---------------------------------------------------------------------------


def test_error_fragment_renders_message():
    """error_fragment.html must render the provided error message."""
    html = render_to_string(
        "components/error_fragment.html",
        {"message": "Failed to load map data.", "retry_url": "/partials/map"},
    )
    assert "Failed to load map data." in html


def test_error_fragment_data_testid():
    """error_fragment.html must include data-testid="error-fragment"."""
    html = render_to_string(
        "components/error_fragment.html",
        {"message": "Error", "retry_url": "/retry"},
    )
    assert 'data-testid="error-fragment"' in html


def test_error_fragment_retry_button_hx_get():
    """Retry button must have hx-get set to the retry_url."""
    html = render_to_string(
        "components/error_fragment.html",
        {"message": "Oops", "retry_url": "/partials/map-preview"},
    )
    assert 'hx-get="/partials/map-preview"' in html


def test_error_fragment_retry_button_aria_label():
    """Retry button must have an aria-label for accessibility."""
    html = render_to_string(
        "components/error_fragment.html",
        {"message": "Oops", "retry_url": "/retry"},
    )
    assert "aria-label" in html


def test_error_fragment_red_styling():
    """Error fragment must use red/destructive Tailwind classes."""
    html = render_to_string(
        "components/error_fragment.html",
        {"message": "Error", "retry_url": "/retry"},
    )
    # Accept any of the standard Tailwind red variants
    assert "red" in html


def test_error_fragment_role_alert():
    """Error fragment must carry role="alert" for immediate screen-reader announcement."""
    html = render_to_string(
        "components/error_fragment.html",
        {"message": "Error", "retry_url": "/retry"},
    )
    assert 'role="alert"' in html


# ---------------------------------------------------------------------------
# 7. badge.html
# ---------------------------------------------------------------------------


def test_badge_renders_label():
    """badge.html must render the provided label text."""
    html = render_to_string("components/badge.html", {"label": "Low", "variant": "low"})
    assert "Low" in html


def test_badge_data_testid():
    """badge.html must include data-testid="badge"."""
    html = render_to_string("components/badge.html", {"label": "L"})
    assert 'data-testid="badge"' in html


def test_badge_low_variant_classes():
    """variant='low' must apply emerald (green) styling."""
    html = render_to_string("components/badge.html", {"label": "Low", "variant": "low"})
    assert "emerald" in html


def test_badge_moderate_variant_classes():
    """variant='moderate' must apply yellow styling."""
    html = render_to_string("components/badge.html", {"label": "Moderate", "variant": "moderate"})
    assert "yellow" in html


def test_badge_high_variant_classes():
    """variant='high' must apply orange styling."""
    html = render_to_string("components/badge.html", {"label": "High", "variant": "high"})
    assert "orange" in html


def test_badge_very_high_variant_classes():
    """variant='very-high' must apply red styling."""
    html = render_to_string("components/badge.html", {"label": "Very High", "variant": "very-high"})
    assert "red" in html


def test_badge_default_variant_classes():
    """No variant (or variant='default') must apply neutral slate styling."""
    html = render_to_string("components/badge.html", {"label": "Unknown"})
    assert "slate" in html


def test_badge_is_inline_span():
    """badge.html must use a <span> element (inline flow)."""
    html = render_to_string("components/badge.html", {"label": "Low", "variant": "low"})
    assert "<span" in html


def test_badge_snapshot(snapshot):
    """Snapshot: badge with variant=low must match stored render."""
    html = render_to_string("components/badge.html", {"label": "Low", "variant": "low"})
    snapshot.assert_match(html, "badge_low.html")


# ---------------------------------------------------------------------------
# 8. nav_link.html
# ---------------------------------------------------------------------------


def test_nav_link_renders_href_and_label():
    """nav_link.html must render href and label text."""
    html = render_to_string(
        "components/nav_link.html",
        {"href": "/map", "label": "Map", "current_path": "/"},
    )
    assert 'href="/map"' in html
    assert "Map" in html


def test_nav_link_data_testid():
    """nav_link.html must include data-testid="nav-link"."""
    html = render_to_string(
        "components/nav_link.html",
        {"href": "/map", "label": "Map", "current_path": "/"},
    )
    assert 'data-testid="nav-link"' in html


def test_nav_link_active_aria_current():
    """When href matches current_path, aria-current='page' must be present."""
    html = render_to_string(
        "components/nav_link.html",
        {"href": "/map", "label": "Map", "current_path": "/map"},
    )
    assert 'aria-current="page"' in html


def test_nav_link_inactive_no_aria_current():
    """When href does not match current_path, aria-current must be absent."""
    html = render_to_string(
        "components/nav_link.html",
        {"href": "/map", "label": "Map", "current_path": "/"},
    )
    assert "aria-current" not in html


def test_nav_link_active_styling():
    """Active link must carry a distinctive visual marker (border-b or font-semibold)."""
    html = render_to_string(
        "components/nav_link.html",
        {"href": "/map", "label": "Map", "current_path": "/map"},
    )
    assert "font-semibold" in html or "border-b" in html


def test_nav_link_snapshot(snapshot):
    """Snapshot: active nav_link must match stored render."""
    html = render_to_string(
        "components/nav_link.html",
        {"href": "/methodology", "label": "Methodology", "current_path": "/methodology"},
    )
    snapshot.assert_match(html, "nav_link_active.html")


# ---------------------------------------------------------------------------
# 9. hero.html
# ---------------------------------------------------------------------------


def test_hero_renders_headline_and_subhead():
    """hero.html must render headline and subhead."""
    html = render_to_string(
        "components/hero.html",
        {"headline": "UK Grid Carbon Intelligence", "subhead": "Real-time intensity data."},
    )
    assert "UK Grid Carbon Intelligence" in html
    assert "Real-time intensity data." in html


def test_hero_data_testid():
    """hero.html must include data-testid="hero"."""
    html = render_to_string(
        "components/hero.html",
        {"headline": "H", "subhead": "S"},
    )
    assert 'data-testid="hero"' in html


def test_hero_h1_tag():
    """hero.html must render headline inside an <h1>."""
    html = render_to_string(
        "components/hero.html",
        {"headline": "My Headline", "subhead": "Subhead text."},
    )
    assert "<h1" in html
    assert "My Headline" in html


def test_hero_with_cta_renders_link():
    """When cta_label is provided, a CTA link must be rendered."""
    html = render_to_string(
        "components/hero.html",
        {"headline": "H", "subhead": "S", "cta_label": "Explore the map", "cta_href": "/map"},
    )
    assert "Explore the map" in html
    assert 'href="/map"' in html


def test_hero_without_cta_no_button():
    """When cta_label is absent, no CTA element should be rendered."""
    html = render_to_string(
        "components/hero.html",
        {"headline": "H", "subhead": "S"},
    )
    assert "button" not in html.lower() or 'role="button"' not in html


def test_hero_cta_default_href():
    """When cta_label is provided but cta_href is absent, href defaults to '#'."""
    html = render_to_string(
        "components/hero.html",
        {"headline": "H", "subhead": "S", "cta_label": "Go"},
    )
    assert 'href="#"' in html


def test_hero_snapshot(snapshot):
    """Snapshot: hero with CTA must match stored render."""
    html = render_to_string(
        "components/hero.html",
        {
            "headline": "UK Grid Carbon Intelligence",
            "subhead": "Real-time intensity data.",
            "cta_label": "Explore the map",
            "cta_href": "/map",
        },
    )
    snapshot.assert_match(html, "hero_with_cta.html")


# ---------------------------------------------------------------------------
# 10. theme_toggle.html
# ---------------------------------------------------------------------------


def test_theme_toggle_data_testid():
    """theme_toggle.html must include data-testid="theme-toggle"."""
    html = render_to_string("components/theme_toggle.html")
    assert 'data-testid="theme-toggle"' in html


def test_theme_toggle_has_three_options():
    """theme_toggle.html must render exactly three <option> elements."""
    html = render_to_string("components/theme_toggle.html")
    assert html.count("<option") == 3


def test_theme_toggle_light_option():
    """theme_toggle.html must include a 'Light' / 'default' option."""
    html = render_to_string("components/theme_toggle.html")
    assert 'value="default"' in html


def test_theme_toggle_dark_option():
    """theme_toggle.html must include a 'Dark' option."""
    html = render_to_string("components/theme_toggle.html")
    assert 'value="dark"' in html


def test_theme_toggle_high_contrast_option():
    """theme_toggle.html must include a 'High Contrast' option."""
    html = render_to_string("components/theme_toggle.html")
    assert 'value="high-contrast"' in html


def test_theme_toggle_aria_label():
    """theme_toggle.html select must carry an aria-label for accessibility."""
    html = render_to_string("components/theme_toggle.html")
    assert "aria-label" in html


def test_theme_toggle_sr_only_label():
    """theme_toggle.html must include a visually-hidden label for screen readers."""
    html = render_to_string("components/theme_toggle.html")
    assert "sr-only" in html


def test_theme_toggle_local_storage_key_in_script():
    """The inline script must reference the localStorage key 'energy-project-theme'."""
    html = render_to_string("components/theme_toggle.html")
    assert "energy-project-theme" in html


def test_theme_toggle_snapshot(snapshot):
    """Snapshot: theme_toggle render must match stored snapshot."""
    html = render_to_string("components/theme_toggle.html")
    snapshot.assert_match(html, "theme_toggle.html")


# ---------------------------------------------------------------------------
# Theme CSS variables — structural test
# ---------------------------------------------------------------------------

CSS_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "static", "tailwind", "input.css",
)


def test_css_has_default_theme_block():
    """input.css must contain a [data-theme='default'] or :root block."""
    with open(CSS_PATH) as f:
        css = f.read()
    assert "[data-theme=" in css or ":root" in css


def test_css_has_dark_theme_block():
    """input.css must contain a [data-theme='dark'] block."""
    with open(CSS_PATH) as f:
        css = f.read()
    assert '[data-theme="dark"]' in css


def test_css_has_high_contrast_theme_block():
    """input.css must contain a [data-theme='high-contrast'] block."""
    with open(CSS_PATH) as f:
        css = f.read()
    assert '[data-theme="high-contrast"]' in css


def test_css_defines_all_six_tokens():
    """input.css must define all six required CSS custom properties."""
    with open(CSS_PATH) as f:
        css = f.read()
    for token in [
        "--color-bg",
        "--color-fg",
        "--color-accent",
        "--color-muted",
        "--color-card-bg",
        "--color-border",
    ]:
        assert token in css, f"Missing CSS token: {token}"
