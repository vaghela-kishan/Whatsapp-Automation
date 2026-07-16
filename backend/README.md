# AI Support Platform — Backend

Production-grade FastAPI backend for the AI Customer Support Automation Platform.
Built on Clean Architecture: routes are thin, business logic lives in services,
data access lives in CRUD/repositories, and integrations sit behind interfaces.

## Requirements

- Python 3.11+
- (Later) PostgreSQL 16 + Redis via Docker Compose

## Quickstart (Windows / PowerShell)

```powershell
cd ai-support-platform\backend

# 1. Create & activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements-dev.txt

# 3. Environment file (already created for dev; copy from example otherwise)
#    copy .env.example .env

# 4. Run the API (reload on change)
uvicorn app.main:app --reload
```

Open:
- Swagger UI  → http://127.0.0.1:8000/docs
- ReDoc       → http://127.0.0.1:8000/redoc
- Health      → http://127.0.0.1:8000/api/v1/health

## Testing

```powershell
pytest
```

## Project layout

```
app/
  main.py            App factory, lifespan (DB init + seed), router wiring
  core/              config, logging, exceptions, middleware, context
  db/                Base, session, mixins, portable types, init_db
  api/               deps + versioned routers (v1/endpoints/*)
  models/            Customer, Conversation, Message, Order, FAQ, enums
  schemas/           Pydantic contracts
  crud/              Repositories (customer, conversation, order, faq)
  services/          intent · faq · order · ai · conversation · stats · seed
  integrations/      ai/ (gemini, mock) · whatsapp/ (meta, mock)
  workers/           Scheduler / background tasks
  utils/             Helpers
alembic/             Migrations
tests/               Pytest suite
```

## The automation pipeline

`app/services/conversation_service.py::handle_inbound` is the core:

```
identify customer → open/continue conversation → persist inbound →
detect intent → resolve answer (order lookup / FAQ / AI) →
persist + send outbound → update conversation state
```

Deterministic facts (order status, FAQ answers) are sent verbatim; only
open-ended turns (greetings, unknown questions, escalations) go to the AI
provider. Provider selection is config-driven (`AI_PROVIDER`,
`WHATSAPP_PROVIDER`) and falls back to the mock engines automatically, so the
app always starts and always replies — even with no API keys.

## Key endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/chat/send` | Simulator / inbound message → AI reply |
| GET/POST | `/api/v1/webhook/whatsapp` | Meta Cloud API verify + inbound |
| GET | `/api/v1/conversations` | Agent inbox list |
| POST | `/api/v1/conversations/{id}/reply` | Human agent reply |
| GET | `/api/v1/orders` · `/orders/{number}` | Orders |
| GET/POST/PATCH/DELETE | `/api/v1/faqs` | Knowledge base |
| GET | `/api/v1/stats/dashboard` | Dashboard analytics |

## Database migrations (Alembic)

Migrations begin in Step 2 (the `users` table). Commands:

```powershell
alembic revision --autogenerate -m "message"   # generate
alembic upgrade head                            # apply
alembic downgrade -1                            # roll back one
```

## Switching SQLite → PostgreSQL

1. `docker compose up -d db redis` (from the project root)
2. In `.env` set:
   `DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/support`
3. `alembic upgrade head`

No application code changes required — the ORM layer is database-agnostic.
