"""Fixed outcome-blind EPANET 60-second sensitivity, retaining the primary labels."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from assurance import OUT, CATALOGUES, select_states, trajectory, summarize_task, paired_effect


def choose_case(state):
    w, r, _, _ = trajectory(state, 1., "epanet")
    active = [name for name in CATALOGUES[state["network"]]
              if r.link["status"].loc[int(state["hour"]*3600), name] > 0]
    return dict(state=state, asset=active[state["order"] % len(active)])


def evaluate(case):
    state, asset = case["state"], case["asset"]
    result = dict(task_id=state["task_id"], network=state["network"], asset=asset)
    try:
        w0, r0, _, _ = trajectory(state, state["hidden_factor"], "epanet", step=60)
        w, r, warning_list, seconds = trajectory(state, state["hidden_factor"], "epanet", asset, step=60)
        result.update(paired_effect(summarize_task(w, r, state, asset), summarize_task(w0, r0, state)))
        result.update(seconds=seconds, warnings=warning_list)
    except Exception as error:
        result.update(error=repr(error))
    return result


if __name__ == "__main__":
    selected = [choose_case(s) for s in select_states()
                if s["split"] == "test" and s["order"] % 2 == 0]
    (OUT / "fine_step_selection.json").write_text(json.dumps(selected, indent=2))
    result = []
    with ProcessPoolExecutor(max_workers=2) as executor:
        for r in executor.map(evaluate, selected):
            result.append(r)
            print("fine step", len(result), "/", len(selected), r["task_id"], flush=True)
    (OUT / "fine_step_results.json").write_text(json.dumps(result, indent=2))
