"""Redis-backed conversation memory and booking-draft state, keyed by session ID."""

from collections.abc import Sequence

from redis import Redis

from conversation.schemas import BookingDraft, ChatTurn


def _history_key(session_id: str) -> str:
    return f"chat:{session_id}:history"


def _draft_key(session_id: str) -> str:
    return f"chat:{session_id}:booking_draft"


class ChatMemory:
    """Rolling window of the most recent messages in a session, expiring after inactivity."""

    def __init__(self, redis: Redis, max_messages: int, ttl_seconds: int) -> None:
        self._redis = redis
        self._max_messages = max_messages
        self._ttl_seconds = ttl_seconds

    def load(self, session_id: str) -> list[ChatTurn]:
        raw_items = self._redis.lrange(_history_key(session_id), 0, -1)
        return [ChatTurn.model_validate_json(item) for item in raw_items]

    def append(self, session_id: str, turns: Sequence[ChatTurn]) -> None:
        key = _history_key(session_id)
        pipeline = self._redis.pipeline()
        pipeline.rpush(key, *(turn.model_dump_json() for turn in turns))
        pipeline.ltrim(key, -self._max_messages, -1)
        pipeline.expire(key, self._ttl_seconds)
        pipeline.execute()


class BookingDraftStore:
    """Partially collected interview details for a session, until the booking is saved."""

    def __init__(self, redis: Redis, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_seconds

    def load(self, session_id: str) -> BookingDraft:
        raw = self._redis.get(_draft_key(session_id))
        if raw is None:
            return BookingDraft()
        return BookingDraft.model_validate_json(raw)

    def save(self, session_id: str, draft: BookingDraft) -> None:
        self._redis.set(_draft_key(session_id), draft.model_dump_json(), ex=self._ttl_seconds)

    def clear(self, session_id: str) -> None:
        self._redis.delete(_draft_key(session_id))
