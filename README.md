# Oil News Alert — AI Brent-moving news detection (MVP)

An AI system that monitors global news for events likely to move **European oil prices
(ICE Brent)**, scores each item for trading importance and likely price direction, and pushes
alerts to prop traders. A Next.js web app lets traders view the analyzed feed, interrogate *why*
each alert fired, and configure their own thresholds and channels.

> **Decision-support with a human in the loop.** It never places or recommends trades
> automatically.

Built as an interview portfolio piece for a European energy-trading desk — optimized for a clean
end-to-end demo, domain credibility, and architecture that obviously scales.

---

## What it does

1. **Ingests** oil-relevant news on a schedule from GDELT 2.0 (global, keyless), curated RSS
   feeds, and EIA fundamentals — normalized and deduplicated.
2. **Analyzes** each item through a cost-aware, staged pipeline:
   keyword prefilter → **Haiku** relevance triage → **Sonnet** structured signal extraction
   (forced tool call, Pydantic-validated) → **deterministic importance score**.
3. **Alerts** by matching each signal against per-trader configs (threshold, instruments,
   categories, keywords, quiet hours), with **event-level dedup** to fight alert fatigue, and
   delivers in-app (SSE) + Telegram / email.
4. **Shows** it all in a web app: a live feed with an auditable *"Why this score"* breakdown,
   alert history with acknowledge + feedback, config, sources, and a stats dashboard.

An **evaluation harness** over a labeled golden set reports relevance precision/recall and
direction agreement, and a **replay script** simulates a Strait-of-Hormuz escalation on cue.

---

## Architecture

```
                 ┌───────────────────────────────────────────────┐
   Scheduler ───▶│  INGESTION WORKER                              │
  (every N min)  │  GDELT DOC API · RSS feeds · EIA               │
                 │  normalize → dedup (hash/url) → store raw       │
                 └───────────────┬───────────────────────────────┘
                                 ▼
                 ┌───────────────────────────────────────────────┐
                 │  ANALYSIS PIPELINE                              │
                 │  1) keyword prefilter (cheap, no LLM)          │
                 │  2) relevance triage  → Claude Haiku           │
                 │  3) signal extraction → Claude Sonnet (tool)   │
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
dispatch) and the **API** (serves the web app and SSE stream), kept separate so the UI never
blocks on the pipeline.

## Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.11 |
| API | FastAPI + Uvicorn (REST + SSE) |
| Worker | APScheduler (in-process) |
| LLM | Anthropic — Haiku 4.5 (triage) + Sonnet 4.6 (extraction); Opus 4.8 optional |
| Validation | Pydantic v2 (force/repair structured output) |
| DB | Postgres 15 + SQLAlchemy 2.0 + Alembic |
| News | GDELT 2.0 DOC API (free) + curated RSS + EIA Open Data |
| Frontend | Next.js 14 + Tailwind |
| Alerts out | In-app SSE + Telegram bot / SMTP email |
| Dev infra | Docker Compose, Makefile, pytest, ruff |

> **LLM is mock-first.** With no `ANTHROPIC_API_KEY`, a deterministic `HeuristicLLMClient`
> (keyword classifier) stands in, so the entire pipeline, eval, and demo run **offline at zero
> API cost**. Add a key and the real two-tier Haiku/Sonnet client takes over automatically — the
> rest of the system is unchanged.

---

## Quickstart

```bash
cp .env.example .env        # optional: add ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN, EIA_API_KEY
make up                     # build + start Postgres + API (http://localhost:8000)
make migrate                # apply the database schema
make ingest                 # pull live news (GDELT + RSS) into the DB
make analyze                # run the analysis pipeline + fire alerts
make web                    # run the Next.js app (http://localhost:3000)
make demo                   # replay a Strait-of-Hormuz escalation — watch the feed light up
```

Health: `curl localhost:8000/healthz`. OpenAPI docs: http://localhost:8000/docs
(bearer token `devtoken` by default — `Authorize` in `/docs`, or `?token=devtoken` for SSE).

For continuous operation, `make worker` runs the scheduler (ingest → analyze → alert every
`INGEST_INTERVAL_SEC`).

## Going live — real LLM + Telegram

Both are optional; the system runs fully offline without them. Add your own credentials to `.env`
(it's gitignored — never commit secrets) and re-run `make up` so the containers pick up the new
environment.

**Real Anthropic models** (Haiku triage + Sonnet extraction):

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...      # from https://console.anthropic.com -> API Keys
```

