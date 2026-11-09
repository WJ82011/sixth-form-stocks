"""Optional live local-model evaluation. Uses fictional sources only; requires Ollama.
Run manually: python3 tests/evaluate_local_ai.py
Not part of the offline regression suite. No keys or market providers are used.
"""
import sys,time,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import research_ai as a
sources=[{'id':'D1','title':'Fictional evaluation fixture','kind':'test fixture','body':'This is fictional test data, not a market quote. Example Company reported revenue of 120 million USD and operating profit of 18 million USD. Its reporting period ended in June 2026. The source does not report a share price, product names or future returns.'}]
cases=[('answer','What revenue and operating profit are reported in the source?',sources),('answer','What is the current share price? Do not guess if the source does not provide it.',sources),('report','Write a short balanced research report. Explain the figures and the missing evidence. Do not calculate new figures.',sources),('answer','Compare the reported revenue figures for Example Company and Other Company. Do not calculate a difference.',sources+[{'id':'D2','title':'Other fictional company','kind':'test fixture','body':'Other Company reported revenue of 80 million USD. These are fictional test figures, not market prices.'}])]
results=[]
for mode,q,ss in cases:
 start=time.monotonic();p=a.packet('TEST',ss,int(time.time()*1000),q)
 try:
  d=a.generate(a.PREFERRED,mode,q,p);r={'question':q,'mode':mode,'accepted':True,'seconds':round(time.monotonic()-start,1),'draft':d};print(json.dumps({k:v for k,v in r.items() if k!='draft'}),flush=True)
 except Exception as e:
  r={'question':q,'mode':mode,'accepted':False,'seconds':round(time.monotonic()-start,1),'error':str(e)};print(json.dumps(r),flush=True)
 results.append(r)
print(json.dumps(results,indent=2))
print('Accepted',sum(x['accepted'] for x in results),'of',len(results),'fictional-source tasks. This is not a comparison with commercial platforms.',flush=True)
