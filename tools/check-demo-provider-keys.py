#!/usr/bin/env python3
"""Report whether demo export provider keys are present (boolean only).

Never prints key values. Env names preferred by workers / CI:
  FINNHUB_API_KEY
  MASSIVE_API_KEY

Also accepts the aliases already wired in demo_data_sources.py
(FINNHUB_TOKEN / FINNHUB_KEY, POLYGON_API_KEY / MASSIVE_KEY) and
~/.marketdesk-reborn/{finnhub_key,massive_key} for local Mac runs.
"""
from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import demo_data_sources as providers  # noqa: E402


def main() -> int:
    finnhub = bool(providers.finnhub_key())
    massive = bool(providers.massive_key())
    print(f'FINNHUB_API_KEY present: {finnhub}')
    print(f'MASSIVE_API_KEY present: {massive}')
    if not finnhub or not massive:
        missing = [name for name, ok in (('FINNHUB_API_KEY', finnhub), ('MASSIVE_API_KEY', massive)) if not ok]
        print('Missing (set Cursor Cloud Agent secrets or GitHub Actions secrets): ' + ', '.join(missing))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
