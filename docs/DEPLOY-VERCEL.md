# Deploy Market Desk to Vercel

Production URL: https://sixth-form-stocks.vercel.app

The repo root ships static files from `site/` via `vercel.json` (`outputDirectory: "site"`) plus thin serverless routes under `api/` (`/api/quotes`, `/api/quote`). Production must include `public-host-mode.js`, `cloud-host.js`, `view-loader.js`, and `demo/snapshot.json`.

Public mode auto-enables on `*.vercel.app`, `*.tmp.now`, `*.now.sh`, and hosts containing `sixth-form-stocks` — **no `?demo=1` required**. Cold load of bare `/` should show Overview with prices. Status pill reads **LIVE QUOTES (CACHED)** when the serverless proxy has a Finnhub key, otherwise honest **DEMO DATA** from the bundled snapshot. Keep `?demo=1` only for local static checks; Mac `server.py` on `localhost:8765` stays live; `?demo=local` on loopback forces Mac-shaped static.

## One-time fix (recommended): connect GitHub

1. Open [Vercel → sixth-form-stocks](https://vercel.com/dashboard) → **Settings** → **Git**.
2. **Connect** repository `wj82011/sixth-form-stocks` if it is not linked.
3. Set **Root Directory** to `.` (repository root, not `site/` alone) so both `site/` and `api/` deploy.
4. Set **Production Branch** to `main`.
5. Turn off **Include files outside the root** only if Root Directory is wrong; with root `.`, defaults are fine.
6. Click **Deployments** → **Redeploy** latest (or push to `main` after merge).

## GitHub Action (auto + manual redeploy)

Workflow: `.github/workflows/vercel-production.yml` runs on every `main` push and supports **Run workflow** in the Actions tab.

Add these **repository secrets** (Settings → Secrets and variables → Actions):

| Secret | Where to find it |
|--------|------------------|
| `VERCEL_TOKEN` | Vercel → Account Settings → **Tokens** → Create |
| `VERCEL_ORG_ID` | Project → Settings → General → **Project ID** section (Team / Personal ID) |
| `VERCEL_PROJECT_ID` | Same page → **Project ID** |

**Alternative (hook only):** Project → Settings → **Deploy Hooks** → Create hook for `main` → save URL as `VERCEL_DEPLOY_HOOK`. Requires the project already linked to this GitHub repo.

## Local one-shot redeploy (CLI)

```bash
npm install -g vercel
vercel login
cd /path/to/sixth-form-stocks
vercel link   # pick sixth-form-stocks
vercel deploy --prod
```

Optional local API check (uses project env if linked):

```bash
vercel dev
# then: curl -s 'http://127.0.0.1:3000/api/quotes?symbols=AAPL,NVDA' | head
```

## Verify production

Critical assets (all must be **200**):

```bash
curl -sI https://sixth-form-stocks.vercel.app/public-host-mode.js | head -1
curl -sI https://sixth-form-stocks.vercel.app/cloud-host.js | head -1
curl -sI https://sixth-form-stocks.vercel.app/demo/snapshot.json | head -1
curl -sI https://sixth-form-stocks.vercel.app/view-loader.js | head -1
curl -sI 'https://sixth-form-stocks.vercel.app/api/quotes?symbols=AAPL' | head -1
```

Bare `/` (no query string) — admissions URL:

1. Open https://sixth-form-stocks.vercel.app/ (not `?demo=1`).
2. Within a few seconds Overview shows prices/charts (not stuck on “Reading saved history…”).
3. Status pill reads **LIVE QUOTES (CACHED)** when `FINNHUB_API_KEY` is set on the Vercel project, otherwise **DEMO DATA**.
4. Sidebar tagline / footer mention **PUBLIC PORTFOLIO**, not **LOCAL WORKSTATION** / **FEED OFFLINE**.

Optional local static check (force-on without a Vercel hostname):

```bash
cd site && python3 -m http.server 8777 --bind 127.0.0.1
# http://127.0.0.1:8777/?demo=1
# http://127.0.0.1:8777/?demo=local  → Mac-shaped shell (no snapshot intercept)
```

### Stale-domain symptoms (redeploy needed)

| Symptom | Likely cause |
|---------|----------------|
| `/cloud-host.js` or `/demo/snapshot.json` → **404** | Production still on an old CLI deploy; reconnect Git / redeploy `main` |
| Bare `/` shows **FEED OFFLINE** / empty Overview | Missing or stale `cloud-host.js` / snapshot, or Root Directory wrong |
| UI still says **LOCAL WORKSTATION** on vercel.app | Old bundle without public-host auto mode — redeploy current `main` |
| `/api/quotes` → **404** | Root Directory set to `site/` only, or redeploy needed after P1-a |

## Market data keys

**Cursor Cloud Agent secrets ≠ Vercel project environment variables.**  
Workers and GitHub Actions can see Cursor / Actions secrets. The public Vercel serverless routes only see names you add under the **Vercel project**. Set the same **names** in both places; never paste values into chat.

### Snapshot refresh (CI / Mac)

Refresh from workers/CI (Cursor secrets or GitHub Actions secrets with these exact names):

| Secret name | Use |
|-------------|-----|
| `FINNHUB_API_KEY` | Snapshot export + serverless `/api/quotes` |
| `MASSIVE_API_KEY` | Snapshot daily bars / later optional candles proxy |

```bash
python3 tools/check-demo-provider-keys.py   # boolean presence only — never prints values
python3 tools/export-demo-snapshot.py
```

Or run Actions → **Refresh demo snapshot**. Mac `server.py` keeps using local `~/.marketdesk-reborn/` keys for live.

### Vercel project env (required for live public quotes)

Add these on **Vercel → sixth-form-stocks → Settings → Environment Variables** for **Production** (and Preview if you want preview deploys live):

| Name | Required | Notes |
|------|----------|--------|
| `FINNHUB_API_KEY` | Yes for live quotes | Same name as Cursor / Actions. Server-only — never `NEXT_PUBLIC_` / `VITE_`. |
| `MASSIVE_API_KEY` | Optional for now | Presence is reported; candles proxy comes later. |

Steps:

1. Copy the value from wherever you already store Finnhub (Cursor Dashboard Secrets or `~/.marketdesk-reborn/finnhub_key`) — do **not** paste it into Slack/chat.
2. Vercel → Project → **Settings** → **Environment Variables** → **Add**.
3. Name exactly `FINNHUB_API_KEY` (and optionally `MASSIVE_API_KEY`).
4. Scope: Production (and Preview if desired).
5. **Redeploy** production so the new env is attached to the serverless functions.

Without `FINNHUB_API_KEY` on Vercel, `/api/quotes` still returns **200** with labelled `demoMode: true` snapshot items — the desk stays honest rather than empty.

Never put these keys in the browser, client bundles, `site/`, or chat.

## Known config note

`vercel.json` cache headers use `/(.*)\\.(js|css|svg|png|json)`. Nested groups in the `source` pattern break Vercel validation and can block deploys. Keep Root Directory at `.` so `api/*.js` and `site/` ship together.