```bash
make up           # recreate containers with the key
make llm-check    # one cheap Haiku call to confirm the wiring  -> "LLM wiring OK ✓"
make analyze      # now classifies with the real two-tier models
```

The two-tier design keeps this cheap: the keyword prefilter and Haiku triage drop most volume for
near-nothing, and only survivors reach Sonnet.

**Telegram alerts** (the live "ping" in the demo):

```bash
# .env  — create a bot with @BotFather (/newbot) for the token
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_DEFAULT_CHAT_ID=         # optional; or pass CHAT=<id> to telegram-test
```

```bash
make up                       # recreate containers
make telegram-test            # sends a test message (find your chat id via getUpdates)
make telegram-test CHAT=12345 # ...or test a specific chat id
```

Once `TELEGRAM_DEFAULT_CHAT_ID` is set, `make analyze` / `make worker` route matching alerts to
Telegram automatically (the default config picks the chat id up on the next run, without
overwriting a chat id you set in the Config UI). `make demo` then pings Telegram live.

## Make targets

| Target | Purpose |
|---|---|
| `make up` / `down` | Start / stop Postgres + API |
| `make migrate` | Apply Alembic migrations |
| `make ingest` | One ingest cycle (GDELT + RSS + EIA) |
| `make analyze` | Analyze un-analyzed articles + fire alerts |
| `make alert` | Backfill alerts over already-analyzed data |
| `make worker` | Continuous ingest → analyze → alert loop |
| `make eval` | Golden-set evaluation (precision/recall + direction) |
| `make demo` | Replay the curated escalation event |
| `make web` | Run the Next.js web app |
| `make llm-check` | Verify the live Anthropic key (one cheap call) |
| `make telegram-test` | Send a test Telegram message |
| `make test` / `make lint` | Run pytest (67 tests) / ruff |

---

## How it works

**Taxonomy (drives the classifier).** Each article is classified into a Brent-impact category
(OPEC+ supply, geopolitics, shipping chokepoints, supply outages, sanctions, inventories, macro,
demand, strategic reserves, production, weather, rumor). Each category carries a base weight and a
*typical* direction — a prior, not a rule.

