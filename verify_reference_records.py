"""Refresh bibliographic identity from Crossref primary metadata, without adding claims."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import csv
import html
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parent
EXCLUDE={'saltzer','airmf','leveson','agentdojo','abdar'}

def normalized(s):
    s=html.unescape(s);s=unicodedata.normalize('NFKD',s)
    return re.sub(r'[^a-z0-9]','',s.lower())

def fetch(item):
    key,record=item;doi=record.get('DOI')
    if not doi:return dict(key=key,status='official URL',url=record.get('URL'),included=key not in EXCLUDE)
    url='https://api.crossref.org/works/'+urllib.parse.quote(doi,safe='')
    error=None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'WaterTaskAssuranceBibliographicAudit/1.0'}),timeout=20) as response:
                data=json.load(response)['message']
            match=normalized(record['title'][0])==normalized(data['title'][0])
            return dict(key=key,doi=doi,status='verified' if match else 'title review required',included=key not in EXCLUDE,
                title_match=match,url=url,metadata={k:data[k] for k in ['DOI','title','author','container-title','published','published-print','published-online','issued','volume','issue','page','article-number','type','publisher','relation','update-to','assertion','URL'] if k in data})
        except Exception as e:error=repr(e);time.sleep(.3*(attempt+1))
    return dict(key=key,doi=doi,status='unverified',error=error,included=key not in EXCLUDE)

if __name__=='__main__':
    source=json.loads((ROOT/'reference_catalog.json').read_text())
    rows=[]
    with ThreadPoolExecutor(max_workers=6) as pool:
        for future in as_completed([pool.submit(fetch,item) for item in source.items()]):
            rows.append(future.result())
    rows.sort(key=lambda r:list(source).index(r['key']))
    (ROOT/'results/reference_recheck_20261115.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False))
    print(json.dumps([dict(key=r['key'],status=r['status'],included=r['included'],updates=r.get('metadata',{}).get('update-to',[])) for r in rows],indent=2))
