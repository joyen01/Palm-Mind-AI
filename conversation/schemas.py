"""Typed data shared by the conversation services: LLM outputs, Redis state and results."""

from dataclasses import dataclass
from datetime import date, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from conversation.models import InterviewBooking

Intent = Literal["question", "booking"]
Role = Literal["user", "assistant"]


class TurnAnalysis(BaseModel):
    """Structured output the LLM returns for each user message (routing + extraction)."""

    intent: Intent = Field(
        description=(
            '"booking" if the user wants to book an interview or is giving name, email, date or '
            'time for a booking in progress. Otherwise "question".'
        ),
    )
    standalone_question: str | None = Field(
        default=None,
        description=(
            "For question intent: the latest message rewritten as one self-contained question, "
            "resolving references to earlier turns. Null for booking intent."
        ),
    )
    name: str | None = Field(
        default=None,
        description="The candidate's name, only if stated in the latest message.",
    )
    email: str | None = Field(
        default=None,
        description="The candidate's email address, only if stated in the latest message.",
    )
    interview_date: str | None = Field(
        default=None,
        description="Requested interview date as YYYY-MM-DD, resolved from today's date.",
    )
    interview_time: str | None = Field(
        default=None,
        description="Requested interview start time as 24-hour HH:MM.",
    )


class ChatTurn(BaseModel):
    """One stored message in a session's conversation history."""

    role: Role
    content: str


class BookingDraft(BaseModel):
    """Booking details collected so far for a session. Kept in Redis until the booking is saved."""

    name: str | None = None
    email: str | None = None
    interview_date: str | None = None
    interview_time: str | None = None

    def merged_with(self, analysis: TurnAnalysis) -> "BookingDraft":
        """Return a new draft where values from the latest message replace stored ones."""
        return BookingDraft(
            name=analysis.name or self.name,
            email=analysis.email or self.email,
            interview_date=analysis.interview_date or self.interview_date,
            interview_time=analysis.interview_time or self.interview_time,
        )

    def missing_fields(self) -> list[str]:
        return [field for field, value in self.model_dump().items() if value is None]


@dataclass(frozen=True, slots=True)
class BookingDetails:
    """A validated, complete booking ready to be saved."""

    name: str
    email: str
    interview_date: date
    interview_time: time


@dataclass(frozen=True, slots=True)
class SourceCitation:
    document_id: str
    filename: str
    chunk_index: int
    score: float


@dataclass(frozen=True, slots=True)
class ChatResult:
    session_id: UUID
    reply: str
    intent: Intent
    sources: list[SourceCitation]
    booking: InterviewBooking | None
