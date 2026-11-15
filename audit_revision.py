"""Arithmetic, locked-design and compact-manuscript checks for this revision."""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import math
import re
import pandas as pd
from docx import Document
from followup_validation import states

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results'


def main(manuscript=None):
    checks=[]
    def check(name,passed,detail=''):checks.append(dict(check=name,passed=bool(passed),detail=detail))
    records=json.loads(gzip.decompress((OUT/'followup_receipts.json.gz').read_bytes()))
    planned=states();manifest=json.loads((OUT/'followup_generation_manifest.json').read_text())
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    check('All 48 planned new task records retained',{r['state']['task_id'] for r in records}=={s['task_id'] for s in planned} and len(records)==48)
    check('New profiles identical to committed task plan',{json.dumps(r['state'],sort_keys=True) for r in records}=={json.dumps(s,sort_keys=True) for s in planned})
    check('Follow-up script unchanged since generation',sha(ROOT/'followup_validation.py')==manifest['script_sha256'])
    check('Follow-up protocol unchanged since generation',sha(ROOT/'followup_protocol.md')==manifest['protocol_sha256'])
    check('Primary generator unchanged',sha(ROOT/'assurance.py')==manifest['original_generator_sha256'])
    check('Original fitting/calibration manifest unchanged',sha(OUT/'fit_manifest.json')==manifest['original_fit_sha256'])
    from analyze import load_receipts,frame_from_receipts,severity,predicted_allow,residual_order_statistic
    original_frame,_=frame_from_receipts(load_receipts());diagnostic=[]
    for net,g in original_frame[original_frame.split=='calibration'].groupby('network'):
        residuals=[];eligible_count=0;eligible_tasks=0
        for _,task in g.groupby('task_id'):
            if not task.assessable.all() or not all(all('error' not in e for e in r.forecasts) for r in task.itertuples()):continue
            selected=[r for r in task.itertuples() if all(predicted_allow(e) for e in r.forecasts) and max(map(severity,r.forecasts))<1]
            eligible_count+=len(selected);eligible_tasks+=bool(selected)
            residuals.append(max([0.]+[severity(r.actual)-max(map(severity,r.forecasts)) for r in selected]))
        diagnostic.append(dict(network=net,calibration_tasks=len(residuals),eligible_candidates=eligible_count,nonempty_tasks=eligible_tasks,restricted_margin=residual_order_statistic(residuals)))
    saved={r['network']:r for r in json.loads((OUT/'calibration_candidate_diagnostic.json').read_text())}
    check('Exploratory candidate restriction diagnostic reproduced',all(all(saved[r['network']][k]==v for k,v in r.items()) for r in diagnostic))
    check('Follow-up is later than all original test times',all(s['hour']>240 for s in planned))
    errors=[];label_errors=[];n=0;actual={};cross_harm=0;cross_acceptable=0
    for task in records:
        if 'error' in task:errors.append((task['state']['task_id'],task['error']));continue
        s=task['state'];refs=task['reference_metrics']
        for row in task['results']:
            n+=1
            for key,e in row['evaluations'].items():
                if 'error' in e or key not in refs:errors.append((s['task_id'],row['asset'],key));continue
                a=e['metrics'];b=refs[key]['metrics'];harm={}
                for horizon in ['hold','whole','terminal']:
                    du=(a[horizon]['unmet_m3']-b[horizon]['unmet_m3'])/b[horizon]['requested_m3']
                    de=a[horizon]['envelope_tank_h']-b[horizon]['envelope_tank_h']
                    if not math.isclose(du,e[horizon+'_unmet_delta'],abs_tol=1e-10) or not math.isclose(de,e[horizon+'_tank_hours_delta'],abs_tol=1e-9):errors.append((s['task_id'],row['asset'],key,horizon))
                    harm[horizon]=du>=.01 or de>=1
                    if harm[horizon]!=e[horizon+'_harm']:label_errors.append((s['task_id'],key,horizon))
                deficit=max(b['whole']['final_tank_fractions'][k]-v for k,v in a['whole']['final_tank_fractions'].items())
                recovery=(a['terminal']['unmet_m3']-b['terminal']['unmet_m3'])/b['terminal']['requested_m3']>.001 or deficit>.05
                assessable=a['whole']['assessable'] and b['whole']['assessable']
                acceptable=assessable and a['hold']['realized']==1 and not harm['whole'] and not recovery
                if (e['acceptable'],e['assessable'],e['recovery_failure'])!=(acceptable,assessable,recovery):label_errors.append((s['task_id'],key,'task'))
            aa=row['evaluations'][f"actual:{s['hidden_factor']}:wntr"]
            bb=row['evaluations'][f"actual:{s['hidden_factor']}:epanet"]
            actual[(s['task_id'],row['asset'])]=aa
            cross_harm+=aa.get('whole_harm')!=bb.get('whole_harm')
            cross_acceptable+=aa.get('acceptable')!=bb.get('acceptable')
    check('Follow-up arithmetic independently recomputed',not errors,str(errors[:3]))
    check('Follow-up numerical status and endpoint labels recomputed',not label_errors,str(label_errors[:3]))
    summary=json.loads((OUT/'followup_summary.json').read_text())
    check('All recorded candidates retained',n==summary['candidates'])
    episodes=pd.read_csv(OUT/'followup_agent_episodes.csv',dtype={'selected':str})
    check('1440 new paired policy episodes retained',len(episodes)==1440 and not episodes.duplicated(['task_id','gate','controller']).any())
    check('New controller attempt budgets respected',(episodes.attempts<=4).all())
    matched=True
    for r in episodes.itertuples():
        if pd.isna(r.selected):matched &= r.abstained and not r.acceptable;continue
        e=actual[(r.task_id,r.selected)]
        matched &= (bool(r.acceptable),bool(r.harmful),bool(r.indeterminate))==(e['acceptable'],e['assessable'] and e['whole_harm'],not e['assessable'])
    check('All new selected outcomes match raw evaluator receipts',matched)
    points=pd.read_csv(ROOT/'revision_artwork/Figure_1_source.csv')
    check('Figure 1 retains 144 calibration and test task records',len(points)==144 and (points.category=='Follow-up').sum()==48)
    from analyze import load_receipts
    def risk(e):
        return max(0.,e['hold_unmet_delta']/.01,e['hold_tank_hours_delta'],e['whole_unmet_delta']/.01,e['whole_tank_hours_delta'],e['terminal_unmet_delta']/.001,e['terminal_storage_deficit']/.05)
    independent={}
    for task in load_receipts()+records:
        s=task['state']
        if s['split']=='train':continue
        pairs=[(r['evaluations'][f"actual:{s['hidden_factor']}:wntr"],[r['evaluations'][f'forecast:{f}:epanet'] for f in [.85,1.,1.15]]) for r in task['results']]
        ok=all(a['assessable'] and all('error' not in e for e in forecasts) for a,forecasts in pairs)
        value=max([0.]+[risk(a)-max(map(risk,forecasts)) for a,forecasts in pairs]) if ok else None
        independent[s['task_id']]=(ok,value)
    check('Every Figure 1 residual independently matched',all(bool(r.assessable)==independent[r.task_id][0] and (pd.isna(r.residual) if not r.assessable else math.isclose(r.residual,independent[r.task_id][1],abs_tol=1e-10)) for r in points.itertuples()))
    stages=pd.read_csv(ROOT/'revision_artwork/Figure_2_source.csv')
    check('Figure 2 stages retain every scheduled task',len(stages)==384 and (stages.groupby(['network','cohort','gate']).size()==24).all())
    reference_order=json.loads((ROOT/'revision_reference_order.json').read_text())
    recheck=json.loads((OUT/'reference_recheck_20261115.json').read_text())
    check('24 external sources and one versioned dataset retained',len(reference_order)==25 and len(set(reference_order))==25 and reference_order[-1]=='studydata')
    check('22 selected DOI titles verified against primary metadata',sum(r['key'] in reference_order and r['status']=='verified' for r in recheck)==22)
    urls=json.loads((OUT/'official_url_recheck_20261115.json').read_text())
    check('Two official technical URLs resolve',len(urls)==2 and all(r.get('status')==200 for r in urls))
    if manuscript:
        d=Document(manuscript);body='\n'.join(p.text for p in d.paragraphs);text=body.split('\nReferences\n')[0]
        first=[]
        for token in re.findall(r'\[([\d,]+)\]',text):
            for v in map(int,token.split(',')):
                if v not in first:first.append(v)
        check('Compact citations complete in first-use order',first==list(range(1,26)))
        check('Exactly two main figures and two editable main tables',len(d.inline_shapes)==2 and len(d.tables)==2)
        check('Five editable display equations retained',len(d._element.xpath('.//m:oMath'))==5)
        abstract=body.split('Abstract\n')[1].split('\nKeywords:')[0]
        check('Abstract within 250 words',len(abstract.split())<=250,str(len(abstract.split())))
        check('Six keywords retained',len(body.split('Keywords: ')[1].split('\n')[0].split(';'))==6)
        check('Readable twelve-point double-spaced body',d.styles['Normal'].font.size.pt==12 and d.styles['Normal'].paragraph_format.line_spacing==2)
        check('Uncertainty and physical-safety limits remain visible',all(w in text for w in ['90%','indeterminate','share equations','prospectively']))
        check('Full article type not silently changed to Short Communication','Short Communication' not in text)
        old=pd.DataFrame(json.loads((OUT/'agent_summary.json').read_text()));new=pd.DataFrame(json.loads((OUT/'followup_agent_summary.json').read_text()))
        values=True
        for row in d.tables[1].rows[1:]:
            net,gate,*observed=[c.text for c in row.cells];expected=[]
            if gate=='Scenario task':gate='Robust task'
            for frame in [old,new]:
                g=frame[(frame.network==net)&(frame.gate==gate)].set_index('controller')
                expected.extend([f"{g.loc['catalogue','acceptable']}/{g.loc['learned ranking','acceptable']}",f"{g.loc['catalogue','harmful']}/{g.loc['learned ranking','harmful']}"])
            values &= expected==observed
        check('Every compact Table 2 value matched to executed outputs',values)
        from analyze import frame_from_receipts
        original,_=frame_from_receipts(load_receipts());newframe,_=frame_from_receipts(records)
        t1=True
        for row in d.tables[0].rows[1:]:
            net,cohort,*observed=[c.text for c in row.cells]
            data=(original[(original.network==net)&(original.split=='test')] if cohort=='Primary' else newframe[newframe.network==net])
            expected=[str(data.task_id.nunique()),str(len(data)),str(int(data.assessable.sum())),str(int(data.acceptable.sum())),str(int((data.assessable&data.whole_harm).sum()))]
            t1 &= observed==expected
        check('Every compact Table 1 count matched to raw receipts',t1)
    result=dict(passed=sum(r['passed'] for r in checks),total=len(checks),candidates=n,
        cross_solver_harm_disagreements=cross_harm,cross_solver_acceptable_disagreements=cross_acceptable,checks=checks)
    (OUT/'revision_evidence_audit.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))
    if result['passed']!=result['total']:
        print(json.dumps([r for r in checks if not r['passed']],indent=2));raise SystemExit(1)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manuscript',type=Path);args=p.parse_args();main(args.manuscript)
