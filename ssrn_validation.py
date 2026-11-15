"""Prospective third-cohort generator and fixed calibration manifest builder."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import argparse
import gzip
import hashlib
import json
import time
import numpy as np
import assurance as a
from analyze import load_receipts, frame_from_receipts
from followup_validation import evaluate
from admissibility_audit import calibrate, from_frame, json_safe

ROOT=a.ROOT;OUT=a.OUT;SEED=2026111503


def states():
    rng=np.random.default_rng(SEED);records=[]
    for net in a.CATALOGUES:
        for i,hour in enumerate(np.linspace(384,456,24).round().astype(int)):
            profile=rng.uniform(.65,1.35,3).tolist()
            records.append(dict(task_id=f'{net}_ssrn_{i:02d}',network=net,split='test',
                order=i,hour=int(hour),scale=[.925,1.075][i%2],
                hold_h=6 if net=='C-Town' else 3,hidden_factor=profile[0],
                hidden_profile=profile,outside_grid=min(profile)<.85 or max(profile)>1.15))
    return records


def freeze():
    frame,_=frame_from_receipts(load_receipts());manifest={}
    for net,g in frame[frame.split=='calibration'].groupby('network'):
        tasks=from_frame(g)
        manifest[net]={name:json_safe(calibrate(tasks,opportunity_only=conditional))
                       for name,conditional in [('marginal',False),('conditional',True)]}
    (OUT/'ssrn_calibration.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'ssrn_states.json').write_text(json.dumps(states(),indent=2)+'\n')


def generate(workers):
    selected=states();a.prepare_inputs();started=time.monotonic()
    names=['ssrn_validation.py','admissibility_audit.py','ssrn_validation_protocol.md',
           'followup_validation.py','assurance.py','results/fit_manifest.json',
           'results/ssrn_calibration.json','results/ssrn_states.json']
    manifest=dict(seed=SEED,scheduled_tasks=48,hashes={n:a.sha(ROOT/n) for n in names})
    (OUT/'ssrn_generation_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    a.prepare_checkpoints(selected,workers=workers);records=[]
    with ProcessPoolExecutor(max_workers=workers) as executor:
        for future in as_completed([executor.submit(evaluate,s) for s in selected]):
            records.append(future.result())
            (OUT/'ssrn_receipts.json.gz').write_bytes(gzip.compress(json.dumps(records,separators=(',',':')).encode(),mtime=0))
            print(f'New cohort {len(records)}/48 elapsed={time.monotonic()-started:.1f}s',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');p.add_argument('--generate',action='store_true');p.add_argument('--workers',type=int,default=6);args=p.parse_args()
    if args.freeze:freeze()
    if args.generate:generate(args.workers)
