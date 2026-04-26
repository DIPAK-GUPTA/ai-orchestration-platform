# Requirements (assignment mapping)

This file shows how the repository satisfies the stated **technical**, **core**, and **functional** requirements. For setup, use [SETUP.md](./SETUP.md). For why **LangGraph** is used, see [README.md § Runtime](../README.md#runtime-choice-langgraph).

---

## Technical and core requirements

| Requirement | Fulfilled by |
| --- | --- |
| One of: OpenClaw, LangGraph, CrewAI, AutoGen, or custom; justified in README | **LangGraph** in `backend/app/agents/runtime.py` (`requirements.txt`: `langgraph`). Rationale: [README](../README.md#framework-selection-why-langgraph). |
| Web UI, persistence, messaging | **Next.js** UI, **PostgreSQL**, **Telegram** (`messaging/telegram.py`) |
| Optional: full local, one command | `docker compose up --build` (repo root) — [SETUP.md](./SETUP.md) |
| Agents communicate asynchronously | **Celery** runs workflows; **A2A** tool in `tools.py` (Redis + DB) |
| Message history stored and shown in UI | `Message` model, `GET /api/messages`, **Messages** page |
| At least one channel: WhatsApp, Telegram, or Slack | **Telegram** (others: extend like Slack in README) |
| Real LLM + graph in worker (not a UI mock) | `tasks.py` → `WorkflowGraph` → `ainvoke` with LangChain + tools |

---

## Functional requirements

| Requirement | Fulfilled by |
| --- | --- |
| **Agent CRUD** — name, role, system prompt, model, tools, channels | API `api/routes/agents.py`; model `models.py` (`Agent`); UI **New/Edit** (`AgentForm`); channels: Telegram + `channel_config` JSON. **Delete:** `DELETE /api/agents/{id}` (use `/docs` if the UI has no delete button). |
| **Config** — schedules, memory, skills, interaction rules, guardrails | Same model + `AgentForm`; guardrails/ interaction in `runtime.py`; memory in `memory.py`; schedules via `check_scheduled_agents` (needs **celery_beat** — included in Docker Compose) |
| **Visual workflow builder** + conditions + feedback loops | **Workflows → New/Edit** (`WorkflowGraphEditor`); edge conditions in `runtime.py`; template **content_creation** has a critic–ideator **loop** (`templates.py`) |
| **≥2 pre-built templates** | **3** in `app/agents/templates.py`; **Templates** in UI |
| **External channel** (WA / TG / SL) | **Telegram** implemented |
| **Monitoring** — logs, A2A, token/cost | **Executions** page: REST + WebSocket; A2A in stream + DB; totals on execution; per-step on logs |
| **E2E demo** — 2+ agents, real work | Use a **template** or build a 2+ agent graph → **Run** with `OPENAI_API_KEY`. Record a short demo; see [Demo checklist in README](../README.md#demo-checklist) |

---

## Framework choice (short)

**LangGraph** is used so workflows in the database map directly to a **StateGraph** (branches, loops) with **async** `ainvoke` and LangChain tools. **CrewAI/AutoGen** are better for fixed teams than a user-edited graph; **OpenClaw** targets a different (always-on / SOUL) model. A **custom** runtime was unnecessary here.

**Code paths:** `workers/tasks.py` (run) → `agents/runtime.py` (graph) · `messaging/telegram.py` (Telegram) · `api/routes/messages.py` + `app/messages/page` (history)
