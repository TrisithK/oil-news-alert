# Deploying to Render

This repo ships a [`render.yaml`](./render.yaml) blueprint that provisions the whole system from a
connected GitHub repo: a managed **Postgres**, the **API** (REST + SSE), an optional **worker**
(continuous ingest → analyze → alert), and the **static frontend**.

> You create the Render account and click deploy — that part can't be automated for you. The repo
> is fully prepared so it's a few clicks plus pasting your own secrets.

## What gets created

| Service | Type | Free-tier? |
|---|---|---|
| `oilnews-db` | Postgres 15 | ✅ (expires ~30 days; then recreate) |
| `oilnews-api` | Docker web service (uvicorn) | ✅ (spins down when idle) |
| `oilnews-worker` | Docker background worker | ❌ paid — or use the free alternative below |
| `oilnews-web` | Static site (Next.js export) | ✅ |

## Steps

1. **Push this repo to GitHub** (a private repo is fine).

2. **Render → New → Blueprint → select the repo.** Render reads `render.yaml` and shows the plan.
   Review it; the worker is the only paid line. (For a fully-free deploy, remove the
   `oilnews-worker` service before applying — see *Free vs paid* below.) Click **Apply**.

3. **Wait for the first build.** The API's `preDeployCommand` runs `alembic upgrade head` and seeds
   the news sources + the default alert config into the database automatically.

4. **Add your secrets** (optional but recommended) on the **API** and **worker** services →
   *Environment*:
   - `ANTHROPIC_API_KEY` — go live with real Haiku/Sonnet models. Without it, the offline
     heuristic classifier runs (zero cost). See the README "Going live" section.
   - `TELEGRAM_BOT_TOKEN` (+ `TELEGRAM_DEFAULT_CHAT_ID`), `EIA_API_KEY` — optional.

5. **Wire the frontend to the API.** Once `oilnews-api` is live, copy its URL
   (e.g. `https://oilnews-api.onrender.com`) into the **web** service's `NEXT_PUBLIC_API_BASE`
   env var, then **Manual Deploy** the web service so the value bakes into the static build.
   (`NEXT_PUBLIC_API_TOKEN` is wired to the API's generated bearer token automatically.)
   Optionally tighten `CORS_ORIGINS` on the API to your web URL.

6. **Open the web URL.** Health check: `curl https://oilnews-api.onrender.com/healthz`.
   If the feed is empty, trigger ingestion (next section).

## Triggering ingestion

- **With the worker (paid):** it runs `ingest → analyze → alert` every `INGEST_INTERVAL_SEC`
  automatically. Nothing to do.
- **Free alternative (no worker):** call the manual trigger on a schedule. Point a free cron
  service (e.g. cron-job.org) at it every ~15 minutes:

  ```
  POST https://oilnews-api.onrender.com/api/ingest/run
  Header: Authorization: Bearer <API_BEARER_TOKEN>
  ```

  (Find the token in the API service's *Environment* tab. The endpoint runs one full
  ingest → analyze → alert cycle and makes live external calls.)

  Or just hit it once manually to populate the demo:

  ```bash
  curl -X POST -H "Authorization: Bearer <token>" \
    https://oilnews-api.onrender.com/api/ingest/run
  ```

## Free vs paid

- **Fully free:** DB + API + static frontend. Delete the `oilnews-worker` service from the
  blueprint (or in the dashboard) and use the external-cron trigger above.
- **Always-on:** keep the worker (Render `starter` ≈ a few $/month) for hands-off continuous
  operation.

## Caveats (be honest in the interview)

- **Auth is "auth-lite":** one shared bearer token, and it's visible client-side (any SPA calling
  an API with a static token exposes it). Fine for a demo; production needs per-user auth
  (SSO/RBAC) — already called out as the next step.
- **Free services sleep:** Render's free web service spins down when idle, so the first request
  after a quiet spell is slow and the SSE stream reconnects. Free Postgres expires after ~30 days.
- **Cost control:** the two-tier LLM design (prefilter → Haiku → Sonnet) keeps inference cheap, but
  a live key on a busy worker does spend — set `MAX_ITEMS_PER_CYCLE` / `INGEST_INTERVAL_SEC` to
  bound it.

## Other platforms

The app is plain Docker + a static frontend, so it ports easily: Fly.io (`fly launch` per service +
a Postgres app), Railway, or any VPS running `docker compose` behind Caddy/nginx for HTTPS. The only
platform-specific file here is `render.yaml`; everything else is standard.
