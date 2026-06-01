"""
apps/blog/loader.py

Loads blog posts from web/content/blog/*.md files at request time.
Posts are plain markdown with YAML frontmatter; no database table is used.

Data contract:
  - Files live at BASE_DIR/../content/blog/*.md
    (i.e. web/content/blog/*.md relative to the repo root)
  - Required frontmatter keys: title, slug, published_at, description
  - Optional frontmatter keys: tags (list, defaults to [])
  - Body: everything after the closing --- delimiter

Designed for on-demand reads — content is small (<100 posts expected)
and OS-level file caching makes repeated reads cheap. If profiling shows
this is a bottleneck, add Django cache.get/set around load_posts().
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import frontmatter  # python-frontmatter

logger = logging.getLogger(__name__)

# Resolve the content directory relative to this file's location:
# web/apps/blog/loader.py  →  web/content/blog/
_CONTENT_DIR = Path(__file__).resolve().parent.parent.parent / "content" / "blog"


@dataclass(frozen=True)
class Post:
    """Immutable value object representing a parsed blog post."""

    title: str
    slug: str
    published_at: date
    description: str
    body: str
    tags: list[str] = field(default_factory=list)

    def __hash__(self) -> int:
        # frozen=True requires hashable fields; list is not hashable by default.
        # Override to hash on slug (unique per post).
        return hash(self.slug)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Post):
            return NotImplemented
        return self.slug == other.slug


def _parse_post_string(raw: str) -> Post:
    """
    Parse a raw markdown string (with YAML frontmatter) into a Post.

    Raises ValueError if required frontmatter keys are missing.
    """
    parsed = frontmatter.loads(raw)
    meta = parsed.metadata

    # Validate required keys
    for key in ("title", "slug", "published_at", "description"):
        if key not in meta:
            raise ValueError(f"Blog post frontmatter missing required key: {key!r}")

    # published_at may come back as a datetime.date or datetime.datetime
    pub = meta["published_at"]
    if hasattr(pub, "date"):
        pub = pub.date()

    return Post(
        title=str(meta["title"]),
        slug=str(meta["slug"]),
        published_at=pub,
        description=str(meta["description"]),
        body=parsed.content,
        tags=list(meta.get("tags", [])),
    )


def _load_post_from_file(path: Path) -> Post | None:
    """
    Read and parse a single .md file. Returns None on parse error
    (logged as a warning) so one bad file doesn't break the whole index.
    """
    try:
        raw = path.read_text(encoding="utf-8")
        return _parse_post_string(raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to parse blog post %s: %s", path, exc)
        return None


def load_posts(content_dir: Path | None = None) -> list[Post]:
    """
    Load all *.md files from the content directory and return them
    sorted by published_at descending (newest first).

    Args:
        content_dir: Override the default content directory. Used in tests.
    """
    directory = content_dir or _CONTENT_DIR

    if not directory.exists():
        logger.warning("Blog content directory does not exist: %s", directory)
        return []

    posts: list[Post] = []
    for path in sorted(directory.glob("*.md")):
        post = _load_post_from_file(path)
        if post is not None:
            posts.append(post)

    return sorted(posts, key=lambda p: p.published_at, reverse=True)


def get_post_by_slug(slug: str, content_dir: Path | None = None) -> Post | None:
    """
    Return the Post with the given slug, or None if not found.
    Iterates load_posts() — fine at this scale.
    """
    for post in load_posts(content_dir=content_dir):
        if post.slug == slug:
            return post
    return None
