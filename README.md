# Oil News Alert — AI Brent-moving news detection (MVP)

An AI system that monitors global news for events likely to move **European oil prices
(ICE Brent)**, scores each item for trading importance and likely price direction, and pushes
alerts to prop traders. A web app lets traders view the analyzed feed, see *why* each alert
fired, and configure their own thresholds and channels.

> **Decision-support with a human in the loop.** It never places or recommends trades
> automatically.

---

## Architecture

```
                 ┌───────────────────────────────────────────────┐
   Scheduler ───▶│  INGESTION WORKER                              │
  (every N min)  │  GDELT DOC API · RSS feeds · (NewsData/FMP)    │
                 │  normalize → dedup (hash/url) → store raw       │
                 └───────────────┬───────────────────────────────┘
                                 ▼
                 ┌───────────────────────────────────────────────┐
                 │  ANALYSIS PIPELINE                              │
                 │  1) keyword prefilter (cheap, no LLM)          │
                 │  2) relevance triage  → Claude Haiku           │
                 │  3) signal extraction → Claude Sonnet (JSON)   │
                 │  4) importance score  (deterministic formula)  │
                 └───────────────┬───────────────────────────────┘
                                 ▼
                 ┌───────────────────────────────────────────────┐
                 │  ALERTING ENGINE                               │
                 │  match configs · event-level dedup · quiet hrs │
                 │  deliver: in-app(SSE) + Telegram/email         │
                 └───────────────┬───────────────────────────────┘
                                 ▼
        Postgres  ◀──────────────────────────▶  FastAPI  ◀──── Next.js web app
   (articles, analyses, alerts, configs)         (REST + SSE)
```

Two processes share one Postgres DB: the **worker** (scheduler + ingest + analysis + alert
dispatch) and the **API** (serves the web app and SSE stream). They are kept separate so the
UI never blocks on the pipeline.

## Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| API | FastAPI + Uvicorn |
| Worker | APScheduler (in-process) |
| LLM | Anthropic — Haiku (triage) + Sonnet (extraction), Opus optional |
| Validation | Pydantic v2 |
| DB | Postgres 15 + SQLAlchemy 2.0 + Alembic |
| News | GDELT 2.0 DOC API (free) + curated RSS |
| Fundamentals | EIA Open Data API |
| Frontend | Next.js + Tailwind (Phase 5) |
| Alerts out | In-app SSE + Telegram / SMTP email |

## Quickstart

```bash
cp .env.example .env        # fill in keys (ANTHROPIC_API_KEY etc.)
make up                     # build + start Postgres + API (http://localhost:8000)
make migrate                # apply the database schema
make test                   # run the test suite
```

Health check: `curl localhost:8000/healthz` → `{"status":"ok"}`.
OpenAPI docs: http://localhost:8000/docs

## Make targets

| Target | Purpose |
|---|---|
| `make up` | Build images, start Postgres + API |
| `make down` | Stop and remove containers |
| `make migrate` | Apply Alembic migrations |
| `make makemigration m="..."` | Autogenerate a migration |
| `make test` | Run pytest |
| `make lint` / `make fmt` | Ruff check / format |
| `make ingest` | One ingest+analyze cycle *(Phase 1)* |
| `make demo` | Replay a curated escalation event *(Phase 6)* |

## Repo layout

```
oil-news-alert/
├─ docker-compose.yml      # db + api (worker/frontend added in later phases)
├─ Makefile                # one-command dev workflow
├─ .env.example
├─ backend/
│  ├─ Dockerfile
│  ├─ pyproject.toml       # deps + ruff + pytest config
│  ├─ alembic.ini
│  ├─ app/
│  │  ├─ main.py           # FastAPI app
│  │  ├─ api/              # routers (Phase 4)
│  │  ├─ core/             # settings, logging
│  │  ├─ db/               # models, session, alembic/
│  │  └─ schemas/          # Pydantic request/response (Phase 4)
│  ├─ worker/              # ingest / analyze / alerting (Phases 1–3)
│  ├─ eval/                # golden-set harness (Phase 6)
│  └─ tests/
└─ frontend/               # Next.js + Tailwind (Phase 5)
```

## Build status

- [x] **Phase 0 — Scaffold & infra**: monorepo, Docker Compose (Postgres + API), FastAPI
      skeleton, SQLAlchemy + Alembic, the full data model, tooling (ruff, pre-commit, pytest).
- [ ] Phase 1 — Ingestion (GDELT + RSS + EIA, dedup, scheduler)
- [ ] Phase 2 — Analysis pipeline (prefilter → triage → extraction → score) + eval harness
- [ ] Phase 3 — Alerting engine (matching, event dedup, Telegram/email)
- [ ] Phase 4 — API (REST + SSE)
- [ ] Phase 5 — Web app (Next.js)
- [ ] Phase 6 — Eval, polish, demo replay

## Guardrails

No secrets in git (`.env` is ignored; `.env.example` documents the keys). External model
version strings are pinned. Outbound source domains are allowlisted. External HTTP is
rate-limited with backoff. Ingestion is idempotent. Strictly decision-support — nothing
destructive runs automatically and no trades are placed or recommended.

## Limitations & scaling path (MVP)

The MVP uses free/open data sources and polling. Production would move to streaming ingestion
(Redis Streams / Kafka), licensed wire feeds (Reuters/Bloomberg/Argus/Platts), embedding-based
event clustering with a vector DB, backtesting alerts against historical Brent ticks, and
SSO/RBAC. See the spec for the full scaling discussion.
