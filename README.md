# Document RAG Backend

A backend with two REST APIs, built with Django and Django REST Framework:

1. **Document Ingestion API**: upload a `.pdf` or `.txt` file, extract its text, chunk it with a selectable strategy, embed the chunks, store the vectors in Qdrant and the metadata in PostgreSQL.
2. **Conversational RAG API**: multi-turn chat over the indexed documents, with a custom RAG pipeline, chat memory in Redis, and interview booking (name, email, date, time) handled by the LLM and stored in PostgreSQL.

## Stack

| Concern | Choice |
| --- | --- |
| Web framework | Django 5.2 + Django REST Framework |
| Chat model | Anthropic Claude via the `anthropic` SDK (`claude-sonnet-5-5`, configurable) |
| Embeddings | OpenAI `text-embedding-3-small` via the `openai` SDK (configurable) |
| Vector store | Qdrant (`qdrant-client`) |
| Metadata and bookings | PostgreSQL via the Django ORM |
| Chat memory and booking drafts | Redis |
| PDF extraction | pypdf |

## Project layout

```
config/          Django project: settings, root URLs, WSGI entry point
core/            Shared clients: Anthropic chat model, OpenAI embedder, Qdrant store, Redis
ingestion/       Document Ingestion API
  chunking/      Strategy 1 (fixed_size) and strategy 2 (paragraph), plus the factory
  extraction.py  PDF and TXT text extraction
  services.py    Pipeline: extract -> chunk -> embed -> index -> record metadata
conversation/    Conversational RAG API
  service.py     Orchestration: route -> retrieve -> answer, or book
  memory.py      Redis chat history and booking drafts
  booking.py     Booking validation and persistence
  retrieval.py   Query embedding and top-k search
  prompts.py     Prompt templates
```

## Setup

### Option A: Docker Compose (app, PostgreSQL, Redis and Qdrant)

```bash
cp .env.example .env          # then set OPENAI_API_KEY, ANTHROPIC_API_KEY and DJANGO_SECRET_KEY
docker compose up --build
```

The API is served at `http://localhost:8000`. Migrations run on startup.

### Option B: Local Python

Requires Python 3.12+ and running PostgreSQL, Redis and Qdrant services (the compose file starts them).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # point POSTGRES_HOST, REDIS_URL and QDRANT_URL at your services
python manage.py migrate
python manage.py runserver
```

### Configuration

All settings come from environment variables; see [.env.example](.env.example). The required ones are `DJANGO_SECRET_KEY`, `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`.

## Document Ingestion API

`POST /api/ingestion/documents/` (multipart form)

| Field | Required | Description |
| --- | --- | --- |
| `file` | yes | A `.pdf` or `.txt` file (UTF-8 for TXT), up to `UPLOAD_MAX_BYTES` (default 20 MB). |
| `chunking_strategy` | no | `fixed_size` (default) or `paragraph`. |

- `fixed_size`: character windows of `CHUNK_SIZE` with `CHUNK_OVERLAP` overlap, cut at whitespace where possible.
- `paragraph`: packs whole paragraphs. Oversized paragraphs are split by sentence, then by window. Consecutive chunks share trailing units up to `CHUNK_OVERLAP` characters.

```bash
curl -X POST http://localhost:8000/api/ingestion/documents/ \
  -F "file=@handbook.pdf" \
  -F "chunking_strategy=paragraph"
```

Response (`201 Created`):

```json
{
  "id": "5f0c1e2a-6a4b-4c1e-9d8e-2f5a7b9c0d11",
  "filename": "handbook.pdf",
  "file_type": "pdf",
  "size_bytes": 84213,
  "chunking_strategy": "paragraph",
  "chunk_size": 1000,
  "chunk_overlap": 200,
  "chunk_count": 37,
  "status": "indexed",
  "error_message": "",
  "created_at": "2026-11-06T10:15:00Z",
  "updated_at": "2026-11-06T10:15:04Z"
}
```

Unsupported types, empty documents and unreadable PDFs return `422` with a `detail` message. A failed record is kept with `status: "failed"` and its `error_message`.

## Conversational RAG API

`POST /api/chat/sessions/{session_id}/messages/` with body `{"message": "..."}`

The client generates the `session_id` as a UUID and reuses it for every turn of a conversation. Chat history is kept in Redis under that ID.

```bash
SESSION=$(python -c "import uuid; print(uuid.uuid4())")

curl -X POST "http://localhost:8000/api/chat/sessions/$SESSION/messages/" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the refund policy?"}'

curl -X POST "http://localhost:8000/api/chat/sessions/$SESSION/messages/" \
  -H "Content-Type: application/json" \
  -d '{"message": "And how long does it take?"}'

curl -X POST "http://localhost:8000/api/chat/sessions/$SESSION/messages/" \
  -H "Content-Type: application/json" \
  -d '{"message": "I would like to book an interview for next Tuesday at 2pm. I am Ada Lovelace, ada@example.com."}'
```

Response (`201 Created`):

- `intent`: `question` or `booking`.
- `reply`: the assistant's message.
- `sources`: for questions, the `filename`, `chunk_index`, `document_id` and `score` of each excerpt used.
- `booking`: for bookings, the saved record once all four fields are valid; otherwise `null` while the assistant asks for what is missing.

Saved bookings are stored in the `conversation_interviewbooking` table in PostgreSQL.

### How a message is handled

1. **Route and extract (one LLM call)**: the chat model returns structured output containing the intent (`question` or `booking`), a standalone rewrite of the question (which resolves follow-ups such as "and how long does it take?"), and any name, email, date or time stated in the message. The output is constrained to a JSON schema. Dates are resolved against today's date in `TIME_ZONE`.
2. **Question path**: embed the standalone question, retrieve the top `RAG_TOP_K` chunks from Qdrant, then call the chat model with the excerpts and recent history. The model must answer only from the excerpts and cite them.
3. **Booking path**: merge the new fields into the Redis draft and validate them (name length, email format, date not in the past, `HH:MM` time). Once all four fields are valid, the booking is saved in PostgreSQL and the draft is cleared. A unique constraint on date and time prevents double-booking. Otherwise the chat model asks for the missing or invalid fields.
4. The user message and assistant reply are appended to the Redis history. The history keeps the last `CHAT_MEMORY_MAX_MESSAGES` messages and expires after `CHAT_MEMORY_TTL_SECONDS` of inactivity.

Each message costs one routing call, plus one answer or booking-reply call.

## Testing and Code Quality

- Automated unit tests covering chunking strategies and interview booking validation via `pytest`.
- Type annotations throughout. `mypy --strict` runs with the Pydantic, Django, and DRF plugins.
- `ruff` for linting.

```bash
pip install mypy ruff django-stubs djangorestframework-stubs pytest
pytest
mypy .
ruff check .
```

## Known limitations

- End-to-end tests against live external APIs: unit tests cover chunking and booking validation logic, while live end-to-end flows require running Redis, Qdrant, and valid API keys.
- The APIs have no authentication.
- Ingestion runs synchronously in the request. Large files would benefit from a background worker such as Celery.
- Scanned PDFs without a text layer are not supported (no OCR). Encrypted PDFs are rejected.
- Bookings are saved as soon as all four fields are valid. There is no confirmation step, no email is sent, and cancellation and rescheduling are not implemented.
- Times are stored in `TIME_ZONE` with no availability windows.
