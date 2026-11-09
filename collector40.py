"""Loopback-owned capture, independent of browser visibility and lifecycle."""
import base64
import collections
import datetime as dt
import hashlib
import json
import math
import os
import socket
import struct
import threading
import time
from urllib.parse import quote

import crypto38
import learning40
import market37

HOST='ws.finnhub.io'
MAX_FRAME=2_000_000
DEFAULTS=('AAPL','NVDA','MSFT','GOOGL','AMZN','META','TSLA','AMD','PLTR','JPM','KO','DIS','NFLX','BA','TSM','TTWO')


class Feed:
    """Small bounded RFC 6455 client for Finnhub's JSON feed."""
    def __init__(self, token, tls):
        nonce=base64.b64encode(os.urandom(16)).decode()
        raw=socket.create_connection((HOST,443),timeout=8)
        try:
            self.sock=tls.wrap_socket(raw,server_hostname=HOST)
            self.sock.sendall((f'GET /?token={quote(token,safe="")} HTTP/1.1\r\nHost: {HOST}\r\n'
                f'Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {nonce}\r\n'
                'Sec-WebSocket-Version: 13\r\n\r\n').encode())
            self.buffer=bytearray()
            deadline=time.monotonic()+8
            while b'\r\n\r\n' not in self.buffer:
                remaining=deadline-time.monotonic()
                if remaining<=0:raise TimeoutError('Stream handshake timed out')
                self.sock.settimeout(remaining)
                self.read()
                if len(self.buffer)>16384:raise OSError('Handshake too large')
            header,body=self.buffer.split(b'\r\n\r\n',1)
            lines=bytes(header).split(b'\r\n')
            fields={k.strip().lower():v.strip() for line in lines[1:] for k,sep,v in [line.partition(b':')] if sep}
            accept=base64.b64encode(hashlib.sha1((nonce+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest())
            if lines[0].split()[1:2]!=[b'101'] or fields.get(b'sec-websocket-accept')!=accept:
                raise OSError('Stream handshake rejected')
            self.buffer=bytearray(body)
            self.fragments=None
            self.sock.settimeout(1)
        except Exception:
            getattr(self,'sock',raw).close()
            raise

    def read(self):
        chunk=self.sock.recv(65536)
        if not chunk:raise OSError('Stream closed')
        self.buffer.extend(chunk)

    def send(self, opcode, body):
        mask=os.urandom(4)
        n=len(body)
        size=bytes([128+n]) if n<126 else b'\xfe'+struct.pack('!H',n)
        self.sock.sendall(bytes([128+opcode])+size+mask+bytes(b^mask[i%4] for i,b in enumerate(body)))

    def next_frame(self):
        if len(self.buffer)<2:return None
        flags,n=self.buffer[:2]
        if flags&112 or n&128:raise OSError('Invalid stream frame')
        offset=2
        if n>=126:
            offset=4 if n==126 else 10
            if len(self.buffer)<offset:return None
            n=int.from_bytes(self.buffer[2:offset],'big')
        if n>MAX_FRAME:raise OSError('Oversized stream frame')
        if len(self.buffer)<offset+n:return None
        body=bytes(self.buffer[offset:offset+n])
        del self.buffer[:offset+n]
        return flags,body

    def messages(self):
        try:self.read()
        except TimeoutError:pass
        while (frame:=self.next_frame()) is not None:
            flags,body=frame
            opcode=flags&15
            final=bool(flags&128)
            if opcode>=8 and (not final or len(body)>125):raise OSError('Invalid control frame')
            if opcode==8:raise OSError('Provider closed stream')
            if opcode==9:self.send(10,body)
            if opcode==1:
                if self.fragments is not None:raise OSError('Incomplete stream message')
                if final:yield json.loads(body)
                else:self.fragments=bytearray(body)
            elif opcode==0:
                if self.fragments is None:raise OSError('Unexpected continuation')
                self.fragments.extend(body)
                if len(self.fragments)>MAX_FRAME:raise OSError('Oversized stream message')
                if final:
                    data=self.fragments;self.fragments=None
                    yield json.loads(data)


class Collector:
    def __init__(self,g):
        self.g=g
        self.stop=threading.Event()
        self.lock=threading.Lock()
        self.priority=None
        self.priority_until=0
        self.seq=0
        self.epoch=os.urandom(8).hex()
        self.events=collections.deque(maxlen=2000)
        self.symbols=[]
        self.status={'stream':'Starting','quotes':'Waiting','crypto':'Waiting','history':'Waiting','news':'Waiting','model':'Waiting'}
        self.last_trade=None
        self.indices={}
        self.watch=list(DEFAULTS)
        self.watch_until=0

    def set_status(self, key, message):
        with self.lock:self.status[key]=message

    def watchlist(self):
        if time.monotonic()>=self.watch_until:
            workspace=self.g['read_workspace']()['snapshot']
            self.watch=workspace.get('watch',[]) if workspace is not None else list(DEFAULTS)
            self.watch_until=time.monotonic()+3
        return self.watch

    def pulse(self, priority, cursor, epoch):
        with self.lock:
            if priority:
                self.priority=priority
                self.priority_until=time.monotonic()+8
            current=cursor if epoch==self.epoch and 0<=cursor<=self.seq else self.seq
            rows=[row for row in self.events if row['seq']>current]
            gap=bool(rows and rows[0]['seq']>current+1) or len(rows)>600
            return {'epoch':self.epoch,'cursor':self.seq,'events':rows[-600:],'gap':gap,
                    'symbols':self.symbols[:],'status':dict(self.status),'lastTrade':self.last_trade}

    def start(self):
        for job in (self.stream_loop,self.poll_loop):
            threading.Thread(target=job,daemon=True,name=job.__name__).start()

    def desired(self):
        with self.lock:
            primary=[self.priority] if self.priority and time.monotonic()<self.priority_until else []
        return list(dict.fromkeys(primary+self.watchlist()))[:30]

    def capture(self, data, subscribed):
        if not isinstance(data,dict):return
        if data.get('type')=='error':raise OSError('Provider rejected the subscription')
        if data.get('type')!='trade' or not isinstance(data.get('data'),list):return
        now=int(time.time()*1000)
        rows=[]
        for row in data['data'][:5000]:
            if not isinstance(row,dict) or not isinstance(row.get('s'),str) or row['s'] not in subscribed:continue
            p,t,v=(row.get(k) for k in ('p','t','v'))
            if type(p) not in (int,float) or type(t) is not int or type(v) not in (int,float):continue
            if not (0<p<=1e9 and now-300000<=t<=now+60000 and 0<=v<=1e12):continue
            rows.append({'s':row['s'],'p':p,'t':t,'v':v,'receivedAt':now})
        if not rows:return
        self.g['store_points_batch'](rows)
        with self.lock:
            for row in rows:
                if row['v']>0:
                    self.seq+=1
                    self.events.append({**row,'seq':self.seq})
                    self.last_trade=now

    def stream_loop(self):
        backoff=2
        while not self.stop.is_set():
            token=self.g['get_key']()
            if not token or not self.desired():
                self.set_status('stream','Waiting for Finnhub and a watchlist')
                self.stop.wait(4);continue
            feed=None
            try:
                tls,_=self.g['verified_tls_context']()
                feed=Feed(token,tls)
                self.set_status('stream','Connected')
                previous=set()
                last_byte=time.monotonic()
                while not self.stop.is_set() and token==self.g['get_key']():
                    desired=set(self.desired())
                    if not desired:break
                    for action,items in [('unsubscribe',previous-desired),('subscribe',desired-previous)]:
                        for sym in sorted(items):
                            feed.send(1,json.dumps({'type':action,'symbol':sym}).encode())
                    previous=desired
                    with self.lock:self.symbols=sorted(desired)
                    for message in feed.messages():
                        last_byte=time.monotonic()
                        self.capture(message,desired)
                    if time.monotonic()-last_byte>75:raise OSError('Silent stream')
                    if time.monotonic()-last_byte<2:backoff=2
            except Exception:
                # Avoid logging provider responses or request URLs containing a key.
                self.set_status('stream','Disconnected. Retrying automatically.')
                backoff=min(60,backoff*2)
            finally:
                if feed:feed.sock.close()
                with self.lock:self.symbols=[]
            self.stop.wait(backoff)

    def choose(self, name, items, count=1):
        if not items:return []
        pos=self.indices.get(name,0)%len(items)
        self.indices[name]=pos+count
        return (items+items)[pos:pos+min(count,len(items))]

    def poll_loop(self):
        due={}
        intervals={'quotes':25,'crypto':45,'cryptoHistory':180,'news':180,'marketNews':420,'heatmap':75,'history':180,'model':55}
        while not self.stop.is_set():
            for task,interval in intervals.items():
                if self.stop.is_set():return
                now=time.monotonic()
                if now<due.get(task,0):continue
                due[task]=now+interval
                try:self.refresh(task)
                except Exception:self.set_status(task,'Update unavailable. Saved data kept.')
            self.stop.wait(2)

    def refresh(self,task):
        g=self.g
        watch=self.watchlist()
        equities=[sym for sym in watch if g['ai_catalog_entry'](sym)]
        if task=='quotes' and watch and g['get_key']():
            symbols=self.choose(task,watch,3)
            result=g['handle_api']('/api/quotes',{'symbols':[','.join(symbols)]})
            count=sum(row['status']=='ok' for row in result['items'])
            self.set_status(task,f'{count} of {len(symbols)} snapshots usable')
        elif task in ('news','marketNews') and g['get_key']():
            symbols=self.choose(task,watch) if task=='news' else []
            query={'symbol':symbols} if symbols else {}
            g['handle_api']('/api/news',query)
            self.set_status(task,'Saved feed checked')
        elif task in ('crypto','cryptoHistory'):
            kind='quote' if task=='crypto' else '1D'
            results=[crypto38.packet(g,sym,kind)['status'] for sym in crypto38.PRODUCTS]
            self.set_status(task,', '.join(results))
        elif task=='heatmap' and g['get_massive_key']():
            self.set_status(task,market37.step(g,{'symbols':watch})['status'])
        elif task=='history' and g['get_massive_key']() and equities:
            sym=self.choose(task,equities)[0]
            end=int(time.time())
            result=g['massive_daily_candles'](sym,end-731*86400,end)
            self.set_status(task,sym+' · '+result['status'])
        elif task=='model' and equities:
            sym=self.choose(task,equities)[0]
            result=learning40.report(g,sym)
            self.set_status(task,sym+' · '+str(result['closes'])+' saved closes checked')
