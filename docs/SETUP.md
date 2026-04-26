# Setup and run

All `docker compose` commands run from the **repository root** (the folder with `docker-compose.yml`).

## Prerequisites

- **Docker** + `docker compose`
- For real runs: **`OPENAI_API_KEY`** in `backend/.env`
- For Telegram: bot token + public HTTPS URL (e.g. ngrok) — optional

Without Docker: Python 3.10+, Node 18+, local PostgreSQL and Redis. Match URLs in `backend/.env` to your machine.

## Docker (recommended)

1. `cd` to the project root.
2. `cp backend/.env.example backend/.env` — set at least:
   - `OPENAI_API_KEY=sk-...`
3. Start:  
   `docker compose up --build`
4. Wait for **Uvicorn** on port 8000 and Celery connected to Redis (no repeat Redis errors in logs).
5. Open:

| | URL |
| --- | --- |
| UI | http://localhost:3000 |
| API docs | http://localhost:8000/docs |
| Health | http://127.0.0.1:8000/health |

6. Stop: `Ctrl+C` or `docker compose down`. To wipe data volumes: `docker compose down -v`.

**Host ports (only when you connect from your computer, not between containers):**

| Service | Host | Inside containers |
| --- | --- | --- |
| App UI | 3000 | (Next.js) |
| API | 8000 | 8000 |
| Postgres | **15432** | `postgres:5432` |
| Redis | **16379** | `redis:6379` |

`psql`: `-h 127.0.0.1 -p 15432 -U orchestrator agentdb`  
`redis-cli` from host: `-p 16379`

## What Compose starts

`postgres`, `redis`, `backend` (FastAPI), `celery_worker`, `celery_beat`, `frontend` (Next.js). Inside the network, use hostnames `postgres` and `redis` (not `localhost`).

## Local (no Docker)

From `backend/`: venv, `pip install -r requirements.txt`, then `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` (fix `PYTHONPATH` so `import app` works).  
Separate shells: `celery -A app.workers.celery_app worker -Q agent_tasks,workflow_tasks,default` and (optional) `... beat`.  
From `frontend/`: `npm install` and `npm run dev` with `NEXT_PUBLIC_API_URL=http://localhost:8000` and `NEXT_PUBLIC_WS_URL=ws://localhost:8000`.

## Check it works

`curl -s http://127.0.0.1:8000/health` → `{"status":"ok",...}`

Tests: `cd backend && pytest -q`  
Optional live API tests: set `RUN_API_TESTS=1` and `DATABASE_URL` to a real Postgres, then `pytest tests/test_api_live.py -q` (see root **README**).

## Troubleshooting

| Issue | What to do |
| --- | --- |
| Port already in use (8000, 3000, etc.) | Change the `ports:` mapping in `docker-compose.yml` for that service. |
| Redis connection errors in Celery | `docker compose down` then `docker compose up --build`. Compose should use `redis` as the hostname. |
| Postgres bind error | This project uses host **15432** for Postgres to avoid clashing with a local 5432. |
| Local Redis 6379 busy | This project uses host **16379** for Redis. |

More env details: [CONFIGURATION.md](./CONFIGURATION.md) · System design: [ARCHITECTURE.md](./ARCHITECTURE.md)

## Telegram (optional)

1. Create a bot with [@BotFather](https://t.me/botfather) → set `TELEGRAM_BOT_TOKEN` in `backend/.env`.  
2. Expose the API with HTTPS (e.g. ngrok). Set `TELEGRAM_WEBHOOK_URL` to that public **base** URL.  
3. Start the stack. Register the webhook (see API `/docs` for `POST /api/telegram/webhook/register` if needed).  
4. In the UI, enable the agent as a Telegram agent.

## Main UI routes

| Path | Use |
| --- | --- |
| `/agents` | List agents; New / edit |
| `/workflows` | List; New graph or open one |
| `/executions` | Runs; open one for logs + live stream |
| `/messages` | History |
| `/templates` | Instantiate a template workflow |

## Extension points

- New workflow templates: `backend/app/agents/templates.py`  
- New channel (e.g. Slack): README “Adding a new messaging channel”

Full README: [../README.md](../README.md)
