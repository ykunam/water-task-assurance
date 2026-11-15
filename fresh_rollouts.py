"""Execute already-fixed agent choices against fresh hydraulic continuations."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import pandas as pd
from assurance import OUT, select_states, trajectory, summarize_task, paired_effect

GATES = ("Hold RF", "Nominal task", "Residual task")


def execute_task(arguments):
    state, choices = arguments
    selected_any = any(pd.notna(c["selected"]) for c in choices)
    baseline = None
    if selected_any:
        w0, r0, _, _ = trajectory(state, state["hidden_factor"], "wntr")
        baseline = summarize_task(w0, r0, state)
    records = []
    for choice in choices:
        record = dict(task_id=state["task_id"], network=state["network"],
                      controller=choice["controller"], gate=choice["gate"],
                      selected=None if pd.isna(choice["selected"]) else choice["selected"])
        if record["selected"] is None:
            record.update(executed=False, acceptable=False, completed=False,
                          matched_cached_outcome=bool(choice["abstained"]))
        else:
            try:
                w, r, warning_list, elapsed = trajectory(
                    state, state["hidden_factor"], "wntr", record["selected"])
                action = summarize_task(w, r, state, record["selected"])
                effects = paired_effect(action, baseline)
                matched = bool(effects["acceptable"] == choice["acceptable"]
                               and (effects["realized"] == 1) == choice["completed"]
                               and (effects["assessable"] and effects["whole_harm"]) == choice["harmful"]
                               and (not effects["assessable"]) == choice["indeterminate"])
                record.update(executed=True, completed=effects["realized"] == 1,
                              **effects, seconds=elapsed, warnings=warning_list,
                              matched_cached_outcome=matched)
            except Exception as error:
                record.update(executed=True, error=repr(error),
                              matched_cached_outcome=False)
        records.append(record)
    return records


if __name__ == "__main__":
    episodes = pd.read_csv(OUT / "agent_episodes.csv", dtype={"selected":str})
    chosen = episodes[episodes.gate.isin(GATES)]
    states = {s["task_id"]:s for s in select_states() if s["split"] == "test"}
    arguments = [(states[key], g.to_dict("records")) for key,g in chosen.groupby("task_id")]
    rows = []
    with ProcessPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(execute_task, x) for x in arguments]
        for future in as_completed(futures):
            rows.extend(future.result())
            (OUT / "fresh_agent_rollouts.json").write_text(json.dumps(rows, indent=2))
            print("fresh agent rollouts", len(rows), "/", len(chosen), flush=True)
    summary = dict(attempted_rollouts=len(rows), hydraulic_action_executions=sum(x["executed"] for x in rows),
                   abstentions=sum(not x["executed"] for x in rows),
                   matching_cached_outcomes=sum(x["matched_cached_outcome"] for x in rows),
                   errors=sum("error" in x for x in rows))
    (OUT / "fresh_agent_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
