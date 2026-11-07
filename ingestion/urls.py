"""URL routes for the document ingestion API."""

from django.urls import path

from ingestion.views import DocumentUploadView

urlpatterns = [
    path("documents/", DocumentUploadView.as_view(), name="document-upload"),
]
