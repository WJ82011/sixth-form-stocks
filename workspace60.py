"""Named research workspaces. Switching reads a saved copy and does not write a draft."""
import contextlib
import hashlib
import json
import re

METHOD = 'research-workspace-v6.0'
NAME = re.compile(r'^[\w][\w .&-]{0,40}$')
SYMBOL = re.compile(r'^[A-Z0-9][A-Z0-9.-]{0,14}$')
PRESETS = (
    {'name': 'Gaming companies', 'symbols': ['TTWO', 'RBLX', 'U', 'SONY'], 'chartRange': '1D',
     'view': 'home', 'comparisonSymbols': ['TTWO', 'RBLX', 'U', 'SONY'], 'useWatchlist': False},
    {'name': 'Crypto', 'symbols': ['BTC-USD', 'ETH-USD', 'SOL-USD'], 'chartRange': '1D',
     'view': 'crypto', 'comparisonSymbols': [], 'useWatchlist': False},
    {'name': 'Daily review', 'symbols': [], 'chartRange': '1D', 'view': 'home',
     'comparisonSymbols': [], 'useWatchlist': True},
)
AREAS = (
    ('navigation', 'site/look43.js'), ('companies', 'site/app.js'), ('crypto', 'crypto38.py'),
    ('charts', 'site/chart43.js'), ('heatmaps', 'site/heatmap.js'), ('tape', 'site/tape.js'),
    ('replay', 'replay43.py'), ('financials', 'financials.py'), ('intelligence', 'ask48.py'),
    ('forecasts', 'site/crypto57.js'), ('scenarios', 'scenario53.py'), ('scans', 'scanner55.py'),
    ('alerts', 'price_alerts.py'), ('portfolio', 'stress58.py'), ('research', 'journal49.py'),
    ('reports', 'pack59.py'), ('settings', 'site/desk50.js'), ('backups', 'desk50.py'),
    ('workspaces', 'workspace60.py'), ('annotations', 'annotate60.py'), ('overview', 'overview60.py'),
    ('investigations', 'desk61.py'), ('chart board', 'site/desk61.js'),
)


def init(con):
    con.execute('''CREATE TABLE IF NOT EXISTS workspace60(
        id TEXT PRIMARY KEY, name TEXT NOT NULL, body TEXT NOT NULL, updated_at INTEGER NOT NULL)''')
    con.execute('''CREATE TABLE IF NOT EXISTS workspace60_active(id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL)''')


def _id(name):
    return hashlib.sha256(name.encode()).hexdigest()[:12]


def _symbols(values):
    found = []
    for value in values or []:
        symbol = str(value or '').upper().strip()
        if symbol and SYMBOL.fullmatch(symbol) and symbol not in found:
            found.append(symbol)
    return found[:12]


def _body(obj, previous=None):
    name = str((obj or {}).get('name') or (previous or {}).get('name') or '').strip()
    if not NAME.fullmatch(name):
        raise ValueError('Name the workspace with letters, numbers and spaces.')
    layout = (obj or {}).get('layout')
    width = None
    if isinstance(layout, dict) and layout.get('side') not in (None, ''):
        width = int(layout.get('side'))
        if width < 220 or width > 480:
            raise ValueError('Panel width stays between 220 and 480.')
    links = (obj or {}).get('links') if isinstance((obj or {}).get('links'), dict) else {}
    return {
        'name': name,
        'symbols': _symbols((obj or {}).get('symbols', (previous or {}).get('symbols'))),
        'comparisonSymbols': _symbols((obj or {}).get('comparisonSymbols', (previous or {}).get('comparisonSymbols'))),
        'chartRange': str((obj or {}).get('chartRange') or (previous or {}).get('chartRange') or '1D')[:8],
        'view': str((obj or {}).get('view') or (previous or {}).get('view') or 'home')[:24],
        'useWatchlist': bool((obj or {}).get('useWatchlist', (previous or {}).get('useWatchlist'))),
        'layout': {'side': width},
        'links': {
            'packId': str(links.get('packId') or '')[:32],
            'journalSymbol': str(links.get('journalSymbol') or '').upper()[:12],
            'note': str(links.get('note') or '')[:240],
        },
    }


def ensure(g):
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        count = con.execute('SELECT COUNT(*) FROM workspace60').fetchone()[0]
        if count:
            return
        for preset in PRESETS:
            body = _body(preset)
            con.execute('INSERT INTO workspace60(id,name,body,updated_at) VALUES(?,?,?,?)',
                        (_id(body['name']), body['name'], json.dumps(body), 1))


def listed(g):
    ensure(g)
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        rows = con.execute('SELECT id,body,updated_at FROM workspace60 ORDER BY name').fetchall()
        active = con.execute('SELECT workspace_id FROM workspace60_active WHERE id=?', ('current',)).fetchone()
    workspaces = []
    for ident, body, updated in rows:
        parsed = json.loads(body)
        parsed['id'] = ident
        parsed['updatedAt'] = updated
        workspaces.append(parsed)
    return {'workspaces': workspaces, 'activeId': active[0] if active else '', 'method': METHOD}


def save(g, obj, now_ms):
    ensure(g)
    previous = None
    if obj.get('id'):
        try:
            previous = read(g, obj.get('id'))
        except ValueError:
            previous = None
    body = _body(obj, previous)
    ident = previous['id'] if previous else _id(body['name'])
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        con.execute('INSERT INTO workspace60(id,name,body,updated_at) VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name, body=excluded.body, updated_at=excluded.updated_at',
                    (ident, body['name'], json.dumps(body), int(now_ms)))
        con.execute('INSERT INTO workspace60_active(id,workspace_id) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET workspace_id=excluded.workspace_id', ('current', ident))
    body['id'] = ident
    body['updatedAt'] = int(now_ms)
    return body


def read(g, ident):
    ensure(g)
    with contextlib.closing(g['db_connection']()) as con:
        row = con.execute('SELECT body,updated_at FROM workspace60 WHERE id=?', (str(ident or ''),)).fetchone()
    if not row:
        raise ValueError('That workspace is not saved.')
    body = json.loads(row[0])
    body['id'] = ident
    body['updatedAt'] = row[1]
    return body


def activate(g, ident):
    """Point at a saved workspace. The saved symbols stay as they were stored."""
    body = read(g, ident)
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        con.execute('INSERT INTO workspace60_active(id,workspace_id) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET workspace_id=excluded.workspace_id', ('current', body['id']))
    body['notice'] = 'Opened the saved workspace. An unsaved draft on screen was not written over this copy.'
    body['since'] = changed(g, body)
    return body


def changed(g, body):
    """What was saved after this workspace's last update. Reads stored records only."""
    since = int(body.get('updatedAt') or 0)
    symbols = body.get('symbols') or []
    packs = []
    try:
        with contextlib.closing(g['db_connection']()) as con:
            for symbol in symbols:
                rows = con.execute('SELECT id,created_at FROM pack59 WHERE symbol=? AND created_at>? ORDER BY created_at', (symbol, since)).fetchall()
                packs.extend({'id': row[0], 'symbol': symbol, 'createdAt': row[1]} for row in rows)
    except Exception:
        packs = []
    return {
        'since': since,
        'packs': packs,
        'notice': 'Changes are research packs saved after this workspace was last updated.' if packs else 'No research pack was saved after this workspace was last updated.',
    }


def question(text):
    words = str(text or '').lower()
    return 'workspace' in words and ('change' in words or 'resume' in words or 'left' in words)
