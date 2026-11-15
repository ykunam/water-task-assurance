"""Resume an interrupted primary run while verifying frozen generation code."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import pandas as pd
from assurance import OUT, ROOT, sha, select_states, one_state

manifest = json.loads((OUT / "generation_manifest.json").read_text())
assert sha(ROOT / "assurance.py") == manifest["code_sha256"], "Frozen generator changed"
assert sha(ROOT / "protocol.md") == manifest["protocol_sha256"], "Frozen protocol changed"
states = json.loads((OUT / "states.json").read_text())
assert states == select_states(), "Frozen state list changed"
path = OUT / "receipts.json"
receipts = json.loads(path.read_text())
done = {r["state"]["task_id"] for r in receipts}
assert len(done) == len(receipts), "Duplicate task receipt"
pending = [s for s in states if s["task_id"] not in done]
resume = dict(started_utc=pd.Timestamp.now(tz="UTC").isoformat(),
              frozen_code_sha256=manifest["code_sha256"],
              retained_receipts_sha256=sha(path), retained=len(receipts),
              pending_task_ids=[s["task_id"] for s in pending])
(OUT / "resume_manifest.json").write_text(json.dumps(resume, indent=2))
with ProcessPoolExecutor(max_workers=6) as executor:
    futures = {executor.submit(one_state, s):s for s in pending}
    for future in as_completed(futures):
        state = futures[future]
        try:
            record = future.result()
        except Exception as error:
            record = dict(state=state, error=repr(error))
        receipts.append(record)
        receipts.sort(key=lambda x:(x["state"]["network"], x["state"]["split"], x["state"]["order"]))
        path.write_text(json.dumps(receipts, separators=(",", ":")))
        print("resumed", len(receipts), "/", len(states), state["task_id"],
              "candidates", len(record.get("results", [])), "error", record.get("error"), flush=True)
resume["completed_utc"] = pd.Timestamp.now(tz="UTC").isoformat()
resume["final_receipts_sha256"] = sha(path)
(OUT / "resume_manifest.json").write_text(json.dumps(resume, indent=2))
