# Setup Guide

This guide gets the Document RAG backend running on your machine. For what the APIs do and how they behave, see [README.md](README.md).

## 1. Prerequisites

- **Docker and Docker Compose**: the easiest way to run the app and its services (PostgreSQL, Redis, Qdrant).
- **Python 3.12 or newer**: only needed for the local setup (option B).
- **OpenAI API key**: used for embeddings.
- **Anthropic API key**: used for chat, routing and interview booking.

## 2. Configure the environment

From the project folder:

```bash
cp .env.example .env
```

Open `.env` and set these values:

| Variable | Required | What to put |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Yes | A long random string. Generate one with `python3 -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `OPENAI_API_KEY` | Yes | Your OpenAI key. Needed for document upload and chat. |
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic key. Needed for chat. |

The other values in `.env.example` work as they are. The server starts without the API keys, but upload and chat requests fail until the keys are set.

## 3. Start the application

Choose **A** (everything in Docker) or **B** (the app runs on your machine and only the services run in Docker).

### Option A: Docker Compose

```bash
docker compose up --build
```

This starts:

- the API at `http://localhost:8000`
- PostgreSQL on port `5432`
- Redis on port `6379`
- Qdrant on port `6333`

Migrations run automatically on startup.

To stop everything, press `Ctrl+C`, then run `docker compose down`.

### Option B: Run the app locally

**Step 1: start the services**

```bash
docker compose up -d db redis qdrant
```

The default values in `.env.example` already point to these services on `localhost`.

**Step 2: create a virtual environment and install dependencies**

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Step 3: create the database tables**

```bash
python manage.py migrate
```

**Step 4: start the development server**

```bash
python manage.py runserver
```

The API is at `http://localhost:8000`.

## 4. Check that it works

Upload a small text document:

```bash
echo "Refunds are processed within 14 days of the request." > sample.txt

curl -X POST http://localhost:8000/api/ingestion/documents/ \
  -F "file=@sample.txt"
```

You should get `201 Created` with `"status": "indexed"`.

Then ask a question in a new chat session:

```bash
SESSION=$(python3 -c "import uuid; print(uuid.uuid4())")

curl -X POST "http://localhost:8000/api/chat/sessions/$SESSION/messages/" \
  -H "Content-Type: application/json" \
  -d '{"message": "How long do refunds take?"}'
```

You should get `201 Created` with `"intent": "question"` and a reply that mentions 14 days. Delete `sample.txt` afterwards.

## 5. Optional: type checking and linting

These tools are not in `requirements.txt`. Install them when you need them:

```bash
pip install mypy ruff django-stubs djangorestframework-stubs
mypy .
ruff check .
```

## 6. Troubleshooting

| Problem | Fix |
| --- | --- |
| `The SECRET_KEY setting must not be empty` | Set `DJANGO_SECRET_KEY` in `.env`. |
| Upload or chat returns `500`, and the log says `OPENAI_API_KEY must be set` or `ANTHROPIC_API_KEY must be set` | Set the key in `.env`, then restart the server. |
| `400 Bad Request` with `Invalid HTTP_HOST` | Add the host you are calling to `DJANGO_ALLOWED_HOSTS` in `.env`. |
| `connection refused` on port `5432`, `6379` or `6333` | The services are not running. Run `docker compose ps`, then `docker compose up -d db redis qdrant`. |
| `password authentication failed` during `migrate` | `POSTGRES_USER`, `POSTGRES_PASSWORD` and `POSTGRES_DB` in `.env` must match the database. The defaults are `rag` for all three. |
| `port is already allocated` | Another program uses that port. Stop it, or change the port mapping in `docker-compose.yml`. |
| Qdrant errors about vector size after changing `EMBEDDING_DIMENSIONS` | The existing collection has a different size. Change `QDRANT_COLLECTION` to a new name, or delete the collection and upload the documents again. |

## 7. Stop and reset

```bash
docker compose down        # stop containers, keep data
docker compose down -v     # stop containers and delete PostgreSQL, Redis and Qdrant data
```
