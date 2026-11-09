"""v2.7 saved briefing sources and coverage metadata. No network or AI here."""
import datetime as dt
import json
import math
import re
from urllib.parse import urlsplit

DAY=86400000

def init(con):
    con.execute('CREATE TABLE IF NOT EXISTS desk_news(scope TEXT PRIMARY KEY,fetched_at INTEGER NOT NULL,body TEXT NOT NULL)')
    con.execute('CREATE TABLE IF NOT EXISTS desk_import_metadata(symbol TEXT PRIMARY KEY,body TEXT NOT NULL)')
    # Upgrade earlier CSV imports once at startup; regular briefing reads never
    # decode entire multi-year price files just to display their metadata.
    for symbol,body in con.execute('SELECT symbol,payload FROM imported_daily_history').fetchall():
        remember_import(con,symbol,json.loads(body))
    con.execute('DELETE FROM desk_import_metadata WHERE symbol NOT IN (SELECT symbol FROM imported_daily_history)')

def text(value,limit):
    return re.sub(r'[\x00-\x1f\x7f]',' ',value).strip()[:limit] if isinstance(value,str) else ''

def news_rows(raw,now):
    """Retain small linked headline records, never article bodies or images."""
    if not isinstance(raw,list):return []
    found={}
    for row in raw[:200]:
        if not isinstance(row,dict):continue
        title=text(row.get('headline'),280);publisher=text(row.get('source'),100);url=text(row.get('url'),1600);stamp=row.get('datetime')
        if not title or not publisher or isinstance(stamp,bool) or not isinstance(stamp,(int,float)) or not math.isfinite(stamp):continue
        if not now-7*DAY<=stamp*1000<=now:continue
        try:
            parts=urlsplit(url)
            if parts.scheme not in ('https','http') or not parts.netloc or parts.username or parts.password:continue
        except ValueError:continue
        item={'headline':title,'source':publisher,'url':url,'datetime':int(stamp)}
        old=found.get(url)
        if old is None or stamp>old['datetime']:found[url]=item
    return sorted(found.values(),key=lambda x:x['datetime'],reverse=True)[:36]

def remember_news(con,scope,raw,fetched_at,now):
    if not isinstance(fetched_at,int) or not 946684800000<=fetched_at<=now+60000:return False
    old=con.execute('SELECT fetched_at FROM desk_news WHERE scope=?',(scope,)).fetchone()
    if old and old[0]>fetched_at:return False
    con.execute('INSERT OR REPLACE INTO desk_news VALUES(?,?,?)',(scope,fetched_at,json.dumps(news_rows(raw,now))))
    con.execute('DELETE FROM desk_news WHERE rowid NOT IN (SELECT rowid FROM desk_news ORDER BY fetched_at DESC LIMIT 64)')
    return True

def read_news(con,scopes,now):
    result={}
    for scope in scopes:
        row=con.execute('SELECT fetched_at,body FROM desk_news WHERE scope=?',(scope,)).fetchone()
        result[scope]={'fetchedAt':row[0] if row else None,'items':news_rows(json.loads(row[1]),now) if row else []}
    return result

def extent(con,table,time_column,symbol):
    row=con.execute(f'SELECT MIN({time_column}),MAX({time_column}),COUNT(*) FROM {table} WHERE symbol=?',(symbol,)).fetchone()
    return {'first':row[0],'last':row[1],'count':row[2]}

def remember_import(con,symbol,data):
    points=data.get('points',[])
    meta={'symbol':symbol,'source':text(data.get('source'),160),'splitAdjusted':data.get('split_adjusted') is True,
          'priceColumn':text(data.get('price_column'),50),'importedAt':data.get('imported_at'),
          'count':len(points),'first':points[0]['t'] if points else None,'last':points[-1]['t'] if points else None}
    con.execute('INSERT OR REPLACE INTO desk_import_metadata VALUES(?,?)',(symbol,json.dumps(meta)))

def imports(con):
    total=con.execute('SELECT COUNT(*) FROM desk_import_metadata').fetchone()[0]
    result=[json.loads(row[0]) for row in con.execute('SELECT body FROM desk_import_metadata ORDER BY rowid DESC LIMIT 200')]
    return {'total':total,'items':result}

def snapshot(con,symbols,now):
    history={}
    for symbol in symbols:
        history[symbol]={'daily':extent(con,'massive_daily_bars','ts_ms',symbol),
                         'intraday':extent(con,'observations','ts',symbol)}
    return {'history':history,'news':read_news(con,['general',*symbols],now),'imports':imports(con)}
