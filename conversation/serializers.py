"""Request validation and response shapes for the conversational RAG API."""

from typing import Any

from rest_framework import serializers

from conversation.models import InterviewBooking


class ChatMessageRequestSerializer(serializers.Serializer[Any]):
    message = serializers.CharField(max_length=4000)


class SourceCitationSerializer(serializers.Serializer[Any]):
    document_id = serializers.UUIDField()
    filename = serializers.CharField()
    chunk_index = serializers.IntegerField()
    score = serializers.FloatField()


class InterviewBookingSerializer(serializers.ModelSerializer[InterviewBooking]):
    class Meta:
        model = InterviewBooking
        fields = [
            "id",
            "session_id",
            "name",
            "email",
            "interview_date",
            "interview_time",
            "created_at",
        ]
        read_only_fields = fields


class ChatResultSerializer(serializers.Serializer[Any]):
    session_id = serializers.UUIDField()
    reply = serializers.CharField()
    intent = serializers.ChoiceField(choices=["question", "booking"])
    sources = SourceCitationSerializer(many=True)
    booking = InterviewBookingSerializer(allow_null=True)
