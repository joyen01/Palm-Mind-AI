"""HTTP endpoint for multi-turn chat. Interview bookings are created from the chat."""

from uuid import UUID

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from conversation.serializers import ChatMessageRequestSerializer, ChatResultSerializer
from conversation.service import build_conversation_service


class ChatMessagesView(APIView):
    """POST a user message to a session. The reply and any sources or booking are returned."""

    def post(self, request: Request, session_id: UUID) -> Response:
        request_serializer = ChatMessageRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        result = build_conversation_service().send_message(
            session_id=session_id,
            message=request_serializer.validated_data["message"],
        )
        return Response(ChatResultSerializer(result).data, status=status.HTTP_201_CREATED)
