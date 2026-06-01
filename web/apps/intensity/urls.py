from django.urls import path

from . import views

app_name = "intensity"

urlpatterns = [
    path("national/", views.NationalIntensityView.as_view(), name="national"),
]
