"""Label-isolated fitting, decision rules and paired agent evaluation."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from assurance import ROOT, OUT, SEED, FORECAST, CATALOGUES

GATES = ["Scope", "Storage rule", "Hold RF", "Whole RF", "Calibrated whole RF",
         "Nominal hold", "Nominal task", "Robust hold", "Robust whole",
         "Robust task no validity", "Robust task", "Learned robust task", "Deny all"]


def predicted_allow(evaluation, horizon="whole", recovery=True, validity=True):
    if "error" in evaluation:
        return False
    return bool((not validity or evaluation["assessable"])
                and evaluation["realized"] == 1
                and not evaluation[horizon + "_harm"]
                and (not recovery or not evaluation["recovery_failure"]))


def decide(gate, view, threshold):
    """Consumes forecasts and learned scores, never actual outcomes."""
    if gate == "Scope":
        return True, 0
    if gate == "Deny all":
        return False, 0
    if gate == "Storage rule":
        return view["storage_rule"], 0
    if gate in ("Hold RF", "Whole RF", "Calibrated whole RF"):
        p = view["hold_score"] if gate == "Hold RF" else view["whole_score"]
        cut = threshold if gate == "Calibrated whole RF" else .5
        return bool(p < cut), 0
    if gate == "Learned robust task" and view["whole_score"] >= threshold:
        return False, 0
    forecasts = view["forecasts"]
    if gate.startswith("Nominal"):
        return predicted_allow(forecasts[1], horizon="hold" if gate == "Nominal hold" else "whole",
                               recovery=gate == "Nominal task"), 1
    horizon = "hold" if gate == "Robust hold" else "whole"
    recovery = gate not in ("Robust hold", "Robust whole")
    validity = gate != "Robust task no validity"
    return all(predicted_allow(x, horizon, recovery, validity) for x in forecasts), 3


def agent_order(assets, whole_scores, controller):
    if controller == "catalogue":
        return list(assets)
    return sorted(assets, key=lambda a: (whole_scores[a], assets.index(a)))


def propose_until_allowed(order, decisions, budget=4):
    """Only denial receipts and available assets affect this controller."""
    attempts = []
    selected = None
    workload = 0
    for asset in order[:budget]:
        allowed, simulations = decisions[asset]
        attempts.append(dict(asset=asset, allowed=bool(allowed), forecast_simulations=simulations))
        workload += simulations
        if allowed:
            selected = asset
            break
    return selected, attempts, workload


def frame_from_receipts(receipts):
    rows, errors = [], []
    for task in receipts:
        state = task["state"]
        if "error" in task:
            errors.append(dict(**state, error=task["error"]))
            continue
        for record in task["results"]:
            actual = record["evaluations"][f"actual:{state['hidden_factor']}:wntr"]
            cross = record["evaluations"][f"actual:{state['hidden_factor']}:epanet"]
            row = dict(**state, asset=record["asset"], reserved=record["reserved"],
                       storage_rule=record["storage_rule"], **record["features"],
                       actual=actual, actual_epanet=cross,
                       forecasts=[record["evaluations"][f"forecast:{f}:epanet"] for f in FORECAST])
            row.update(assessable=bool(actual["assessable"]), acceptable=bool(actual["acceptable"]),
                       whole_harm=actual.get("whole_harm", False),
                       hold_harm=actual.get("hold_harm", False),
                       recovery_failure=actual.get("recovery_failure", False),
                       realized=actual.get("realized", 0))
            rows.append(row)
    return pd.DataFrame(rows), errors


def positive_probability(model, x):
    if 1 not in model.classes_:
        return np.zeros(len(x))
    return model.predict_proba(x)[:, list(model.classes_).index(1)]


def fit_network(a):
    names = [c for c in a if c.startswith("x_")]
    train = a[(a.split == "train") & a.assessable]
    cal = a[(a.split == "calibration") & a.assessable]
    if not len(train) or not len(cal):
        raise ValueError("No assessable fitting/calibration data")
    labels = {"hold": train.hold_harm.astype(int), "whole": (~train.acceptable).astype(int)}
    models = {}
    for target in labels:
        m = RandomForestClassifier(n_estimators=300, min_samples_leaf=5,
                                   class_weight="balanced", random_state=SEED, n_jobs=1)
        m.fit(train[names], labels[target])
        models[target] = m
        a[target + "_score"] = positive_probability(m, a[names])
    scores = a.loc[cal.index, "whole_score"].to_numpy()
    failed = (~cal.acceptable).to_numpy()
    options = []
    for threshold in np.arange(0, .501, .01):
        allowed = scores < threshold
        risk = float(allowed[failed].mean()) if failed.any() else 0.0
        retention = float(allowed[~failed].mean()) if (~failed).any() else 0.0
        if risk <= .05:
            options.append((retention, float(threshold), risk))
    best = max(options)
    meta = dict(features=names, training_rows=len(train), calibration_rows=len(cal),
                training_indeterminate_excluded=int(((a.split == "train") & ~a.assessable).sum()),
                calibration_indeterminate_excluded=int(((a.split == "calibration") & ~a.assessable).sum()),
                calibration_failures=int(failed.sum()), threshold=best[1],
                calibration_failure_acceptance=best[2], calibration_acceptable_retention=best[0])
    return a, meta


def candidate_metrics(a, allows, gate):
    valid = a.assessable.to_numpy(bool)
    harmful = a.whole_harm.to_numpy(bool) & valid
    acceptable = a.acceptable.to_numpy(bool)
    allowed = np.asarray(allows, dtype=bool)
    return dict(gate=gate, n=len(a), indeterminate=int((~valid).sum()),
                harmful=int(harmful.sum()), harmful_accepted=int((allowed & harmful).sum()),
                acceptable=int(acceptable.sum()), acceptable_retained=int((allowed & acceptable).sum()),
                indeterminate_accepted=int((allowed & ~valid).sum()), allowed=int(allowed.sum()))


def block_interval(values):
    values = np.asarray(values, float)
    n = len(values)
    if not n:
        return [None, None]
    rng = np.random.default_rng(SEED)
    estimates = []
    for _ in range(2000):
        starts = rng.integers(0, n, size=int(np.ceil(n/3)))
        idx = np.concatenate([(s + np.arange(3)) % n for s in starts])[:n]
        estimates.append(float(values[idx].mean()))
    return np.quantile(estimates, [.025, .975]).tolist()


def analyze(smoke=False):
    receipts = json.loads((OUT / ("smoke_receipts.json" if smoke else "receipts.json")).read_text())
    data, errors = frame_from_receipts(receipts)
    if smoke:
        print(data[["network", "asset", "assessable", "acceptable", "whole_harm", "recovery_failure", "realized"]].to_string(index=False))
        return
    fitted, manifests, candidate_stats, records, traces = [], {}, [], [], []
    for network, a in data.groupby("network", sort=False):
        a, meta = fit_network(a.copy())
        manifests[network] = meta
        fitted.append(a)
        test = a[a.split == "test"].copy()
        views = {i: dict(hold_score=r.hold_score, whole_score=r.whole_score,
                         forecasts=r.forecasts, storage_rule=bool(r.storage_rule))
                 for i, r in test.iterrows()}
        for gate in GATES:
            decision = {i: decide(gate, v, meta["threshold"]) for i, v in views.items()}
            for stratum, mask in [("all", np.ones(len(test), bool)),
                                  ("reserved", test.reserved.to_numpy(bool)),
                                  ("inside grid", ~test.outside_grid.to_numpy(bool)),
                                  ("outside grid", test.outside_grid.to_numpy(bool))]:
                subset = test[mask]
                candidate_stats.append(dict(network=network, stratum=stratum,
                    **candidate_metrics(subset, [decision[i][0] for i in subset.index], gate)))
            for task_id, group in test.groupby("task_id", sort=True):
                assets = group.asset.tolist()
                choices = {r.asset: decision[i] for i, r in group.iterrows()}
                scores = dict(zip(group.asset, group.whole_score))
                for controller in ("catalogue", "learned ranking"):
                    selected, attempts, workload = propose_until_allowed(
                        agent_order(assets, scores, controller), choices)
                    outcome = None if selected is None else group[group.asset == selected].iloc[0]
                    record = dict(network=network, task_id=task_id, gate=gate,
                        controller=controller, order=int(group.order.iloc[0]),
                        outside_grid=bool(group.outside_grid.iloc[0]), selected=selected,
                        attempts=len(attempts), forecast_simulations=workload,
                        completed=bool(outcome is not None and outcome.realized == 1),
                        harmful=bool(outcome is not None and outcome.assessable and outcome.whole_harm),
                        indeterminate=bool(outcome is not None and not outcome.assessable),
                        recovery_failure=bool(outcome is not None and outcome.assessable and outcome.recovery_failure),
                        acceptable=bool(outcome is not None and outcome.acceptable),
                        abstained=selected is None)
                    records.append(record)
                    traces.append(dict(**record, receipts=attempts))
    fitted = pd.concat(fitted, ignore_index=True)
    serialized = fitted.drop(columns=["actual", "actual_epanet", "forecasts"]).copy()
    for col in ["hold_unmet_delta", "whole_unmet_delta", "terminal_unmet_delta", "whole_tank_hours_delta",
                "terminal_storage_deficit"]:
        serialized[col] = [r.get(col, np.nan) for r in fitted.actual]
    for col in ["hold_unmet_delta", "whole_unmet_delta", "whole_tank_hours_delta", "assessable", "whole_harm"]:
        serialized["epanet_" + col] = [r.get(col, np.nan) for r in fitted.actual_epanet]
    serialized.to_csv(OUT / "candidate_outcomes.csv", index=False)
    for gate in GATES:
        serialized["allow_" + gate] = [decide(gate, dict(hold_score=r.hold_score,
            whole_score=r.whole_score, forecasts=r.forecasts, storage_rule=r.storage_rule),
            manifests[r.network]["threshold"])[0] for r in fitted.itertuples()]
    serialized.to_csv(OUT / "candidate_decisions.csv", index=False)
    pd.DataFrame(candidate_stats).to_csv(OUT / "candidate_metrics.csv", index=False)
    agents = pd.DataFrame(records)
    agents.to_csv(OUT / "agent_episodes.csv", index=False)
    (OUT / "agent_traces.json").write_text(json.dumps(traces, separators=(",", ":")))
    summaries = []
    for (net, controller, gate), g in agents.groupby(["network", "controller", "gate"], sort=False):
        summaries.append(dict(network=net, controller=controller, gate=gate, n=len(g),
            **{c:int(g[c].sum()) for c in ["completed", "harmful", "indeterminate", "recovery_failure", "acceptable", "abstained", "attempts", "forecast_simulations"]},
            acceptable_ci=block_interval(g.sort_values("order").acceptable.astype(float))))
    (OUT / "agent_summary.json").write_text(json.dumps(summaries, indent=2))
    contrasts = []
    for (net, controller), g in agents.groupby(["network", "controller"]):
        wide = g.pivot(index="order", columns="gate", values="acceptable").astype(int)
        for comparator in ["Hold RF", "Whole RF", "Nominal task", "Robust hold", "Robust whole"]:
            delta = wide["Robust task"] - wide[comparator]
            contrasts.append(dict(network=net, controller=controller, comparator=comparator,
                delta_acceptable=float(delta.mean()), count_delta=int(delta.sum()),
                block_interval=block_interval(delta.to_numpy())))
    (OUT / "paired_contrasts.json").write_text(json.dumps(contrasts, indent=2))
    (OUT / "fit_manifest.json").write_text(json.dumps(manifests, indent=2))
    (OUT / "state_failures.json").write_text(json.dumps(errors, indent=2))
    numerical = {}
    for net, g in fitted.groupby("network"):
        actual = g.actual.tolist(); cross = g.actual_epanet.tolist()
        comparable = [(a, b) for a, b in zip(actual, cross) if "error" not in a and "error" not in b]
        numerical[net] = dict(candidates=len(g), wntr_assessable=int(g.assessable.sum()),
            simulation_errors=sum("error" in x for x in actual),
            cross_solver_pairs=len(comparable),
            cross_solver_harm_disagreements=sum(a["whole_harm"] != b["whole_harm"] for a,b in comparable),
            cross_solver_acceptable_disagreements=sum(a["acceptable"] != b["acceptable"] for a,b in comparable),
            max_unmet_delta_disagreement=max(abs(a["whole_unmet_delta"]-b["whole_unmet_delta"]) for a,b in comparable),
            max_tank_hour_delta_disagreement=max(abs(a["whole_tank_hours_delta"]-b["whole_tank_hours_delta"]) for a,b in comparable),
            max_wntr_pdd_residual=max(x["metrics"]["whole"]["max_pdd_residual_m3s"] for x in actual if "error" not in x),
            max_wntr_continuity_residual=max(x["metrics"]["whole"]["max_continuity_residual_m3s"] for x in actual if "error" not in x))
    (OUT / "numerical_summary.json").write_text(json.dumps(numerical, indent=2))
    print(json.dumps(dict(candidates=len(fitted), agent_episodes=len(agents),
                         states=len(receipts), state_failures=len(errors), numerical=numerical), indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    analyze(parser.parse_args().smoke)
