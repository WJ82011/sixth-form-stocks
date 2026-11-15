#!/usr/bin/env python3
"""Build a static symbol+name index for public listing search (no prices)."""
from __future__ import annotations

import csv
import io
import json
import pathlib
import re
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'site' / 'listings-index.json'
NASDAQ = 'https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt'
OTHER = 'https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt'
CHECKED = 1731657600000  # 2026-11-15 UTC ms for metadata


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={'User-Agent': 'MarketDesk-Directory/6.9'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read(8_000_000).decode('utf-8', 'replace')


SKIP = re.compile(r'\b(ETF|ETN|Warrant|Right|Unit\b|Notes due|Preferred)\b', re.I)


def main():
    rows = []
    seen = set()
    for url, field in ((NASDAQ, 'Symbol'), (OTHER, 'ACT Symbol')):
        text = fetch(url)
        for row in csv.DictReader(io.StringIO(text), delimiter='|'):
            sym = (row.get(field) or row.get('NASDAQ Symbol') or '').strip()
            name = (row.get('Security Name') or '').strip()
            if not sym or sym in seen or row.get('Test Issue') == 'Y' or row.get('ETF') == 'Y':
                continue
            if SKIP.search(name):
                continue
            if not re.match(r'^[A-Z0-9][A-Z0-9.\-]{0,23}$', sym):
                continue
            seen.add(sym)
            rows.append({'symbol': sym, 'name': name[:160]})
    rows.sort(key=lambda x: x['symbol'])
    payload = {
        'version': 1,
        'checkedAt': CHECKED,
        'total': len(rows),
        'source': 'Nasdaq Trader symbol directories',
        'notice': 'Listing discovery only. No prices or financial coverage implied.',
        'rows': rows,
    }
    OUT.write_text(json.dumps(payload, separators=(',', ':')) + '\n')
    print(f'Wrote {len(rows)} listings to {OUT} ({OUT.stat().st_size // 1024} KB)')


if __name__ == '__main__':
    main()