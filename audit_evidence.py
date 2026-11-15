"""Independent arithmetic and provenance checks of saved experiment receipts."""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import math
import re
import numpy as np
import pandas as pd
from assurance import ROOT, OUT, FORECAST, RESERVED, select_states
from analyze import load_receipts


def main(manuscript=None):
    checks=[]
    def check(name, passed, evidence=""):
        checks.append(dict(check=name, passed=bool(passed), evidence=evidence))
    digest=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    receipts=load_receipts();states=select_states()
    manifest=json.loads((OUT/"generation_manifest.json").read_text())
    check("Frozen generation implementation unchanged",digest(ROOT/"assurance.py")==manifest["code_sha256"])
    check("Original prospective protocol unchanged",digest(ROOT/"protocol.md")==manifest["protocol_sha256"])
    check("All 144 frozen tasks retained",len(receipts)==144 and {x['state']['task_id'] for x in receipts}=={s['task_id'] for s in states})
    check("No state-level failures",all('error' not in x for x in receipts))
    references={r['task_id']:r['references'] for r in json.loads(gzip.decompress((OUT/"references.json.gz").read_bytes()))}
    check("All matched reference metrics retained",len(references)==144)
    arithmetic_errors=[];class_errors=[];assessment_errors=[];candidates=0;evals=0
    eligible_test={};cross_harm=0;cross_acceptable=0
    for task in receipts:
        state=task['state'];task_id=state['task_id'];rows=task['results']
        if state['split']=='test':eligible_test[task_id]={r['asset'] for r in rows}
        check_set={f"forecast:{f}:epanet" for f in FORECAST}|{f"actual:{state['hidden_factor']}:{s}" for s in ['wntr','epanet']}
        for row in rows:
            candidates+=1
            if set(row['evaluations'])!=check_set:arithmetic_errors.append((task_id,row['asset'],'evaluation keys'))
            for key,ev in row['evaluations'].items():
                evals+=1
                if 'error' in ev or 'error' in references[task_id][key]:
                    arithmetic_errors.append((task_id,row['asset'],key,'simulation error'));continue
                action=ev['metrics'];base=references[task_id][key]['metrics'];computed={}
                for h in ['hold','whole','terminal']:
                    delta_u=(action[h]['unmet_m3']-base[h]['unmet_m3'])/base[h]['requested_m3']
                    delta_e=action[h]['envelope_tank_h']-base[h]['envelope_tank_h']
                    if not math.isclose(delta_u,ev[h+'_unmet_delta'],abs_tol=1e-10,rel_tol=1e-9):arithmetic_errors.append((task_id,row['asset'],key,h,'unmet'))
                    if not math.isclose(delta_e,ev[h+'_tank_hours_delta'],abs_tol=1e-9):arithmetic_errors.append((task_id,row['asset'],key,h,'envelope'))
                    computed[h]=bool(delta_u>=.01 or delta_e>=1)
                    if computed[h]!=ev[h+'_harm']:class_errors.append((task_id,row['asset'],key,h))
                deficit=max(base['whole']['final_tank_fractions'][n]-v for n,v in action['whole']['final_tank_fractions'].items())
                recovery=(action['terminal']['unmet_m3']-base['terminal']['unmet_m3'])/base['terminal']['requested_m3']>.001 or deficit>.05
                good=ev['assessable'] and action['hold']['realized']==1 and not computed['whole'] and not recovery
                if bool(recovery)!=ev['recovery_failure'] or bool(good)!=ev['acceptable']:class_errors.append((task_id,row['asset'],key,'task'))
                if bool(action['whole']['assessable'] and base['whole']['assessable'])!=ev['assessable']:assessment_errors.append((task_id,row['asset'],key))
            first=row['evaluations'][f"actual:{state['hidden_factor']}:wntr"]
            second=row['evaluations'][f"actual:{state['hidden_factor']}:epanet"]
            cross_harm+=first.get('whole_harm')!=second.get('whole_harm')
            cross_acceptable+=first.get('acceptable')!=second.get('acceptable')
    check("530 candidate actions and 2650 solver evaluations retained",candidates==530 and evals==2650)
    check("Continuous effects independently recomputed from matched references",not arithmetic_errors,str(arithmetic_errors[:3]))
    check("All horizon labels recovery and acceptable outcomes recomputed",not class_errors,str(class_errors[:3]))
    check("Paired numerical assessability labels consistent",not assessment_errors)
    check("530 paired binary harm outcomes agree",cross_harm==0)
    check("Six acceptable outcome disagreements retained",cross_acceptable==6)
    decisions=pd.read_csv(OUT/'candidate_decisions.csv',dtype={'asset':str})
    fit=json.loads((OUT/'fit_manifest.json').read_text())
    for net,count in [('C-Town',33),('Net3',27)]:
        local=decisions[decisions.network==net]
        check(net+" network-specific features finite",len(fit[net]['features'])==count and np.isfinite(local[fit[net]['features']].to_numpy()).all())
        dev=local[local.split!='test']
        check(net+" reserved assets excluded from development",not dev.asset.isin(RESERVED[net]).any())
    check("Post-inspection feature correction disclosed",(ROOT/'analysis_amendments.md').exists() and (OUT/'initial_feature_join_analysis.json').exists())
    policy_metrics=pd.read_csv(OUT/'candidate_metrics.csv')
    all_metrics_match=True
    for r in policy_metrics.itertuples():
        a=decisions[(decisions.network==r.network)&(decisions.split=='test')]
        if r.stratum=='reserved':a=a[a.reserved]
        if r.stratum=='inside grid':a=a[~a.outside_grid]
        if r.stratum=='outside grid':a=a[a.outside_grid]
        allow=a['allow_'+r.gate].to_numpy(bool);harm=a.whole_harm.to_numpy(bool)&a.assessable.to_numpy(bool)
        acceptable=a.acceptable.to_numpy(bool);unknown=~a.assessable.to_numpy(bool)
        expected=[len(a),int(harm.sum()),int((allow&harm).sum()),int(acceptable.sum()),int((allow&acceptable).sum()),int(unknown.sum()),int((allow&unknown).sum())]
        all_metrics_match &= expected==[r.n,r.harmful,r.harmful_accepted,r.acceptable,r.acceptable_retained,r.indeterminate,r.indeterminate_accepted]
    check("Every policy stratum count and denominator recomputed",all_metrics_match)
    episodes=pd.read_csv(OUT/'agent_episodes.csv',dtype={'selected':str})
    check("1440 paired policy episodes retained",len(episodes)==1440 and not episodes.duplicated(['task_id','controller','gate']).any())
    check("All controllers obey four attempt budget",(episodes.attempts<=4).all())
    check("Selected assets belong to authorized candidate sets",all(pd.isna(r.selected) or r.selected in eligible_test[r.task_id] for r in episodes.itertuples()))
    traces=json.loads((OUT/'agent_traces.json').read_text())
    trace_match=True
    for t in traces:
        allowed=[r for r in t['receipts'] if r['allowed']]
        trace_match &= len(allowed)<=1 and len(t['receipts'])==t['attempts'] and (allowed[-1]['asset'] if allowed else None)==t['selected']
    check("Agent choices follow recorded denials and first acceptance",trace_match)
    fresh=json.loads((OUT/'fresh_agent_rollouts.json').read_text())
    check("288 fresh attempted rollouts retained",len(fresh)==288)
    check("170 fresh actions and 118 abstentions retained",sum(r['executed'] for r in fresh)==170 and sum(not r['executed'] for r in fresh)==118)
    check("Fresh execution matches every cached categorical outcome",all(r['matched_cached_outcome'] for r in fresh) and not any('error' in r for r in fresh))
    recovery_match=True
    for r in fresh:
        old=episodes[(episodes.task_id==r['task_id'])&(episodes.controller==r['controller'])&(episodes.gate==r['gate'])].iloc[0]
        recovery_match &= bool(r.get('assessable',False) and r.get('recovery_failure',False))==bool(old.recovery_failure)
    check("Fresh recovery outcomes independently matched",recovery_match)
    fine=json.loads((OUT/'fine_step_summary.json').read_text())
    check("24 fixed finer step comparisons complete",sum(x['n'] for x in fine.values())==24 and all(x['errors']==0 for x in fine.values()))
    check("No finer step harm or acceptable label changes in selected sample",all(x['harm_changes']==0 and x['acceptable_changes']==0 for x in fine.values()))
    containment=pd.DataFrame(json.loads((OUT/'residual_containment.json').read_text()))
    for net,expected in [('C-Town',(20,19)),('Net3',(21,13))]:
        g=containment[containment.network==net]
        check(net+" failed or limited containment transparently counted",(int(g.assessable.sum()),int(g.contained.eq(True).sum()))==expected)
    check("C-Town residual margin implies universal abstention",fit['C-Town']['residual_margin']>1 and not decisions[(decisions.network=='C-Town')&(decisions.split=='test')]['allow_Residual task'].any())
    fig1=pd.read_csv(ROOT/'artwork/Figure_1_source.csv')
    independent_residuals={}
    def risk_vector(e):
        return max(0.,e['hold_unmet_delta']/.01,e['hold_tank_hours_delta'],
                   e['whole_unmet_delta']/.01,e['whole_tank_hours_delta'],
                   e['terminal_unmet_delta']/.001,e['terminal_storage_deficit']/.05)
    for task in receipts:
        state=task['state']
        if state['split']=='train':continue
        actual=[r['evaluations'][f"actual:{state['hidden_factor']}:wntr"] for r in task['results']]
        eligible=all(e['assessable'] for e in actual)
        residual=max(0.,max(risk_vector(e)-max(risk_vector(r['evaluations'][f'forecast:{f}:epanet']) for f in FORECAST)
                             for e,r in zip(actual,task['results']))) if eligible else None
        independent_residuals[state['task_id']]=(eligible,residual)
    check("All 96 Figure 1 task records match independently recomputed residuals",len(fig1)==96 and all(
        bool(r.assessable)==independent_residuals[r.task_id][0] and
        (pd.isna(r.residual) if not r.assessable else math.isclose(r.residual,independent_residuals[r.task_id][1],abs_tol=1e-10))
        for r in fig1.itertuples()))
    for net in ['C-Town','Net3']:
        values=sorted(v for task,(eligible,v) in independent_residuals.items() if eligible and task.startswith(net+'_calibration_'))
        rank=math.ceil(.9*(len(values)+1));margin=values[rank-1] if rank<=len(values) else None
        check(net+" residual margin independently recomputed",math.isclose(margin,fit[net]['residual_margin'],abs_tol=1e-10))
    fig2=pd.read_csv(ROOT/'artwork/Figure_2_source.csv')
    points_match=len(fig2)==20
    for r in fig2.itertuples():
        g=episodes[(episodes.network==r.network)&(episodes.controller==r.controller)&(episodes.gate==r.gate)]
        points_match &= len(g)==r.n==24 and int(g.acceptable.sum())==r.acceptable
    check("All 20 Figure 2 points match executed policy episodes",points_match)
    source=json.loads((ROOT/'reference_catalog.json').read_text())
    order=json.loads((ROOT/'citation_order.json').read_text())
    check("29 references retained with no duplicate DOI",len(source)==len(order)==29 and len({r['DOI'].lower() for r in source.values() if r.get('DOI')})==27)
    if manuscript:
        from docx import Document
        d=Document(manuscript);text='\n'.join(p.text for p in d.paragraphs);body=text.split('\nReferences\n')[0]
        first=[]
        for token in re.findall(r'\[([\d,]+)\]',body):
            for n in map(int,token.split(',')):
                if n not in first:first.append(n)
        check("Citations in first-use order without missing entries",first==list(range(1,30)))
        check("Exactly two figures and two editable main tables",len(d.inline_shapes)==2 and len(d.tables)==2)
        check("Five editable display equations",len(d._element.xpath('.//m:oMath'))==5)
        abstract=text.split('Abstract\n')[1].split('\nKeywords:')[0]
        check("Abstract within 250 words",len(abstract.split())<=250,str(len(abstract.split())))
        check("Six keywords",len(text.split('Keywords: ')[1].split('\n')[0].split(';'))==6)
        check("Main paragraphs double spaced",d.styles['Normal'].paragraph_format.line_spacing==2)
        check("Scientific failure and secondary status disclosures retained",all(x in body for x in ['13/21','secondary','post','withholding','no human']))
        check("No all Q1 or submission ready claim invented",'all-Q1' not in body and 'submission-ready' not in body)
        check("Both figures and tables cited in prose",all(x in body for x in ['Table 1','Table 2','Figure 1','Figure 2']))
        t=d.tables[1];table_match=True
        for row in t.rows[1:]:
            net,gate,harm,acceptable,unknown=[c.text for c in row.cells]
            r=policy_metrics[(policy_metrics.network==net)&(policy_metrics.gate==gate)&(policy_metrics.stratum=='all')].iloc[0]
            table_match &= [harm,acceptable,unknown]==[f'{r.harmful_accepted}/{r.harmful}',f'{r.acceptable_retained}/{r.acceptable}',f'{r.indeterminate_accepted}/{r.indeterminate}']
        check("Every Table 2 value matched to audited candidate counts",table_match)
    result=dict(passed=sum(c['passed'] for c in checks),total=len(checks),checks=checks)
    (OUT/'evidence_audit.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(dict(passed=result['passed'],total=result['total'],failures=[c for c in checks if not c['passed']]),indent=2))
    if result['passed']!=result['total']:raise SystemExit(1)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manuscript',type=Path)
    main(p.parse_args().manuscript)
