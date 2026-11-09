"""Persistent, one-shot price alerts. SQLite only; never fetches market data."""
import math
import re
import uuid

MAX_ALERTS=100
MAX_HISTORY=2000
MAX_AGE_MS=300000
SOURCES={'finnhub_quote','finnhub_websocket_trade'}
SYMBOL=re.compile(r'^[A-Z0-9][A-Z0-9.\-:_]{0,23}$')

def init(con):
    con.execute('CREATE TABLE IF NOT EXISTS price_alert_meta (id INTEGER PRIMARY KEY, revision INTEGER NOT NULL)')
    con.execute('INSERT OR IGNORE INTO price_alert_meta VALUES(1,0)')
    con.execute('''CREATE TABLE IF NOT EXISTS price_alerts (
        id TEXT PRIMARY KEY, symbol TEXT NOT NULL, direction TEXT NOT NULL,
        target REAL NOT NULL, unit TEXT NOT NULL, status TEXT NOT NULL,
        created_at INTEGER NOT NULL, armed_at INTEGER NOT NULL, arm INTEGER NOT NULL,
        last_ts INTEGER NOT NULL DEFAULT 0, last_received INTEGER,
        last_price REAL, last_source TEXT)''')
    con.execute('''CREATE TABLE IF NOT EXISTS price_alert_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, alert_id TEXT NOT NULL, arm INTEGER NOT NULL,
        symbol TEXT NOT NULL, direction TEXT NOT NULL, target REAL NOT NULL,
        unit TEXT NOT NULL, price REAL NOT NULL, price_ts INTEGER NOT NULL,
        received_at INTEGER NOT NULL, source TEXT NOT NULL,
        UNIQUE(alert_id,arm))''')
    con.execute('CREATE INDEX IF NOT EXISTS alert_symbol_status ON price_alerts(symbol,status)')


def bump(con):
    con.execute('UPDATE price_alert_meta SET revision=revision+1 WHERE id=1')


def positive(value):
    if isinstance(value,bool): raise ValueError('Enter a price above zero.')
    try: value=float(value)
    except (TypeError,ValueError,OverflowError): raise ValueError('Enter a valid target price.')
    if not math.isfinite(value) or not 0 < value <= 1e9:
        raise ValueError('Target price must be above zero and no more than 1 billion.')
    return value


def fields(obj):
    symbol=str(obj.get('symbol','')).strip().upper()
    if not SYMBOL.fullmatch(symbol): raise ValueError('Choose a valid stock symbol.')
    direction=obj.get('direction')
    if direction not in ('above','below'): raise ValueError('Choose at or above, or at or below.')
    unit=obj.get('unit','provider units')
    if unit not in ('USD','provider units'): raise ValueError('Unsupported price unit.')
    return symbol,direction,positive(obj.get('target')),unit


def change(con,obj,now):
    """Caller supplies a transaction; action and observations serialize through SQLite."""
    if not isinstance(obj,dict): raise ValueError('Invalid alert request.')
    action=obj.get('action')
    if action=='create':
        symbol,direction,target,unit=fields(obj)
        existing=con.execute("SELECT id FROM price_alerts WHERE symbol=? AND direction=? AND target=? AND unit=? AND status='armed' LIMIT 1",(symbol,direction,target,unit)).fetchone()
        if existing:return existing[0]
        if con.execute('SELECT count(*) FROM price_alerts').fetchone()[0]>=MAX_ALERTS:
            raise ValueError('You can save up to 100 alerts. Delete one before adding another.')
        ident=uuid.uuid4().hex
        con.execute('INSERT INTO price_alerts VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (ident,symbol,direction,target,unit,'armed',now,now,1,0,None,None,None))
        bump(con)
        return ident
    ident=obj.get('id')
    if not isinstance(ident,str) or not re.fullmatch('[a-f0-9]{32}',ident):
        raise ValueError('Invalid alert ID.')
    row=con.execute('SELECT status FROM price_alerts WHERE id=?',(ident,)).fetchone()
    if not row: raise ValueError('This alert no longer exists. Refresh the list.')
    if action=='pause':
        # Triggered alerts remain triggered until explicitly re-armed.
        if row[0]=='armed':con.execute("UPDATE price_alerts SET status='paused' WHERE id=?",(ident,))
    elif action=='rearm':
        if row[0]=='armed':return ident  # Repeated clicks do not reset an active alert.
        con.execute("UPDATE price_alerts SET status='armed',armed_at=?,arm=arm+1,last_ts=0,last_received=NULL,last_price=NULL,last_source=NULL WHERE id=?",(now,ident))
    elif action=='update':
        symbol,direction,target,unit=fields(obj)
        con.execute("UPDATE price_alerts SET symbol=?,direction=?,target=?,unit=?,status='armed',armed_at=?,arm=arm+1,last_ts=0,last_received=NULL,last_price=NULL,last_source=NULL WHERE id=?",(symbol,direction,target,unit,now,ident))
    elif action=='delete':
        con.execute('DELETE FROM price_alerts WHERE id=?',(ident,))
        # Trigger history keeps its own immutable symbol, target and source.
    else: raise ValueError('Unknown alert action.')
    bump(con)
    return ident


def observe(con,symbol,ts,price,source,received):
    """Evaluate a new observation; duplicates and earlier observations do not fire."""
    if source not in SOURCES or isinstance(ts,bool) or not isinstance(ts,int):return 0
    if ts>received or received-ts>MAX_AGE_MS:return 0
    try: price=positive(price)
    except ValueError:return 0
    fired=0;changed=False
    rows=con.execute("SELECT id,direction,target,unit,armed_at,arm,last_ts FROM price_alerts WHERE symbol=? AND status='armed'",(symbol,)).fetchall()
    for ident,direction,target,unit,armed,arm,last_ts in rows:
        if ts<armed or ts<=last_ts:continue
        changed=True
        con.execute('UPDATE price_alerts SET last_ts=?,last_received=?,last_price=?,last_source=? WHERE id=?',(ts,received,price,source,ident))
        matches=price>=target if direction=='above' else price<=target
        if not matches:continue
        con.execute('''INSERT OR IGNORE INTO price_alert_events
            (alert_id,arm,symbol,direction,target,unit,price,price_ts,received_at,source)
            VALUES(?,?,?,?,?,?,?,?,?,?)''',(ident,arm,symbol,direction,target,unit,price,ts,received,source))
        con.execute("UPDATE price_alerts SET status='triggered' WHERE id=? AND status='armed'",(ident,))
        fired+=1
    if changed:bump(con)
    if fired:
        con.execute('DELETE FROM price_alert_events WHERE id NOT IN (SELECT id FROM price_alert_events ORDER BY id DESC LIMIT ?)',(MAX_HISTORY,))
    return fired


def snapshot(con,now):
    def records(query):
        cur=con.execute(query);names=[x[0] for x in cur.description]
        return [dict(zip(names,row)) for row in cur.fetchall()]
    return {'revision':con.execute('SELECT revision FROM price_alert_meta WHERE id=1').fetchone()[0],'alerts':records('SELECT * FROM price_alerts ORDER BY created_at DESC,id'),
            'events':records('SELECT * FROM price_alert_events ORDER BY id DESC LIMIT 2000'),
            'serverTime':now,'maxAlerts':MAX_ALERTS,'historyLimit':MAX_HISTORY,'maxPriceAgeSeconds':MAX_AGE_MS//1000,
            'notice':'One trigger per arming. Only newly received quote or positive-size trade prices dated at or after arming and no more than five minutes old qualify. No invented prices, crossing times or monitoring while your Mac is off.'}
