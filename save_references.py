"""Re-execute and preserve matched no-action metrics for independent arithmetic audit."""
from concurrent.futures import ProcessPoolExecutor
import gzip
import json
from assurance import OUT, FORECAST, select_states, trajectory, summarize_task


def evaluate(state):
    pairs = [("forecast",f,"epanet") for f in FORECAST]
    pairs += [("actual",state["hidden_factor"],s) for s in ("wntr","epanet")]
    metrics = {}
    for tag,factor,solver in pairs:
        key=f"{tag}:{factor}:{solver}"
        try:
            w,r,warnings,seconds=trajectory(state,factor,solver)
            metrics[key]=dict(metrics=summarize_task(w,r,state),warnings=warnings,seconds=seconds)
        except Exception as error:
            metrics[key]=dict(error=repr(error))
    return dict(task_id=state["task_id"],references=metrics)


if __name__=="__main__":
    records=[]
    with ProcessPoolExecutor(max_workers=6) as executor:
        for r in executor.map(evaluate,select_states()):
            records.append(r)
            if len(records)%12==0:print("saved references",len(records),"/144",flush=True)
    data=json.dumps(records,separators=(",",":")).encode()
    (OUT/"references.json.gz").write_bytes(gzip.compress(data,compresslevel=9,mtime=0))
