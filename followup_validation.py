"""Locked later-task validation under unseen, time-varying hidden demand."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import time
import numpy as np
import pandas as pd
import assurance as a
from analyze import (GATES, load_receipts, frame_from_receipts, fit_network,
                     decide, severity, agent_order, propose_until_allowed,
                     candidate_metrics)

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results'
SEED=2026111502


def states():
    rng=np.random.default_rng(SEED);records=[]
    for network in a.CATALOGUES:
        for i,hour in enumerate(np.linspace(288,360,24).round().astype(int)):
            profile=rng.uniform(.70,1.30,3).tolist()
            records.append(dict(task_id=f'{network}_followup_{i:02d}',
                network=network,split='test',order=i,hour=int(hour),
                scale=[.95,1.05][i%2],hold_h=6 if network=='C-Town' else 3,
                hidden_factor=profile[0],hidden_profile=profile,
                outside_grid=bool(min(profile)<.85 or max(profile)>1.15)))
    return records


def profile_future(w,start,end,profile,hold_h):
    step=int(w.options.time.pattern_timestep);cache={}
    switches=(start,start+hold_h*1800,start+hold_h*3600)
    for _,junction in w.junctions():
        for series in junction.demand_timeseries_list:
            if series.base_value<=0:continue
            key=series.pattern_name
            if key not in cache:
                original=series.pattern;values=[]
                for t in range(0,end+step,step):
                    idx=sum(t>=s for s in switches)-1
                    factor=1. if idx<0 else profile[idx]
                    values.append((float(original.at(t)) if original else 1.)*factor)
                name='future_'+str(len(cache));w.add_pattern(name,values);cache[key]=name
            series.pattern_name=cache[key]


def evaluate(state):
    original_impose=a.impose_future;original_summary=a.summarize_task
    original_trajectory=a.trajectory;context={};references={}
    def impose(w,start,end,factor):
        if factor==state['hidden_factor']:
            return profile_future(w,start,end,state['hidden_profile'],state['hold_h'])
        return original_impose(w,start,end,factor)
    def trajectory(s,factor,solver,asset=None,step=300):
        context.update(key=f"{'actual' if factor==s['hidden_factor'] else 'forecast'}:{factor}:{solver}",asset=asset)
        return original_trajectory(s,factor,solver,asset,step)
    def summarize(w,r,s,asset=None):
        result=original_summary(w,r,s,asset)
        if asset is None:references[context['key']]=dict(metrics=result)
        return result
    a.impose_future=impose;a.trajectory=trajectory;a.summarize_task=summarize
    try:
        result=a.one_state(state);result['reference_metrics']=references;return result
    except Exception as error:return dict(state=state,error=repr(error))
    finally:
        a.impose_future=original_impose;a.trajectory=original_trajectory
        a.summarize_task=original_summary


def generate(workers):
    started=time.monotonic();selected=states();a.prepare_inputs()
    manifest=dict(seed=SEED,tasks=len(selected),
        started_utc=pd.Timestamp.now(tz='UTC').isoformat(),
        script_sha256=a.sha(__file__),protocol_sha256=a.sha(ROOT/'followup_protocol.md'),
        original_generator_sha256=a.sha(ROOT/'assurance.py'),
        original_fit_sha256=a.sha(OUT/'fit_manifest.json'))
    (OUT/'followup_generation_manifest.json').write_text(json.dumps(manifest,indent=2))
    a.prepare_checkpoints(selected,workers=workers)
    records=[]
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures=[executor.submit(evaluate,s) for s in selected]
        for future in as_completed(futures):
            records.append(future.result())
            payload=json.dumps(records,separators=(',',':')).encode()
            (OUT/'followup_receipts.json.gz').write_bytes(gzip.compress(payload,mtime=0))
            print(f'Follow-up complete {len(records)}/{len(selected)} elapsed={time.monotonic()-started:.1f}s',flush=True)
    print('FOLLOWUP_GENERATION_COMPLETE',flush=True)


def analyze():
    follow=json.loads(gzip.decompress((OUT/'followup_receipts.json.gz').read_bytes()))
    original,_=frame_from_receipts(load_receipts());new,errors=frame_from_receipts(follow)
    combined=pd.concat([original,new],ignore_index=True)
    locked=json.loads((OUT/'fit_manifest.json').read_text());records=[];candidates=[];containment=[];fits={}
    ids={s['task_id'] for s in states()};counts=[]
    for network,group in combined.groupby('network',sort=False):
        fitted,meta=fit_network(group.copy())
        for key in ['features','training_rows','calibration_rows','threshold','residual_margin','residual_calibration_tasks']:
            assert meta[key]==locked[network][key],(network,key)
        fits[network]=meta
        test=fitted[fitted.task_id.isin(ids)].copy()
        decisions={}
        for gate in GATES:
            decisions[gate]={i:decide(gate,dict(hold_score=r.hold_score,
                whole_score=r.whole_score,forecasts=r.forecasts,
                storage_rule=r.storage_rule,residual_margin=meta['residual_margin']),
                meta['threshold']) for i,r in test.iterrows()}
            candidates.append(dict(network=network,**candidate_metrics(test,[decisions[gate][i][0] for i in test.index],gate)))
        for task_id,task in test.groupby('task_id',sort=True):
            eligible=bool(task.assessable.all()) and all(all('error' not in x for x in r.forecasts) for r in task.itertuples())
            residual=max([0.]+[severity(r.actual)-max(map(severity,r.forecasts)) for r in task.itertuples()]) if eligible else None
            containment.append(dict(task_id=task_id,network=network,assessable=eligible,residual=residual,
                contained=bool(residual<=meta['residual_margin']) if eligible else None))
            for gate in GATES:
                choices={r.asset:decisions[gate][i] for i,r in task.iterrows()}
                scores=dict(zip(task.asset,task.whole_score))
                for controller in ['catalogue','learned ranking']:
                    selected,attempts,queries=propose_until_allowed(agent_order(task.asset.tolist(),scores,controller),choices)
                    outcome=None if selected is None else task[task.asset==selected].iloc[0]
                    records.append(dict(network=network,task_id=task_id,gate=gate,controller=controller,
                        selected=selected,attempts=len(attempts),forecast_simulations=queries,
                        acceptable=bool(outcome is not None and outcome.acceptable),
                        harmful=bool(outcome is not None and outcome.assessable and outcome.whole_harm),
                        indeterminate=bool(outcome is not None and not outcome.assessable),
                        recovery_failure=bool(outcome is not None and outcome.assessable and outcome.recovery_failure),
                        completed=bool(outcome is not None and outcome.realized==1),abstained=selected is None))
        counts.append(dict(network=network,tasks=int(test.task_id.nunique()),candidates=len(test),
            assessable=int(test.assessable.sum()),acceptable=int(test.acceptable.sum()),
            harmful=int((test.assessable&test.whole_harm).sum()),
            feasible_tasks=int(test.groupby('task_id').acceptable.any().sum())))
    episodes=pd.DataFrame(records);episodes.to_csv(OUT/'followup_agent_episodes.csv',index=False)
    pd.DataFrame(candidates).to_csv(OUT/'followup_candidate_metrics.csv',index=False)
    summaries=[]
    for (network,controller,gate),g in episodes.groupby(['network','controller','gate'],sort=False):
        summaries.append(dict(network=network,controller=controller,gate=gate,n=len(g),
            **{k:int(g[k].sum()) for k in ['acceptable','harmful','indeterminate','recovery_failure','completed','abstained']}))
    (OUT/'followup_agent_summary.json').write_text(json.dumps(summaries,indent=2))
    (OUT/'followup_containment.json').write_text(json.dumps(containment,indent=2))
    summary=dict(scheduled_tasks=48,completed_task_records=len(follow),state_errors=errors,
        candidates=len(new),policy_episodes=len(episodes),networks=counts,
        containment={network:dict(assessable=sum(r['assessable'] for r in containment if r['network']==network),
            contained=sum(r['contained'] is True for r in containment if r['network']==network)) for network in a.CATALOGUES})
    (OUT/'followup_summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--generate',action='store_true');p.add_argument('--analyze',action='store_true');p.add_argument('--workers',type=int,default=6);p.add_argument('--write-states',action='store_true');args=p.parse_args()
    if args.write_states:(OUT/'followup_states.json').write_text(json.dumps(states(),indent=2))
    if args.generate:generate(args.workers)
    if args.analyze:analyze()
