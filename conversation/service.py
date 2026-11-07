"""Conversational RAG orchestration: route each message, then answer or book.

Each user message makes one structured LLM call (intent, standalone question and booking fields
together). Questions then go through custom retrieval and one answer call. Booking turns merge
fields into a Redis draft, save the booking once every field is valid, and otherwise ask the
user for what is missing.
"""

from uuid import UUID

from django.conf import settings
from django.utils import timezone

from conversation.booking import (
    InterviewBookingRepository,
    SlotUnavailableError,
    to_booking_details,
    validate_draft,
)
from conversation.memory import BookingDraftStore, ChatMemory
from conversation.prompts import ANSWER_SYSTEM_PROMPT, BOOKING_SYSTEM_PROMPT, ROUTER_SYSTEM_PROMPT
from conversation.retrieval import Retriever, format_context
from conversation.schemas import (
    BookingDraft,
    ChatResult,
    ChatTurn,
    SourceCitation,
    TurnAnalysis,
)
from core.llm import ChatMessage, ChatModel, chat_message, get_chat_model, get_embedder
from core.redis_client import get_redis
from core.vector_store import get_vector_store


class ConversationService:
    def __init__(
        self,
        *,
        llm: ChatModel,
        memory: ChatMemory,
        drafts: BookingDraftStore,
        retriever: Retriever,
        bookings: InterviewBookingRepository,
    ) -> None:
        self._llm = llm
        self._memory = memory
        self._drafts = drafts
        self._retriever = retriever
        self._bookings = bookings

    def send_message(self, session_id: UUID, message: str) -> ChatResult:
        key = str(session_id)
        history = self._memory.load(key)
        draft = self._drafts.load(key)

        analysis = self._analyze(message, history, draft)
        if analysis.intent == "booking":
            result = self._handle_booking(session_id, message, history, draft, analysis)
        else:
            result = self._handle_question(session_id, message, history, analysis)

        self._memory.append(
            key,
            [
                ChatTurn(role="user", content=message),
                ChatTurn(role="assistant", content=result.reply),
            ],
        )
        return result

    def _analyze(
        self,
        message: str,
        history: list[ChatTurn],
        draft: BookingDraft,
    ) -> TurnAnalysis:
        system = ROUTER_SYSTEM_PROMPT.format(
            today=timezone.localdate().isoformat(),
            timezone=settings.TIME_ZONE,
            draft=draft.model_dump_json(),
        )
        return self._llm.extract(
            system,
            [*_as_messages(history), chat_message("user", message)],
            TurnAnalysis,
        )

    def _handle_question(
        self,
        session_id: UUID,
        message: str,
        history: list[ChatTurn],
        analysis: TurnAnalysis,
    ) -> ChatResult:
        hits = self._retriever.retrieve(analysis.standalone_question or message)
        excerpts = format_context(hits)
        reply = self._llm.complete(
            ANSWER_SYSTEM_PROMPT,
            [
                *_as_messages(history),
                chat_message(
                    "user",
                    f"Document excerpts:\n{excerpts}\n\nQuestion: {message}",
                ),
            ],
        )
        sources = [
            SourceCitation(
                document_id=hit.document_id,
                filename=hit.filename,
                chunk_index=hit.chunk_index,
                score=hit.score,
            )
            for hit in hits
        ]
        return ChatResult(
            session_id=session_id,
            reply=reply,
            intent="question",
            sources=sources,
            booking=None,
        )

    def _handle_booking(
        self,
        session_id: UUID,
        message: str,
        history: list[ChatTurn],
        draft: BookingDraft,
        analysis: TurnAnalysis,
    ) -> ChatResult:
        key = str(session_id)
        today = timezone.localdate()
        validation = validate_draft(draft.merged_with(analysis), today)
        cleaned = validation.draft
        errors = dict(validation.errors)

        details = to_booking_details(cleaned)
        if details is not None:
            try:
                booking = self._bookings.create(session_id, details)
            except SlotUnavailableError:
                cleaned = cleaned.model_copy(
                    update={"interview_date": None, "interview_time": None},
                )
                errors["interview_time"] = (
                    "That date and time is already booked. Please suggest another slot."
                )
            else:
                self._drafts.clear(key)
                reply = (
                    f"Thanks, {details.name}. Your interview is booked for "
                    f"{details.interview_date:%A %d %B %Y} at {details.interview_time:%H:%M}. "
                    f"Your booking reference is {booking.id}."
                )
                return ChatResult(
                    session_id=session_id,
                    reply=reply,
                    intent="booking",
                    sources=[],
                    booking=booking,
                )

        self._drafts.save(key, cleaned)
        reply = self._booking_follow_up(message, history, cleaned, errors, today.isoformat())
        return ChatResult(
            session_id=session_id,
            reply=reply,
            intent="booking",
            sources=[],
            booking=None,
        )

    def _booking_follow_up(
        self,
        message: str,
        history: list[ChatTurn],
        draft: BookingDraft,
        errors: dict[str, str],
        today: str,
    ) -> str:
        system = BOOKING_SYSTEM_PROMPT.format(
            today=today,
            timezone=settings.TIME_ZONE,
            details=draft.model_dump_json(),
            missing=", ".join(draft.missing_fields()) or "nothing",
            errors="; ".join(errors.values()) or "none",
        )
        return self._llm.complete(
            system,
            [*_as_messages(history), chat_message("user", message)],
        )


def _as_messages(history: list[ChatTurn]) -> list[ChatMessage]:
    return [chat_message(turn.role, turn.content) for turn in history]


def build_conversation_service() -> ConversationService:
    redis = get_redis()
    return ConversationService(
        llm=get_chat_model(),
        memory=ChatMemory(
            redis,
            max_messages=settings.CHAT_MEMORY_MAX_MESSAGES,
            ttl_seconds=settings.CHAT_MEMORY_TTL_SECONDS,
        ),
        drafts=BookingDraftStore(redis, ttl_seconds=settings.CHAT_MEMORY_TTL_SECONDS),
        retriever=Retriever(
            embedder=get_embedder(),
            vector_store=get_vector_store(),
            top_k=settings.RAG_TOP_K,
        ),
        bookings=InterviewBookingRepository(),
    )
