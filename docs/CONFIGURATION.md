# Environment variables

The backend loads **`backend/.env`** (see [`.env.example`](../backend/.env.example)). In **Docker**, `docker-compose.yml` **overrides** `DATABASE_URL`, `REDIS_URL`, and Celery URLs to point at the `postgres` and `redis` services.

Put **secrets** (e.g. `OPENAI_API_KEY`, `TELEGRAM_BOT_TOKEN`) in `backend/.env` and do not commit that file.

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Async SQLAlchemy URL (`postgresql+asyncpg://...`) |
| `DATABASE_URL_SYNC` | Sync URL for Celery (`postgresql://...`) |
| `REDIS_URL` | App + memory (e.g. `.../0`) |
| `CELERY_BROKER_URL` | Celery broker (e.g. `.../1`) |
| `CELERY_RESULT_BACKEND` | Celery results (e.g. `.../2`) |
| `REDIS_HOST` | (Rare) if hostname `redis` does not resolve in your Docker network, set to a working host. |
| `OPENAI_API_KEY` | OpenAI for `gpt-…` models (required for real calls) |
| `OPENAI_MODEL` | Default model name if not set on the agent |
| `ANTHROPIC_API_KEY` | For `claude…` model names on agents |
| `TELEGRAM_BOT_TOKEN` | Telegram bot |
| `TELEGRAM_WEBHOOK_URL` | Public `https://…` base of the API (no path); used for `setWebhook` |
| `SECRET_KEY` | App secret |
| `DEBUG` | `false` in Docker; set `true` for verbose local SQL (optional) |

**Frontend (build-time):** `NEXT_PUBLIC_API_URL` (e.g. `http://localhost:8000`) and `NEXT_PUBLIC_WS_URL` (e.g. `ws://localhost:8000`). In Compose these are set on the `frontend` service.

**Local dev example** (Postgres/Redis on localhost — adjust ports to match your machine):

```env
DATABASE_URL=postgresql+asyncpg://orchestrator:orchestrator_pass@localhost:5432/agentdb
DATABASE_URL_SYNC=postgresql://orchestrator:orchestrator_pass@localhost:5432/agentdb
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
OPENAI_API_KEY=sk-...
```

In **Docker**, only things like `OPENAI_API_KEY` and Telegram settings need to match your setup; database and Redis hosts come from Compose.

Default Postgres in Compose: user `orchestrator`, password `orchestrator_pass`, database `agentdb` (overridable via `POSTGRES_*` in the environment).
