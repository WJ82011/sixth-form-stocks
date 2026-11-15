#!/usr/bin/env python3
"""Add curated US common-stock listings from public Nasdaq Trader symbol files."""
from __future__ import annotations

import csv
import io
import json
import pathlib
import re
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'ai_catalog.json'
CHECKED = '2026-11-15'
NASDAQ = 'https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt'
OTHER = 'https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt'

# Liquid / well-known names to prioritise when they appear in symbol files.
CANDIDATE_SYMBOLS = """
GLW MCHP MRVL ON FTNT ZS FTAI DKNG ROST ANSS CDNS SNPS ANET PCAR APD ECL ITW
EMR PH HSY GIS K DPZ YUM CMG USB PNC TFC USB CFG RF STT MET PRU TRV CB AON MMC
BX KKR APO SPGI MCO ICE CME CBOE MSCI DDOG HUBS WDAY VEEV TTD GDDY FSLR ENPH
FSLR CEG VST D HR LDOS AWK ETR EXC NRG HUM CI EL ELV HCA MCK COR BSX EW SYK ZBH
MOH CIEN LVS MGM WYNN PARA FOX CMCSA CHTR TMUS VZ T SIRI LYV MTCH ETSY EBAY W
SNAP ROKU PSKY DKNG RIVN LI NIO XPEV BIDU JD PDD SE MRNA BNTX REGN VIK
""".split()

SKIP_NAME = re.compile(
    r'\b(ETF|ETN|Fund|Trust Units?|Warrant|Right|Unit\b|Notes due|Preferred|Depositary Shares.*%|'
    r'Callable|Subscription Receipt|Bond|Debenture)\b',
    re.I,
)

CATEGORY_HINTS = (
    ('Technology', r'\b(Software|Cloud|Cyber|Semiconductor|Data|Platform|AI|Digital)\b'),
    ('Healthcare', r'\b(Health|Pharma|Bio|Medical|Therapeutic|Diagnostic)\b'),
    ('Banking & finance', r'\b(Bank|Financial|Insurance|Capital|Asset|Credit|Bancorp)\b'),
    ('Energy', r'\b(Energy|Oil|Gas|Petroleum|Solar|Power|Utility)\b'),
    ('Shops & travel', r'\b(Retail|Restaurant|Hotel|Travel|Stores|Shop)\b'),
    ('More US listings', r'.'),
)


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={'User-Agent': 'MarketDesk-Directory/6.9'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read(5_000_000).decode('utf-8', 'replace')


def parse_nasdaq(text: str) -> dict[str, dict]:
    out = {}
    for row in csv.DictReader(io.StringIO(text), delimiter='|'):
        sym = (row.get('Symbol') or '').strip()
        if not sym or row.get('Test Issue') == 'Y' or row.get('ETF') == 'Y':
            continue
        name = (row.get('Security Name') or '').strip()
        if SKIP_NAME.search(name):
            continue
        out[sym] = {
            'symbol': sym,
            'name': short_name(name),
            'category': 'More US listings',
            'exchange': 'Nasdaq',
            'currency': 'USD',
            'listingName': name,
            'depositary': 'Depositary' in name,
            'checkedAt': CHECKED,
            'listingSource': NASDAQ,
        }
    return out


def parse_other(text: str) -> dict[str, dict]:
    out = {}
    for row in csv.DictReader(io.StringIO(text), delimiter='|'):
        sym = (row.get('ACT Symbol') or row.get('NASDAQ Symbol') or '').strip()
        if not sym or row.get('ETF') == 'Y' or row.get('Test Issue') == 'Y':
            continue
        name = (row.get('Security Name') or '').strip()
        if SKIP_NAME.search(name):
            continue
        exchange = {'N': 'NYSE', 'A': 'NYSE American', 'P': 'NYSE Arca', 'Z': 'Cboe BZX'}.get(
            (row.get('Exchange') or '').strip(), 'NYSE',
        )
        out[sym] = {
            'symbol': sym,
            'name': short_name(name),
            'category': 'More US listings',
            'exchange': exchange,
            'currency': 'USD',
            'listingName': name,
            'depositary': 'Depositary' in name,
            'checkedAt': CHECKED,
            'listingSource': OTHER,
        }
    return out


def short_name(full: str) -> str:
    name = re.sub(r'\s+', ' ', full)
    for cut in (
        r'\s*-\s*Common Stock.*',
        r'\s*-\s*Class [A-Z].*',
        r'\s*Common Stock.*',
        r'\s*Ordinary Shares.*',
        r'\s*\(.*\)\s*$',
    ):
        name = re.sub(cut, '', name, flags=re.I).strip()
    return name[:80] or full[:80]


def guess_category(name: str) -> str:
    for label, pattern in CATEGORY_HINTS:
        if re.search(pattern, name, re.I):
            return label
    return 'More US listings'


def main():
    rows = json.loads(CATALOG.read_text())
    have = {r['symbol'] for r in rows}
    listed = {**parse_nasdaq(fetch(NASDAQ)), **parse_other(fetch(OTHER))}
    added = []
    for sym in CANDIDATE_SYMBOLS:
        if sym in have or sym not in listed:
            continue
        entry = listed[sym]
        entry['category'] = guess_category(entry['listingName'])
        added.append(entry)
        have.add(sym)
    if not added:
        print('No new symbols added')
        return
    rows.extend(added)
    rows.sort(key=lambda x: x['symbol'])
    CATALOG.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + '\n')
    print(f'Added {len(added)} listings ({len(rows)} total):', ', '.join(x['symbol'] for x in added))


if __name__ == '__main__':
    main()