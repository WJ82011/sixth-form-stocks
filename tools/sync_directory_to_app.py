#!/usr/bin/env python3
"""Sync ai_catalog.json into site/stock-directory.json (cacheable listing payload)."""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'ai_catalog.json'
OUT = ROOT / 'site' / 'stock-directory.json'


def main():
    rows = json.loads(CATALOG.read_text())
    OUT.write_text(json.dumps(rows, separators=(',', ':'), ensure_ascii=False))
    print(f'Synced {len(rows)} listings into {OUT}')


if __name__ == '__main__':
    main()