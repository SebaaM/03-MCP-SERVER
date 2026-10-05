"""Rutas REST de la app de actividades."""

from django.urls import path

from activities import views

urlpatterns = [
    path("activities/", views.activity_list, name="activity-list"),
    path("activities/search/", views.activity_search, name="activity-search"),
    path("activities/<str:activity_id>/", views.activity_detail, name="activity-detail"),
    path(
        "activities/<str:activity_id>/register/",
        views.activity_register,
        name="activity-register",
    ),
]
