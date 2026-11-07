from dataclasses import dataclass
from datetime import date, time
from uuid import UUID

from django.db import IntegrityError, transaction
from pydantic import EmailStr, TypeAdapter, ValidationError

from conversation.models import InterviewBooking
from conversation.schemas import BookingDetails, BookingDraft

MAX_NAME_LENGTH = 120
_EMAIL_ADAPTER: TypeAdapter[str] = TypeAdapter(EmailStr)


class SlotUnavailableError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class DraftValidation:
    draft: BookingDraft
    errors: dict[str, str]


def validate_draft(draft: BookingDraft, today: date) -> DraftValidation:
    cleaned = draft.model_copy()
    errors: dict[str, str] = {}

    if draft.name is not None:
        name = draft.name.strip()
        if 0 < len(name) <= MAX_NAME_LENGTH:
            cleaned.name = name
        else:
            cleaned.name = None
            errors["name"] = f"The name must be between 1 and {MAX_NAME_LENGTH} characters."

    if draft.email is not None:
        try:
            cleaned.email = _EMAIL_ADAPTER.validate_python(draft.email.strip())
        except ValidationError:
            cleaned.email = None
            errors["email"] = "The email address is not valid."

    if draft.interview_date is not None:
        try:
            parsed_date = date.fromisoformat(draft.interview_date)
        except ValueError:
            cleaned.interview_date = None
            errors["interview_date"] = "The interview date must be a valid YYYY-MM-DD date."
        else:
            if parsed_date < today:
                cleaned.interview_date = None
                errors["interview_date"] = "The interview date cannot be in the past."

    if draft.interview_time is not None:
        try:
            time.fromisoformat(draft.interview_time)
        except ValueError:
            cleaned.interview_time = None
            errors["interview_time"] = "The interview time must be a 24-hour HH:MM time."

    return DraftValidation(draft=cleaned, errors=errors)


def to_booking_details(draft: BookingDraft) -> BookingDetails | None:
    if (
        draft.name is None
        or draft.email is None
        or draft.interview_date is None
        or draft.interview_time is None
    ):
        return None
    return BookingDetails(
        name=draft.name,
        email=draft.email,
        interview_date=date.fromisoformat(draft.interview_date),
        interview_time=time.fromisoformat(draft.interview_time),
    )


class InterviewBookingRepository:
    def create(self, session_id: UUID, details: BookingDetails) -> InterviewBooking:
        booking = InterviewBooking(
            session_id=session_id,
            name=details.name,
            email=details.email,
            interview_date=details.interview_date,
            interview_time=details.interview_time,
        )
        try:
            with transaction.atomic():
                booking.save(force_insert=True)
        except IntegrityError as exc:
            raise SlotUnavailableError from exc
        return booking
