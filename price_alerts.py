"""Persistent price alerts. SQLite only; never fetches market data.

Level alerts stay one-shot. Crossing, percent and unusual-session rules record a
crossing only after this server has seen the condition change. Replay prices are
not a source.
"""
import datetime as dt
import math
import re
import uuid
from zoneinfo import ZoneInfo

import events42

MAX_ALERTS=100
MAX_HISTORY=2000
MAX_AGE_MS=300000
GAP_MS=15*60*1000
MIN_SESSIONS=20
NY=ZoneInfo('America/New_York')
SOURCES={'finnhub_quote','finnhub_websocket_trade','coinbase_ticker'}
KINDS={'level','cross','percent','unusual'}
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
    present={row[1] for row in con.execute('PRAGMA table_info(price_alerts)')}
    for name,decl in (
        ('kind',"TEXT NOT NULL DEFAULT 'level'"),('frequency',"TEXT NOT NULL DEFAULT 'once'"),
        ('condition_met','INTEGER'),('reference_price','REAL'),('reference_date','TEXT'),
        ('sample_size','INTEGER'),('evaluation_note','TEXT')):
        if name not in present:con.execute(f'ALTER TABLE price_alerts ADD COLUMN {name} {decl}')
    events={row[1] for row in con.execute('PRAGMA table_info(price_alert_events)')}
    for name,decl in (
        ('comparison_price','REAL'),('comparison_ts','INTEGER'),('match_type',"TEXT NOT NULL DEFAULT 'level'"),
        ('rule_text','TEXT'),('chart_range','TEXT'),('start_date','TEXT'),('end_date','TEXT')):
        if name not in events:con.execute(f'ALTER TABLE price_alert_events ADD COLUMN {name} {decl}')


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
    kind=obj.get('kind') or 'level'
    if kind not in KINDS: raise ValueError('Choose a level, crossing, percent or unusual-session alert.')
    direction=obj.get('direction')
    if direction not in ('above','below'): raise ValueError('Choose at or above, or at or below.')
    frequency=obj.get('frequency') or 'once'
    if frequency not in ('once','repeat'): raise ValueError('Choose once or repeat.')
    if kind=='level': frequency='once'
    unit=obj.get('unit','provider units')
    if kind in ('percent','unusual'): unit='percent'
    elif unit not in ('USD','provider units'): raise ValueError('Unsupported price unit.')
    if kind=='unusual': target=90.0
    elif kind=='percent':
        target=positive(obj.get('target'))
        if target>100: raise ValueError('Use a percentage from just above zero to 100.')
    else: target=positive(obj.get('target'))
    return symbol,kind,direction,target,unit,frequency


def saved_close(con,symbol,day):
    try: rows=con.execute('SELECT ts_ms,c FROM massive_daily_bars WHERE symbol=? ORDER BY ts_ms',(symbol,)).fetchall()
    except Exception: return None
    for ts,price in rows:
        if isinstance(price,bool) or not isinstance(price,(int,float)) or not math.isfinite(price) or price<=0: continue
        if dt.datetime.fromtimestamp(ts/1000,NY).date().isoformat()==day: return float(price)
    return None


def rule_text(kind,direction,target,unit,reference_price,reference_date,sample):
    if kind=='cross': return f"Crosses {'above' if direction=='above' else 'below'} {target:g} {unit}."
    if kind=='percent': return f"{'Up' if direction=='above' else 'Down'} {target:g}% from the saved close of {reference_price:g} on {reference_date}."
    if kind=='unusual': return f"Completed-session move larger than 90% of the previous {sample or 0} valid sessions. A move this large needs at least {MIN_SESSIONS} earlier sessions, and a split-sized jump is not treated as a signal."
    return f"{'At or above' if direction=='above' else 'At or below'} {target:g} {unit}."


