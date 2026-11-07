"""Root URL configuration: one prefix per REST API."""

from django.urls import include, path

urlpatterns = [
    path("api/ingestion/", include("ingestion.urls")),
    path("api/chat/", include("conversation.urls")),
]