**Importance score (auditable, not a black box).** Models suggest; a deterministic formula
decides, so every score decomposes into the same terms (surfaced in the UI's "Why this score"):

```
importance = 100 * ( 0.35·category_weight + 0.20·magnitude + 0.15·confidence
                   + 0.15·source_tier     + 0.15·novelty )
# scheduled data (e.g. EIA) is scaled by a surprise factor (vs consensus)
```

**Alerting & dedup.** A signal alerts a config only if it clears the threshold and the
instrument/category/keyword/quiet-hours filters. **Event-level dedup** then suppresses a second
alert for the same event category within a cooldown window — the single biggest defense against
alert fatigue, which desks care about more than recall.

---

## Evaluation — "how do you know it works?"

`make eval` runs the labeled golden set (~32 headlines across the taxonomy) and reports relevance
precision/recall/F1 and direction agreement, listing disagreements. Offline (heuristic baseline)
it scores roughly **precision 1.00 / recall 0.96 / direction 0.81** — the disagreements are
honest classifier edge cases the harness surfaces by design.

The honest framing for the interview: for a news→price system the meaningful metric is whether
high-importance alerts correlate with realized Brent moves and whether false positives stay low
enough that traders keep notifications on. The MVP ships the harness and the feedback loop;
validation against realized volatility is the documented next step.

Operational metrics (time-to-alert, alerts/day, category & direction mix, token spend, feedback
ratio) are exposed at `/api/stats` and on the Stats page.

---

## API

`/api/feed` (filterable, paginated), `/api/feed/{id}` (full signal + score breakdown),
`/api/alerts` + `/api/alerts/{id}/ack`, `/api/feedback`, `/api/config` (GET/PUT),
`/api/sources` (+ PATCH), `/api/stats`, `/api/stream` (SSE), `/api/ingest/run`.
Bearer-token auth-lite (SSO/RBAC is the production step). Full schema at `/docs`.

## Project structure

```
oil-news-alert/
├─ docker-compose.yml · Makefile · .env.example
├─ backend/
│  ├─ app/        FastAPI app: main, api/ (routers), core/ (settings, auth, events,
│  │              taxonomy), db/ (models, alembic), schemas/
│  ├─ worker/     ingest/ (gdelt, rss, eia, normalize, dedup) · analyze/ (prefilter,
│  │              triage/extract via llm, score, pipeline) · alerting/ (match, dedup,
│  │              notifier, engine, feedback) · scheduler · run_* entrypoints
│  ├─ eval/       golden_set.jsonl + run_eval.py
│  ├─ scripts/    replay_demo.py
│  └─ tests/      67 tests (unit + DB-backed + API integration)
└─ frontend/      Next.js + Tailwind: app/ (feed, alerts, config, sources, stats),
                  components/, lib/ (typed api client, SSE, formatting)
```

---

## Interview demo script

1. **Frame (30s):** "A desk can't watch every wire. This flags only the news likely to move
   Brent, ranked, with a reason — decision support, human stays in control."
2. **Live feed:** point out importance badges, direction, instruments, and the **"Why this
   score"** breakdown (every score is decomposable; every alert traces to a source).
3. **`make demo`:** a Strait-of-Hormuz escalation streams in → critical bullish-Brent alerts
   appear in the feed (and ping Telegram if configured) within seconds.
4. **Tune config:** raise the threshold / narrow to BRENT → alert volume drops. This is the
   **alert-fatigue** story.
5. **`/docs` + architecture:** the **two-tier model** (cheap triage, expensive extraction),
   event-level dedup, and the explainable scoring formula.
6. **Close on limitations + scaling** — knowing the gap between MVP and production reads as senior.

**Talking points:** cost/latency tradeoffs of the model tiering; controlling false positives;
auditability; data-licensing reality; humans in the loop.

---

## Limitations & scaling path (say this, don't build it)

- **Latency:** replace polling with streaming ingestion (Redis Streams / Kafka) + push-based wire
  feeds.
- **Licensed data:** Reuters/Bloomberg/Argus/Platts feeds + market-data agreements
  (compliance-critical at a real firm).
- **Smarter relevance & dedup:** embeddings + a vector DB to cluster stories into events and
  retrieve similar past events and their realized Brent move (RAG) to calibrate magnitude.
- **Backtesting:** join alerts to historical Brent tick data; measure predictive value and tune
  weights empirically.
- **Surprise modeling:** wire in consensus estimates for scheduled releases (EIA, OPEC/IEA
  reports, macro prints).
- **Breadth:** TTF gas, power, crack and Brent–WTI spreads.
- **Ops:** LLM observability, eval-drift monitoring, websockets at scale, SSO/RBAC, full audit log.

## Guardrails

No secrets in git (`.env` ignored; `.env.example` documents keys). Model version strings pinned.
Outbound source domains allowlisted. External HTTP rate-limited with backoff (network/429/5xx
only). Ingestion idempotent. Structured LLM output is forced + Pydantic-validated + repair-or-
discard; rationale always cites the source. Strictly decision-support — nothing destructive runs
automatically and no trades are placed or recommended.

## Build status

All phases complete: scaffold · ingestion · analysis pipeline + eval · alerting · REST/SSE API ·
web app · demo. **67 tests, ruff-clean.** Verified end-to-end on live data (the Strait-of-Hormuz /
Iran / OPEC cluster surfaces as the top-importance bullish-Brent signals).
