import os
from datetime import datetime, timezone

from django.http import JsonResponse
from django.views.generic import TemplateView, View


class HomeView(TemplateView):
    """Landing page — UK Grid Carbon Intelligence."""

    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["now_utc"] = datetime.now(tz=timezone.utc)
        context["intensity_url"] = "/intensity/national/"
        return context


class HealthView(View):
    """
    Lightweight health endpoint used by Docker HEALTHCHECK and uptime monitors.
    No DB queries — the goal is a fast TCP-level liveness probe.
    Phase 2 can add a db_ok field once queries are wired.
    """

    def get(self, request, *args, **kwargs):
        return JsonResponse(
            {
                "status": "ok",
                "git_sha": os.environ.get("GIT_SHA", "unknown"),
                "service": "energy-project",
            }
        )
