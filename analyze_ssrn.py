"""Analyze fixed gates and independently audit the prospective SSRN cohort."""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import math
import pandas as pd
from analyze import (load_receipts,frame_from_receipts,fit_network,decide,
                     agent_order,propose_until_allowed,severity)
from admissibility_audit import (calibrate,from_frame,allow,task_score,json_safe,
                                forecast_summary)
from ssrn_validation import states

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results'
GATES=['Hold RF','Nominal task','Scenario task','Original residual',
       'Eligible marginal','Eligible conditional']


def read(name):return json.loads(gzip.decompress((OUT/name).read_bytes()))


def run():
    fresh=read('ssrn_receipts.json.gz');old=load_receipts();follow=read('followup_receipts.json.gz')
    checks=[]
    def check(name,ok,detail=''):checks.append(dict(check=name,passed=bool(ok),detail=detail))
    manifest=json.loads((OUT/'ssrn_generation_manifest.json').read_text())
    check('All 48 locked prospective tasks retained',len(fresh)==48 and {json.dumps(r['state'],sort_keys=True) for r in fresh}=={json.dumps(s,sort_keys=True) for s in states()})
    check('Protocol and implementation hashes unchanged after freeze',all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in manifest['hashes'].items()))
    check('New times and observed scales outside previous cohorts',all(s['hour']>360 and s['scale'] in [.925,1.075] for s in states()))
    check('Every new task retains matched references',all('error' not in r and len(r.get('reference_metrics',{}))==5 for r in fresh))
    arithmetic=[];labels=[];pairs=0;cross_harm=0;cross_acceptable=0
    for task in fresh:
        if 'error' in task:arithmetic.append(task['state']['task_id']);continue
        refs=task['reference_metrics'];s=task['state']
        for row in task['results']:
            pairs+=1
            for key,e in row['evaluations'].items():
                if 'error' in e:continue
                a=e['metrics'];b=refs[key]['metrics'];harm={}
                for horizon in ['hold','whole','terminal']:
                    du=(a[horizon]['unmet_m3']-b[horizon]['unmet_m3'])/b[horizon]['requested_m3'];de=a[horizon]['envelope_tank_h']-b[horizon]['envelope_tank_h']
                    if not math.isclose(du,e[horizon+'_unmet_delta'],abs_tol=1e-10) or not math.isclose(de,e[horizon+'_tank_hours_delta'],abs_tol=1e-9):arithmetic.append((s['task_id'],row['asset'],key))
                    harm[horizon]=du>=.01 or de>=1
                    if harm[horizon]!=e[horizon+'_harm']:labels.append((s['task_id'],key,'harm'))
                deficit=max(b['whole']['final_tank_fractions'][k]-v for k,v in a['whole']['final_tank_fractions'].items())
                recovery=(a['terminal']['unmet_m3']-b['terminal']['unmet_m3'])/b['terminal']['requested_m3']>.001 or deficit>.05
                assessable=a['whole']['assessable'] and b['whole']['assessable']
                acceptable=assessable and a['hold']['realized']==1 and not harm['whole'] and not recovery
                if (e['acceptable'],e['assessable'],e['recovery_failure'])!=(acceptable,assessable,recovery):labels.append((s['task_id'],key,'task'))
            aa=row['evaluations'][f"actual:{s['hidden_factor']}:wntr"];bb=row['evaluations'][f"actual:{s['hidden_factor']}:epanet"]
            cross_harm+=aa.get('whole_harm')!=bb.get('whole_harm');cross_acceptable+=aa.get('acceptable')!=bb.get('acceptable')
    check('All continuous new effects recomputed from matched references',not arithmetic,str(arithmetic[:3]))
    check('All new endpoint and numerical labels independently recomputed',not labels,str(labels[:3]))
    primary,_=frame_from_receipts(old);f1,_=frame_from_receipts(follow);f2,errors=frame_from_receipts(fresh)
    check('No state-level prospective simulation errors',not errors)
    combined=pd.concat([primary.assign(cohort='Primary'),f1.assign(cohort='Follow-up'),f2.assign(cohort='Prospective')],ignore_index=True)
    frozen=json.loads((OUT/'ssrn_calibration.json').read_text());locked=json.loads((OUT/'fit_manifest.json').read_text())
    episodes=[];candidates=[];task_scores=[];support=[];calibration=[];witnesses=[];fit_ok=True;cal_ok=True;set_containment=True
    for net,g in combined.groupby('network',sort=False):
        fitted,meta=fit_network(g.copy())
        fit_ok &= all(meta[k]==locked[net][k] for k in ['features','threshold','training_rows','calibration_rows','residual_margin'])
        tasks=from_frame(g[g.split=='calibration']);marginal=calibrate(tasks);conditional=calibrate(tasks,opportunity_only=True)
        cal_ok &= json_safe(marginal)==frozen[net]['marginal'] and json_safe(conditional)==frozen[net]['conditional']
        calibration.append(dict(network=net,calibration_tasks=marginal['tasks'],eligible_tasks=marginal['opportunity_tasks'],eligible_candidates=marginal['eligible_candidates'],original_margin=meta['residual_margin'],original_score_count=meta['residual_calibration_tasks'],marginal_margin=marginal['margin'],conditional_margin=conditional['margin']))
        original_scores=[]
        for tid,t in fitted[fitted.split=='calibration'].groupby('task_id'):
            if not t.assessable.all() or not all(all('error' not in e for e in r.forecasts) for r in t.itertuples()):continue
            values=[]
            for r in t.itertuples():
                eligible,predicted=forecast_summary(r.forecasts)
                values.append(dict(task_id=tid,asset=r.asset,eligible=eligible,actual_severity=severity(r.actual),predicted_severity=predicted,residual=max(0.,severity(r.actual)-predicted),forecast_status=[dict(assessable=e['assessable'],realized=e['realized']) for e in r.forecasts]))
            original_scores.append(max(values,key=lambda r:r['residual']))
        rank=meta['residual_order_rank'];witnesses.append(dict(network=net,rank=rank,calibration_tasks=len(original_scores),witness=sorted(original_scores,key=lambda r:r['residual'])[rank-1]))
        for (cohort,tid),task in fitted[fitted.split=='test'].groupby(['cohort','task_id'],sort=True):
            assets=task.asset.tolist();scores=dict(zip(task.asset,task.whole_score));choices={gate:{} for gate in GATES}
            for i,r in task.iterrows():
                v=dict(hold_score=r.hold_score,whole_score=r.whole_score,forecasts=r.forecasts,storage_rule=r.storage_rule,residual_margin=meta['residual_margin'])
                for gate in GATES:
                    if gate.startswith('Eligible'):
                        margin=marginal['margin'] if gate=='Eligible marginal' else conditional['margin'];allowed=allow(r.forecasts,margin);cost=3
                    else:allowed,cost=decide({'Scenario task':'Robust task','Original residual':'Residual task'}.get(gate,gate),v,meta['threshold'])
                    choices[gate][r.asset]=(allowed,cost)
                    candidates.append(dict(network=net,cohort=cohort,task_id=tid,asset=r.asset,gate=gate,allowed=allowed,acceptable=r.acceptable,harmful=r.assessable and r.whole_harm,indeterminate=not r.assessable))
            ts=task_score(from_frame(task)[0]['candidates'])
            task_scores.append(dict(network=net,cohort=cohort,task_id=tid,eligible=ts['eligible'],score=ts['score'],contained=ts['score']<=marginal['margin']))
            for gate in GATES:
                for controller in ['catalogue','learned ranking']:
                    selected,attempts,cost=propose_until_allowed(agent_order(assets,scores,controller),choices[gate]);r=None if selected is None else task[task.asset==selected].iloc[0]
                    rec=dict(network=net,cohort=cohort,task_id=tid,gate=gate,controller=controller,selected=selected,attempts=len(attempts),forecast_simulations=cost,acceptable=bool(r is not None and r.acceptable),harmful=bool(r is not None and r.assessable and r.whole_harm),indeterminate=bool(r is not None and not r.assessable),completed=bool(r is not None and r.realized==1),recovery_failure=bool(r is not None and r.assessable and r.recovery_failure),abstained=selected is None)
                    episodes.append(rec)
                    if gate=='Eligible marginal' and ts['score']<=marginal['margin'] and selected is not None:set_containment &= rec['acceptable']
        for cohort,data in fitted[fitted.split=='test'].groupby('cohort'):
            support.append(dict(network=net,cohort=cohort,tasks=int(data.task_id.nunique()),candidates=len(data),assessable=int(data.assessable.sum()),acceptable=int(data.acceptable.sum()),harmful=int((data.assessable&data.whole_harm).sum())))
    check('Original fits and original margins remain unchanged',fit_ok)
    check('New margins and all calibration scores match pre-outcome freeze',cal_ok)
    check('Every contained task accepts only acceptable actions under either ranking',set_containment)
    ep=pd.DataFrame(episodes);prospective=ep[ep.cohort=='Prospective']
    check('Exactly 576 matched prospective policy episodes',len(prospective)==576 and not prospective.duplicated(['task_id','gate','controller']).any())
    check('Every controller respects four attempts',(ep.attempts<=4).all())
    check('Conditional gate records vacuity as abstention',ep[ep.gate=='Eligible conditional'].abstained.all())
    check('Both marginal calibration sets retain all 24 scheduled tasks',all(x['calibration_tasks']==24 for x in calibration))
    check('Support diagnostic is four and seven eligible tasks',{x['network']:x['eligible_tasks'] for x in calibration}=={'C-Town':4,'Net3':7})
    check('All-task margins zero and opportunity margins infinite',all(x['marginal_margin']==0 and math.isinf(x['conditional_margin']) for x in calibration))
    check('Both original margin-defining witnesses are forecast-ineligible',all(not r['witness']['eligible'] and math.isclose(r['witness']['residual'],locked[r['network']]['residual_margin'],abs_tol=1e-10) for r in witnesses))
    summaries=[]
    for keys,g in ep.groupby(['network','cohort','gate','controller'],sort=False):summaries.append(dict(zip(['network','cohort','gate','controller'],keys),n=len(g),**{k:int(g[k].sum()) for k in ['acceptable','harmful','indeterminate','completed','recovery_failure','abstained']}))
    ep.to_csv(OUT/'ssrn_agent_episodes.csv',index=False);pd.DataFrame(candidates).to_csv(OUT/'ssrn_candidate_decisions.csv',index=False)
    pd.DataFrame(task_scores).to_csv(OUT/'ssrn_task_scores.csv',index=False)
    result=dict(prospective_tasks=48,candidates=pairs,action_solver_evaluations=pairs*5,prospective_policy_episodes=len(prospective),cross_solver_harm_disagreements=cross_harm,cross_solver_acceptable_disagreements=cross_acceptable,calibration=calibration,support=support,agent_summary=summaries)
    (OUT/'ssrn_summary.json').write_text(json.dumps(json_safe(result),indent=2)+'\n')
    (OUT/'ssrn_calibration_witnesses.json').write_text(json.dumps(json_safe(witnesses),indent=2)+'\n')
    audit=dict(passed=sum(x['passed'] for x in checks),total=len(checks),checks=checks)
    (OUT/'ssrn_evidence_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['agent_summary','support']},default=str,indent=2));print(json.dumps(audit,indent=2))
    assert audit['passed']==audit['total']


if __name__=='__main__':run()
