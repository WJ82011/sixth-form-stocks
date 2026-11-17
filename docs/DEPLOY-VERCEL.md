# Deploy Market Desk to Vercel

Production URL: https://sixth-form-stocks.vercel.app

The repo root ships static files from `site/` via `vercel.json` (`outputDirectory: "site"`). Production must include `cloud-host.js`, `view-loader.js`, and `demo/snapshot.json`.

## One-time fix (recommended): connect GitHub

1. Open [Vercel → sixth-form-stocks](https://vercel.com/dashboard) → **Settings** → **Git**.
2. **Connect** repository `wj82011/sixth-form-stocks` if it is not linked.
3. Set **Root Directory** to `.` (repository root, not `site/` alone).
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

## Verify production

```bash
curl -sI https://sixth-form-stocks.vercel.app/cloud-host.js | head -1
curl -sI https://sixth-form-stocks.vercel.app/demo/snapshot.json | head -1
```

Both should return `HTTP/2 200`. Open the site Overview tab — charts should load within a few seconds (not stuck on “Reading saved history…”).

## Market data keys (not for Vercel)

Browser/static Vercel **cannot** safely hold `FINNHUB_API_KEY` or `MASSIVE_API_KEY`. Production serves `site/demo/snapshot.json` as a labelled **DEMO DATA** snapshot.

Refresh that snapshot from workers/CI (Cursor secrets or GitHub Actions secrets with those exact names):

```bash
python3 tools/check-demo-provider-keys.py   # boolean presence only
python3 tools/export-demo-snapshot.py
```

Or run Actions → **Refresh demo snapshot**. Mac `server.py` keeps using local `~/.marketdesk-reborn/` keys for live.

## Known config note

`vercel.json` cache headers use `/(.*)\\.(js|css|svg|png|json)`. Nested groups in the `source` pattern break Vercel validation and can block deploys.