def change(con,obj,now):
    """Caller supplies a transaction; action and observations serialize through SQLite."""
    if not isinstance(obj,dict): raise ValueError('Invalid alert request.')
    action=obj.get('action')
    if action=='create':
        symbol,kind,direction,target,unit,frequency=fields(obj)
        reference_price=reference_date=None
        if kind=='percent':
            reference_date=str(obj.get('referenceDate') or '')
            try: dt.date.fromisoformat(reference_date)
            except ValueError: raise ValueError('Choose the date of the saved close to compare with.')
            reference_price=obj.get('referencePrice')
            reference_price=saved_close(con,symbol,reference_date) if reference_price in (None,'') else positive(reference_price)
            if not reference_price: raise ValueError('No saved close on that date. The percent alert was not armed.')
        existing=con.execute("SELECT id FROM price_alerts WHERE symbol=? AND direction=? AND target=? AND unit=? AND kind=? AND status='armed' LIMIT 1",(symbol,direction,target,unit,kind)).fetchone()
        if existing:return existing[0]
        if con.execute('SELECT count(*) FROM price_alerts').fetchone()[0]>=MAX_ALERTS:
            raise ValueError('You can save up to 100 alerts. Delete one before adding another.')
        ident=uuid.uuid4().hex
        con.execute('''INSERT INTO price_alerts
            (id,symbol,direction,target,unit,status,created_at,armed_at,arm,last_ts,kind,frequency,reference_price,reference_date,evaluation_note)
            VALUES(?,?,?,?,?,?,?,?,?,0,?,?,?,?,?)''',
            (ident,symbol,direction,target,unit,'armed',now,now,1,kind,frequency,reference_price,reference_date,
             f'Unusual-session alerts wait for {MIN_SESSIONS} valid earlier sessions.' if kind=='unusual' else None))
        bump(con)
        return ident
    ident=obj.get('id')
    if not isinstance(ident,str) or not re.fullmatch('[a-f0-9]{32}',ident):
        raise ValueError('Invalid alert ID.')
    row=con.execute('SELECT status,COALESCE(kind,\'level\') FROM price_alerts WHERE id=?',(ident,)).fetchone()
    if not row: raise ValueError('This alert no longer exists. Refresh the list.')
    if action=='pause':
        # Triggered alerts remain triggered until explicitly re-armed.
        if row[0]=='armed':con.execute("UPDATE price_alerts SET status='paused' WHERE id=?",(ident,))
    elif action=='rearm':
        if row[0]=='armed':return ident  # Repeated clicks do not reset an active alert.
        con.execute("UPDATE price_alerts SET status='armed',armed_at=?,arm=arm+1,last_ts=0,last_received=NULL,last_price=NULL,last_source=NULL,condition_met=NULL"+(',reference_date=NULL,sample_size=NULL' if row[1]=='unusual' else '')+" WHERE id=?",(now,ident))
    elif action=='frequency':
        frequency=obj.get('frequency')
        if frequency not in ('once','repeat'): raise ValueError('Choose once or repeat.')
        kind=con.execute('SELECT COALESCE(kind,\'level\') FROM price_alerts WHERE id=?',(ident,)).fetchone()[0]
        con.execute('UPDATE price_alerts SET frequency=? WHERE id=?',('once' if kind=='level' else frequency,ident))
    elif action=='update':
        symbol,kind,direction,target,unit,frequency=fields(obj)
        con.execute("UPDATE price_alerts SET symbol=?,direction=?,target=?,unit=?,kind=?,frequency=?,status='armed',armed_at=?,arm=arm+1,last_ts=0,last_received=NULL,last_price=NULL,last_source=NULL,condition_met=NULL,evaluation_note=NULL WHERE id=?",(symbol,direction,target,unit,kind,frequency,now,ident))
    elif action=='delete':
        con.execute('DELETE FROM price_alerts WHERE id=?',(ident,))
        # Trigger history keeps its own immutable symbol, target and source.
    else: raise ValueError('Unknown alert action.')
    bump(con)
    return ident


