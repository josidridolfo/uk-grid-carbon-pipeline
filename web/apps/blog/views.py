"""
apps/blog/views.py

Blog index (ListView pattern) and post detail.
Posts are loaded from disk via apps.blog.loader — no database model.
"""

from django.core.paginator import Paginator
from django.http import Http404
from django.views.generic import TemplateView

from .loader import get_post_by_slug, load_posts

POSTS_PER_PAGE = 10


class BlogIndexView(TemplateView):
    """
    /blog/  — list of all posts, newest first, paginated 10/page.
    """

    template_name = "blog/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_posts = load_posts()
        paginator = Paginator(all_posts, POSTS_PER_PAGE)
        page_number = self.request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)
        context["page_obj"] = page_obj
        context["posts"] = page_obj.object_list
        return context


class BlogDetailView(TemplateView):
    """
    /blog/<slug>/  — single post detail page.
    """

    template_name = "blog/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs["slug"]
        post = get_post_by_slug(slug)
        if post is None:
            raise Http404(f"No blog post found with slug: {slug!r}")
        context["post"] = post
        return context
