"""Match journal manuscript table cells, citations and figure source records."""
from pathlib import Path
import argparse
import json
import math
import re
import pandas as pd
from docx import Document
from analyze import load_receipts,frame_from_receipts,severity
from admissibility_audit import task_score,from_frame

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results'


def main(path):
    d=Document(path);body='\n'.join(p.text for p in d.paragraphs);checks=[]
    def check(name,ok,detail=''):checks.append(dict(check=name,passed=bool(ok),detail=detail))
    summary=json.loads((OUT/'ssrn_summary.json').read_text());agents=pd.DataFrame(summary['agent_summary'])
    check('Exactly two figures and two editable research tables',len(d.inline_shapes)==2 and len(d.tables)==2)
    check('Five editable equations with consecutive numbering',len(d._element.xpath('.//m:oMath'))==5 and [int(x) for x in re.findall(r'\((\d)\)\s*$',body,re.M)]==[1,2,3,4,5])
    first=[]
    for token in re.findall(r'\[([\d,]+)\]',body.split('\nReferences\n')[0]):
        for n in map(int,token.split(',')):
            if n not in first:first.append(n)
    check('26 references cited completely in first-use order',first==list(range(1,27)))
    order=json.loads((ROOT/'methodology_reference_order.json').read_text())
    check('New nearest prior work cited as an unreviewed preprint','disc' in order and 'arXiv:2609.24496v1' in body and 'preprint, not peer reviewed' in body)
    check('Substantive AI disclosure precedes references',body.index('Declaration of generative AI and AI-assisted technologies in the manuscript preparation process')<body.index('\nReferences\n') and 'ChatGPT Work assisted with research design' in body)
    check('Journal affiliation/contact present without preprint labeling',all(s in body for s in ['Midwest University','yeshwanth.kunam@gmail.com']) and 'Preprint |' not in body)
    check('Statistical assumptions and retrospective chronology explicit',all(s in body for s in ['exchangeability','retrospective','infinite','No actual outcome enters']))
    abstract=body.split('Abstract\n')[1].split('\nKeywords:')[0]
    check('Scientific abstract within 250 words',len(abstract.split())<=250,str(len(abstract.split())))
    matched=True
    for row,raw in zip(d.tables[0].rows[1:],summary['calibration']):
        expected=[raw['network'],'24',str(raw['eligible_tasks']),str(raw['eligible_candidates']),f"{raw['original_margin']:.4f}",'0','∞']
        matched &= [c.text for c in row.cells]==expected
    check('Every Table 1 calibration-support cell matches frozen results',matched)
    matched=True
    for row in d.tables[1].rows[1:]:
        net,gate,*observed=[c.text for c in row.cells];g=agents[(agents.network==net)&(agents.cohort=='Prospective')&(agents.gate==gate)].set_index('controller')
        expected=[f"{int(g.loc['catalogue',k])}/{int(g.loc['learned ranking',k])}" for k in ['acceptable','harmful','indeterminate','abstained']]
        matched &= expected==observed
    check('Every Table 2 outcome cell matches prospective outputs',matched)
    points=pd.read_csv(ROOT/'methodology_artwork/Figure_1_source.csv');primary,_=frame_from_receipts(load_receipts());expected={}
    for (net,tid),g in primary[primary.split=='calibration'].groupby(['network','task_id']):
        valid=g.assessable.all() and all(all('error' not in e for e in r.forecasts) for r in g.itertuples())
        original=max([0.]+[severity(r.actual)-max(map(severity,r.forecasts)) for r in g.itertuples()]) if valid else None
        expected[tid]=(bool(valid),original,task_score(from_frame(g)[0]['candidates']))
    matched=len(points)==48
    for r in points.itertuples():
        valid,original,eligible=expected[r.task_id]
        matched &= bool(r.original_assessable)==valid and (math.isclose(r.original_score,original,abs_tol=1e-10) if valid else pd.isna(r.original_score)) and math.isclose(r.eligible_score,eligible['score'],abs_tol=1e-10) and r.eligible_candidates==eligible['eligible']
    check('Every Figure 1 source value independently reconstructed',matched)
    stages=pd.read_csv(ROOT/'methodology_artwork/Figure_2_source.csv');ep=pd.read_csv(OUT/'ssrn_agent_episodes.csv');ep=ep[ep.cohort=='Prospective'].set_index(['network','gate','controller','task_id'])
    matched=len(stages)==384 and (stages.groupby(['network','gate','controller']).size()==24).all()
    for r in stages.itertuples():
        e=ep.loc[(r.network,r.gate,r.controller,r.task_id)]
        expected='Abstained' if e.abstained else 'Indeterminate' if e.indeterminate else 'Harm' if e.harmful else 'Unrealized' if not e.completed else 'Recovery failure' if e.recovery_failure else 'Acceptable'
        matched &= r.stage==expected
    check('Every Figure 2 stage matched and every bar retains 24 tasks',matched)
    recheck=json.loads((OUT/'reference_recheck_20261115.json').read_text());check('22 selected DOI identities retain verified records',sum(r['key'] in order and r['status']=='verified' for r in recheck)==22)
    additional=json.loads((OUT/'ssrn_additional_reference_verification.json').read_text());check('Additional arXiv source verified against primary record',additional['version']=='arXiv:2609.24496v1' and additional['authors']==['Yajie Bao','Yinjie Min','Haojie Ren','Changliang Zou'])
    import gzip
    fresh=json.loads(gzip.decompress((OUT/'ssrn_receipts.json.gz').read_bytes()));actual,_=frame_from_receipts(fresh)
    ceilings={net:int(g.groupby('task_id').acceptable.any().sum()) for net,g in actual.groupby('network')}
    saved=json.loads((OUT/'methodology_opportunity_summary.json').read_text());saved={r['network']:r['feasible_tasks'] for r in saved if r['cohort']=='Prospective'}
    check('Finite-pool opportunity ceilings independently matched',saved==ceilings=={'C-Town':12,'Net3':12} and '12/24 C-Town and 12/24 Net3 prospective task pools' in body)
    check('Both figures and both tables cited in main prose',all(label in body.split('\nReferences\n')[0] for label in ['Figure 1 traces','Figure 2 separates','Table 1 contrasts','Table 2 retains']))
    check('Preprint DOI and affiliation superscripts retained','10.48550/arXiv.2609.24496' in body and len(d._element.xpath('.//w:vertAlign[@w:val="superscript"]'))>=2)
    counts={}
    for net,g in actual.groupby('network'):
        values=[task_score(from_frame(t)[0]['candidates']) for _,t in g.groupby('task_id')]
        counts[net]=(sum(r['score']<=0 for r in values),len(values),sum(r['score']<=0 for r in values if r['eligible']),sum(r['eligible']>0 for r in values))
    records=json.loads((OUT/'methodology_containment_summary.json').read_text());record_counts={r['network']:(r['all_contained'],r['all_tasks'],r['opportunity_contained'],r['opportunity_tasks']) for r in records if r['cohort']=='Prospective'}
    check('Marginal and opportunity containment denominators reconstructed',counts==record_counts=={'C-Town':(21,24,2,5),'Net3':(18,24,5,11)} and all(s in body for s in ['21/24 C-Town and 18/24 Net3','2/5 and 5/11']))
    result=dict(passed=sum(x['passed'] for x in checks),total=len(checks),checks=checks)
    (OUT/'methodology_manuscript_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));assert result['passed']==result['total']


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manuscript',type=Path,required=True);args=p.parse_args();main(args.manuscript)