def _record(con,row,price,ts,received,source,match,comparison,comparison_ts,text,chart,start,end):
    ident,arm,symbol,direction,target,unit,frequency=row
    con.execute('''INSERT OR IGNORE INTO price_alert_events
        (alert_id,arm,symbol,direction,target,unit,price,price_ts,received_at,source,comparison_price,comparison_ts,match_type,rule_text,chart_range,start_date,end_date)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (ident,arm,symbol,direction,target,unit,price,ts,received,source,comparison,comparison_ts,match,text,chart,start,end))
    if match=='crossing' and frequency=='once':
        con.execute("UPDATE price_alerts SET status='triggered',arm=arm+1,condition_met=1,evaluation_note=NULL WHERE id=? AND status='armed'",(ident,))
    else:
        con.execute("UPDATE price_alerts SET arm=arm+1,condition_met=?,evaluation_note=NULL WHERE id=? AND status='armed'",(1 if match!='reset' else 0,ident))
    return 1 if match=='crossing' else 0


def observe(con,symbol,ts,price,source,received):
    """Evaluate a new quote or trade. Replay and daily bars do not enter here."""
    if source not in SOURCES or isinstance(ts,bool) or not isinstance(ts,int):return 0
    if ts>received or received-ts>MAX_AGE_MS:
        con.execute("UPDATE price_alerts SET evaluation_note=? WHERE symbol=? AND status='armed'",('The latest price is stale or dated ahead of this server, so it was not evaluated.',symbol))
        bump(con)
        return 0
    try: price=positive(price)
    except ValueError:return 0
    fired=0;changed=False
    rows=con.execute('''SELECT id,direction,target,unit,armed_at,arm,last_ts,COALESCE(kind,'level'),COALESCE(frequency,'once'),condition_met,reference_price,reference_date,last_received
        FROM price_alerts WHERE symbol=? AND status='armed' ''',(symbol,)).fetchall()
    for ident,direction,target,unit,armed,arm,last_ts,kind,frequency,met,reference,reference_date,last_received in rows:
        if ts<armed or ts<=last_ts:continue
        changed=True
        con.execute('UPDATE price_alerts SET last_ts=?,last_received=?,last_price=?,last_source=? WHERE id=?',(ts,received,price,source,ident))
        if kind=='level':
            matches=price>=target if direction=='above' else price<=target
            if not matches:continue
            con.execute('''INSERT OR IGNORE INTO price_alert_events
                (alert_id,arm,symbol,direction,target,unit,price,price_ts,received_at,source,comparison_price,match_type,rule_text,chart_range)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (ident,arm,symbol,direction,target,unit,price,ts,received,source,target,'level',rule_text('level',direction,target,unit,None,None,None),'1D'))
            con.execute("UPDATE price_alerts SET status='triggered' WHERE id=? AND status='armed'",(ident,))
            fired+=1
            continue
        if kind=='unusual':
            continue
        if kind=='percent':
            if not reference: 
                con.execute('UPDATE price_alerts SET evaluation_note=? WHERE id=?',('The comparison close is missing, so this alert was not evaluated.',ident))
                continue
            change=(price/reference-1)*100
            matches=change>=target if direction=='above' else change<=-target
            compared,compared_ts=reference,None
        else:
            matches=price>=target if direction=='above' else price<=target
            compared,compared_ts=target,None
        gap=last_received is None or received-int(last_received)>GAP_MS
        if met==1 and matches: continue
        if matches and (met is None or gap):
            fired+=_record(con,(ident,arm,symbol,direction,target,unit,frequency),price,ts,received,source,'after_gap',compared,compared_ts,rule_text(kind,direction,target,unit,reference,reference_date,None),'1M',reference_date,None)
            continue
        if met==0 and matches:
            fired+=_record(con,(ident,arm,symbol,direction,target,unit,frequency),price,ts,received,source,'crossing',compared,compared_ts,rule_text(kind,direction,target,unit,reference,reference_date,None),'1M',reference_date,None)
        elif not matches:
            con.execute('UPDATE price_alerts SET condition_met=0,evaluation_note=NULL WHERE id=?',(ident,))
    if changed:bump(con)
    if fired:
        con.execute('DELETE FROM price_alert_events WHERE id NOT IN (SELECT id FROM price_alert_events ORDER BY id DESC LIMIT ?)',(MAX_HISTORY,))
    return fired


