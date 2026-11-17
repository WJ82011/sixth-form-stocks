# Demo equity fixtures

`equity_bars.json` holds **distinct historical close / previous-close pairs** (plus short session tips and watchlist daily bars) used by `tools/export-demo-snapshot.py` when Finnhub / Massive keys are not available.

## Preferred refresh (free providers already in the product)

1. **Finnhub free tier** — REST quotes (`c`, `pc`) when `FINNHUB_API_KEY` or `~/.marketdesk-reborn/finnhub_key` is set.
2. **Massive Basic** — daily aggregates when `MASSIVE_API_KEY` / `POLYGON_API_KEY` or `~/.marketdesk-reborn/massive_key` is set.
3. **Coinbase Exchange public REST** — crypto (no key).
4. **FRED public CSV** — macro (no key).

Run:

```bash
python3 tools/export-demo-snapshot.py
```

Offline (fixture + no network):

```bash
MARKETDESK_DEMO_OFFLINE=1 python3 tools/export-demo-snapshot.py
```

The public Vercel host still labels the bundle as **DEMO DATA / not live**.
