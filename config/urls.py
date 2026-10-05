"""URLs raíz del proyecto Django del laboratorio (etapa 03)."""

from django.urls import include, path

urlpatterns = [
    path("api/", include("activities.urls")),
]