def observe_sessions(con,symbol,now):
    """Score completed-session alerts from saved closes. Quotes are not used."""
    import crypto38
    if symbol in crypto38.PRODUCTS:
        con.execute("UPDATE price_alerts SET evaluation_note=? WHERE symbol=? AND kind='unusual' AND status='armed'",
                    ('This crypto market uses completed UTC candles, not the New York equity calendar.', symbol))
        return 0
    rows=con.execute('''SELECT id,direction,target,unit,arm,COALESCE(frequency,'once'),condition_met,reference_date
        FROM price_alerts WHERE symbol=? AND status='armed' AND kind='unusual' ''',(symbol,)).fetchall()
    if not rows:return 0
    try: saved=con.execute('SELECT ts_ms,c FROM massive_daily_bars WHERE symbol=? ORDER BY ts_ms',(symbol,)).fetchall()
    except Exception: return 0
    points=[]
    for ts,price in saved:
        if isinstance(price,bool) or not isinstance(price,(int,float)) or not math.isfinite(price) or price<=0: continue
        day=dt.datetime.fromtimestamp(ts/1000,NY).date()
        points.append((day,float(price),int(ts)))
    if len(points)<2:
        con.execute("UPDATE price_alerts SET evaluation_note=? WHERE symbol=? AND kind='unusual' AND status='armed'",('Not enough saved closes to judge a session move.',symbol))
        bump(con);return 0
    *earlier,prev,last=points
    sample=[]
    for left,right in zip(points,points[1:-1]):
        if left[1]>0 and abs(math.log(right[1]/left[1]))<=.7: sample.append(abs(right[1]/left[1]-1)*100)
    fired=0
    for ident,direction,target,unit,arm,frequency,met,seen in rows:
        if seen==last[0].isoformat(): continue
        if abs(math.log(last[1]/prev[1]))>.7:
            con.execute('UPDATE price_alerts SET reference_date=?,sample_size=?,evaluation_note=? WHERE id=?',(last[0].isoformat(),len(sample),'This move is large enough to be a split or a bad print. It was not treated as an unusual session. Saved prices were not changed.',ident))
            continue
        if len(sample)<MIN_SESSIONS:
            con.execute('UPDATE price_alerts SET reference_date=?,sample_size=?,evaluation_note=? WHERE id=?',(last[0].isoformat(),len(sample),f'Needs {MIN_SESSIONS} valid earlier session moves. {len(sample)} are saved, so this alert is not enabled.',ident))
            continue
        ordered=sorted(sample); rank=ordered[max(0,math.ceil(.9*len(ordered))-1)]
        move=abs(last[1]/prev[1]-1)*100; matches=move>rank
        gap=events42.previous_session(last[0])!=prev[0]
        text=rule_text('unusual',direction,target,unit,prev[1],prev[0].isoformat(),len(sample))+f' This session moved {move:.2f}%. The 90th percentile of the earlier sample was {rank:.2f}%.'
        con.execute('UPDATE price_alerts SET sample_size=?,reference_date=?,reference_price=? WHERE id=?',(len(sample),last[0].isoformat(),prev[1],ident))
        if met==1 and matches: continue
        if matches and (met is None or gap):
            fired+=_record(con,(ident,arm,symbol,direction,target,unit,frequency),last[1],last[2],now,'saved_daily_close','after_gap',prev[1],prev[2],text,'3M',prev[0].isoformat(),last[0].isoformat())
        elif met==0 and matches and not gap:
            fired+=_record(con,(ident,arm,symbol,direction,target,unit,frequency),last[1],last[2],now,'saved_daily_close','crossing',prev[1],prev[2],text,'3M',prev[0].isoformat(),last[0].isoformat())
        else:
            con.execute('UPDATE price_alerts SET condition_met=?,evaluation_note=NULL WHERE id=?',(1 if matches else 0,ident))
    bump(con)
    return fired


def snapshot(con,now):
    def records(query):
        cur=con.execute(query);names=[x[0] for x in cur.description]
        return [dict(zip(names,row)) for row in cur.fetchall()]
    return {'revision':con.execute('SELECT revision FROM price_alert_meta WHERE id=1').fetchone()[0],'alerts':records('SELECT * FROM price_alerts ORDER BY created_at DESC,id'),
            'events':records('SELECT * FROM price_alert_events ORDER BY id DESC LIMIT 2000'),
            'serverTime':now,'maxAlerts':MAX_ALERTS,'historyLimit':MAX_HISTORY,'maxPriceAgeSeconds':MAX_AGE_MS//1000,
            'notice':'The local server checks armed alerts while it is running, including when the browser tab is closed. Nothing is checked while the server or the Mac is off. Level alerts trigger once on a qualifying quote. Crossing and percent alerts record a crossing only after an unmet price was seen and a later price meets the rule. A price after a gap is labelled separately. Unusual-session alerts use saved closes, need 20 valid earlier sessions, and skip split-sized jumps. Replay prices are not evaluated.'}
