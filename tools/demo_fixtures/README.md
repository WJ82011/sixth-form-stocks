# Demo equity fixtures

`equity_bars.json` holds **distinct historical close / previous-close pairs** (plus short session tips and watchlist daily bars) used by `tools/export-demo-snapshot.py` when Finnhub / Massive keys are not available.

## Preferred refresh (free providers already in the product)

1. **Finnhub free tier** — REST quotes (`c`, `pc`) when `FINNHUB_API_KEY` or `~/.marketdesk-reborn/finnhub_key` is set.
2. **Massive Basic** — daily aggregates when `MASSIVE_API_KEY` / `POLYGON_API_KEY` or `~/.marketdesk-reborn/massive_key` is set.
3. **Coinbase Exchange public REST** — crypto (no key).
4. **FRED public CSV** — macro (no key).

### Worker / CI env names

Use these exact secret names (Cursor Cloud Agent secrets or GitHub Actions repository secrets):

| Name | Purpose |
|------|---------|
| `FINNHUB_API_KEY` | Live equity quotes for export |
| `MASSIVE_API_KEY` | Daily bars for export |

Check presence without printing values:

```bash
python3 tools/check-demo-provider-keys.py
```

Re-run export (also available as Actions → **Refresh demo snapshot**):

```bash
python3 tools/export-demo-snapshot.py
```

Offline (fixture + no network):

```bash
MARKETDESK_DEMO_OFFLINE=1 python3 tools/export-demo-snapshot.py
```

The public Vercel host still labels the bundle as **DEMO DATA / not live**. Do **not** put Finnhub or Massive keys in browser/static Vercel env — the public site stays a refreshed snapshot. Mac `server.py` already reads local key files for live.
