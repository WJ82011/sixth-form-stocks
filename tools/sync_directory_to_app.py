#!/usr/bin/env python3
"""Embed ai_catalog.json into site/app.js STOCK_DIRECTORY constant."""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'ai_catalog.json'
APP = ROOT / 'site' / 'app.js'


def main():
    rows = json.loads(CATALOG.read_text())
    blob = json.dumps(rows, separators=(',', ':'), ensure_ascii=False)
    text = APP.read_text()
    pattern = re.compile(
        r'(const STOCK_DIRECTORY = Object\.freeze\()\[.*?\](\);)',
        re.DOTALL,
    )
    if not pattern.search(text):
        raise SystemExit('STOCK_DIRECTORY block not found in app.js')
    text = pattern.sub(rf'\1{blob}\2', text, count=1)
    APP.write_text(text)
    print(f'Synced {len(rows)} listings into {APP}')


if __name__ == '__main__':
    main()