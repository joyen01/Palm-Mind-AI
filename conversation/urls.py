"""URL routes for the conversational RAG API."""

from django.urls import path

from conversation.views import ChatMessagesView

urlpatterns = [
    path(
        "sessions/<uuid:session_id>/messages/",
        ChatMessagesView.as_view(),
        name="chat-messages",
    ),
]
