"""Tests for interview booking validation and draft handling."""

from datetime import date, time

from conversation.booking import to_booking_details, validate_draft
from conversation.schemas import BookingDetails, BookingDraft, TurnAnalysis


def test_validate_draft_all_valid() -> None:
    today = date(2026, 11, 7)
    draft = BookingDraft(
        name="Ada Lovelace",
        email="ada@example.com",
        interview_date="2026-11-10",
        interview_time="14:00",
    )
    result = validate_draft(draft, today=today)
    assert not result.errors
    assert result.draft.name == "Ada Lovelace"
    assert result.draft.email == "ada@example.com"
    assert result.draft.interview_date == "2026-11-10"
    assert result.draft.interview_time == "14:00"


def test_validate_draft_past_date_rejected() -> None:
    today = date(2026, 11, 7)
    draft = BookingDraft(
        name="Alan Turing",
        email="alan@example.com",
        interview_date="2026-11-01",
        interview_time="10:00",
    )
    result = validate_draft(draft, today=today)
    assert "interview_date" in result.errors
    assert result.draft.interview_date is None
    assert "past" in result.errors["interview_date"].lower()


def test_validate_draft_invalid_email_rejected() -> None:
    today = date(2026, 11, 7)
    draft = BookingDraft(
        name="Grace Hopper",
        email="not-an-email",
        interview_date="2026-11-15",
        interview_time="09:30",
    )
    result = validate_draft(draft, today=today)
    assert "email" in result.errors
    assert result.draft.email is None


def test_validate_draft_invalid_time_rejected() -> None:
    today = date(2026, 11, 7)
    draft = BookingDraft(
        name="Claude Shannon",
        email="shannon@example.com",
        interview_date="2026-11-15",
        interview_time="25:99",
    )
    result = validate_draft(draft, today=today)
    assert "interview_time" in result.errors
    assert result.draft.interview_time is None


def test_draft_merge_and_missing_fields() -> None:
    draft = BookingDraft(name="John von Neumann")
    assert draft.missing_fields() == ["email", "interview_date", "interview_time"]

    analysis = TurnAnalysis(
        intent="booking",
        email="john@example.com",
        interview_date="2026-11-20",
        interview_time="11:00",
    )
    merged = draft.merged_with(analysis)
    assert merged.missing_fields() == []
    assert merged.name == "John von Neumann"
    assert merged.email == "john@example.com"


def test_to_booking_details() -> None:
    complete_draft = BookingDraft(
        name="Margaret Hamilton",
        email="margaret@example.com",
        interview_date="2026-12-01",
        interview_time="15:30",
    )
    details = to_booking_details(complete_draft)
    assert details == BookingDetails(
        name="Margaret Hamilton",
        email="margaret@example.com",
        interview_date=date(2026, 12, 1),
        interview_time=time(15, 30),
    )

    incomplete_draft = BookingDraft(name="Margaret Hamilton")
    assert to_booking_details(incomplete_draft) is None
