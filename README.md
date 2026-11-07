# Document RAG Backend

Two REST APIs built with Django:

1. **Document Ingestion** — upload a `.pdf` or `.txt`, extract text, chunk it, embed the chunks and store vectors in Qdrant with metadata in PostgreSQL.
2. **Conversational RAG** — multi-turn chat over indexed documents, Redis-backed memory, and interview booking collected via the LLM and stored in PostgreSQL.

## Stack

| Concern | Choice |
| --- | --- |
| Web framework | Django 5.2 + DRF |
| Chat + embeddings | Ollama (local, no API key needed) |
| Vector store | Qdrant |
| Metadata / bookings | PostgreSQL |
| Chat memory / drafts | Redis |
| PDF extraction | pypdf |

## Project layout

```
config/          settings, root URLs, WSGI
core/            shared LLM client (Ollama), Qdrant store, Redis
ingestion/       Document Ingestion API
  chunking/      fixed_size and paragraph strategies + factory
  extraction.py  PDF and TXT text extraction
  services.py    extract -> chunk -> embed -> index -> save
conversation/    Conversational RAG API
  service.py     route -> retrieve -> answer, or book
  memory.py      Redis chat history and booking drafts
  booking.py     booking validation and persistence
  retrieval.py   query embedding and Qdrant search
  prompts.py     prompt templates
tests/           unit tests (chunking, booking, extraction)
```

## Setup

### Option A: Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

Then pull the models:
```bash
docker compose exec ollama ollama pull llama3.2
docker compose exec ollama ollama pull nomic-embed-text
```

API is at `http://localhost:8000`. Migrations run on startup.

### Option B: Native Ollama

1. Install [Ollama](https://ollama.com/download) and pull the models:
   ```bash
   ollama pull llama3.2
   ollama pull nomic-embed-text
   ```
2. Start services:
   ```bash
   docker compose up -d db redis qdrant
   ```
3. Run the app:
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

All config is via environment variables — see [.env.example](.env.example).

## Document Ingestion API

`POST /api/ingestion/documents/` (multipart form)

| Field | Required | Notes |
| --- | --- | --- |
| `file` | yes | `.pdf` or `.txt`, max `UPLOAD_MAX_BYTES` (default 20 MB) |
| `chunking_strategy` | no | `fixed_size` (default) or `paragraph` |

```bash
curl -X POST http://localhost:8000/api/ingestion/documents/ \
  -F "file=@handbook.pdf" \
  -F "chunking_strategy=paragraph"
```

Returns `201` with the document record. Unsupported types, empty files, and unreadable PDFs return `422`.

## Conversational RAG API

`POST /api/chat/sessions/{session_id}/messages/` — body: `{"message": "..."}`

Generate a UUID for `session_id` and reuse it across turns; history is kept in Redis.

```bash
SESSION=$(python -c "import uuid; print(uuid.uuid4())")

curl -X POST "http://localhost:8000/api/chat/sessions/$SESSION/messages/" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the refund policy?"}'
```

Response fields: `intent` (`question` or `booking`), `reply`, `sources`, `booking`.

Each turn makes one routing LLM call plus one answer or booking-reply call.

## Tests and quality

```bash
pytest
mypy .
ruff check .
```
