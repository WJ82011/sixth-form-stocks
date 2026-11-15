#!/usr/bin/env python3
"""Repeat the isolated offline suite. No keys, user data or external providers."""
import argparse,datetime as dt,json,pathlib,re,subprocess,sys,time

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--rounds',type=int,default=3,choices=range(1,11))
 parser.add_argument('--output',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parents[1]/'Reliability-Test-Report.json')
 args=parser.parse_args();rounds=[];start=time.monotonic()
 for i in range(args.rounds):
  print('Reliability run '+str(i+1)+' of '+str(args.rounds)+' — disposable data, no provider calls',flush=True)
  before=time.monotonic()
  try:
   result=subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name('run_all.py'))],capture_output=True,text=True,timeout=180)
   match=re.search(r'Ran (\d+) tests in',result.stderr)
   record={'round':i+1,'passed':result.returncode==0,'tests':int(match.group(1)) if match else None,'seconds':round(time.monotonic()-before,3)}
   if result.returncode:record['failureSummary']=result.stderr[-16000:]
  except subprocess.TimeoutExpired:record={'round':i+1,'passed':False,'seconds':round(time.monotonic()-before,3),'failureSummary':'Suite exceeded the 180-second bound.'}
  rounds.append(record);print(('PASS' if record['passed'] else 'FAIL')+' · '+str(record.get('tests','?'))+' tests · '+str(record['seconds'])+' seconds',flush=True)
  if not record['passed']:break
 report={'release':'6.8.0','checkedAtUTC':dt.datetime.now(dt.timezone.utc).isoformat(),'python':sys.version.split()[0],'requestedRounds':args.rounds,'completedRounds':len(rounds),'passed':len(rounds)==args.rounds and all(x['passed'] for x in rounds),'totalSeconds':round(time.monotonic()-start,3),'runs':rounds,'scope':'Isolated automated regression and failure injection, not proof of live-provider uptime, universal financial accuracy or AI semantic truth.'}
 args.output.write_text(json.dumps(report,indent=2)+'\n');print('Report saved: '+args.output.name,flush=True)
 return 0 if report['passed'] else 1
if __name__=='__main__':sys.exit(main())
