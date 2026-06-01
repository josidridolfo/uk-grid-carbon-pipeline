from django.urls import include, path

urlpatterns = [
    path("", include("apps.core.urls")),
    path("blog/", include("apps.blog.urls", namespace="blog")),
]
