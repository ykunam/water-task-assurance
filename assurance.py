"""Prospective, simulator-only isolation/recovery experiment.

Forecasts never receive the hidden future-demand factor. Models are fitted only
on the training partition. Every failed simulation remains a recorded outcome.
"""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import argparse
import hashlib
import json
import os
import pickle
import shutil
import tempfile
import time
import urllib.request
import warnings

import numpy as np
import pandas as pd
import networkx as nx
import wntr
from sklearn.ensemble import RandomForestClassifier

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"
DATA = ROOT / "data"
SEED = 20261115
FORECAST = (0.85, 1.0, 1.15)
CATALOGUES = {
    "C-Town": ["PU" + str(i) for i in range(1, 12)],
    "Net3": ["10", "335", "238", "240", "241", "243", "60", "20"],
}
RESERVED = {"C-Town": ["PU10", "PU11"], "Net3": ["60", "20"]}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare_inputs(input_dir=None):
    DATA.mkdir(exist_ok=True)
    info = json.loads((ROOT / "inputs.json").read_text())
    for name in info:
        destination = DATA / name
        if not destination.exists():
            if input_dir is not None and (Path(input_dir) / name).exists():
                shutil.copy(Path(input_dir) / name, destination)
            elif name == "Net3.inp":
                shutil.copy(Path(wntr.__file__).parent / "library/networks/Net3.inp", destination)
            else:
                with urllib.request.urlopen(info[name]["source"], timeout=60) as response:
                    destination.write_bytes(response.read())
        if sha(destination) != info[name]["sha256"]:
            raise ValueError("Input hash mismatch: " + name)


def model(network, scale=1.0, step=300):
    name = "CTOWN.INP" if network == "C-Town" else "Net3.inp"
    w = wntr.network.WaterNetworkModel(str(DATA / name))
    o = w.options
    o.hydraulic.demand_model = "PDD"
    o.hydraulic.minimum_pressure = 0
    o.hydraulic.required_pressure = 15
    o.hydraulic.pressure_exponent = 0.5
    o.hydraulic.accuracy = 1e-6
    o.hydraulic.trials = 500
    o.hydraulic.unbalanced = "STOP"
    o.hydraulic.demand_multiplier = scale
    o.time.hydraulic_timestep = step
    o.time.report_timestep = step
    o.time.rule_timestep = step
    return w


def impose_future(w, start, end, factor):
    """Replace only positive-demand time series, preserving the native prefix."""
    timestep = int(w.options.time.pattern_timestep)
    cache = {}
    for name, junction in w.junctions():
        for series in junction.demand_timeseries_list:
            if series.base_value <= 0:
                continue
            key = series.pattern_name
            if key not in cache:
                original = series.pattern
                multipliers = [
                    (float(original.at(t)) if original is not None else 1.0)
                    * (factor if t >= start else 1.0)
                    for t in range(0, end + timestep, timestep)
                ]
                new_name = "future_" + str(len(cache))
                w.add_pattern(new_name, multipliers)
                cache[key] = new_name
            series.pattern_name = cache[key]


def add_isolation(w, asset, start, release):
    """Highest-priority hold rule, then one reopen request and native automation."""
    from wntr.network.controls import (
        SimTimeCondition, AndCondition, ControlAction, Rule, Control, ControlPriority,
    )
    link = w.get_link(asset)
    during = AndCondition(SimTimeCondition(w, ">=", start),
                          SimTimeCondition(w, "<", release))
    w.add_control("task_isolation", Rule(
        during, ControlAction(link, "status", 0),
        priority=ControlPriority.very_high,
    ))
    w.add_control("task_release", Control(
        SimTimeCondition(w, "=", release), ControlAction(link, "status", 1),
        priority=ControlPriority.very_high,
    ))


def run(w, solver):
    began = time.perf_counter()
    with tempfile.TemporaryDirectory() as temp:
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            if solver == "epanet":
                r = wntr.sim.EpanetSimulator(w).run_sim(
                    file_prefix=str(Path(temp) / "run"), version=2.2,
                    convergence_error=True,
                )
            else:
                r = wntr.sim.WNTRSimulator(w).run_sim(convergence_error=True)
    if r.error_code is not None:
        raise RuntimeError("Solver error " + str(r.error_code))
    return r, [str(x.message) for x in captured], time.perf_counter() - began


def window(w, r, start, end, asset=None):
    step = int(w.options.time.report_timestep)
    idx = np.arange(start, end, step, dtype=int)
    junctions = w.junction_name_list
    if not set(idx).issubset(r.node["head"].index) or end not in r.node["head"].index:
        raise ValueError("Incomplete trajectory")
    pressure = r.node["pressure"].loc[idx, junctions].to_numpy()
    delivered = r.node["demand"].loc[idx, junctions].to_numpy()
    expected = wntr.metrics.expected_demand(
        w, start_time=start, end_time=end, timestep=step,
    ).iloc[:-1][junctions].to_numpy()
    positive = np.maximum(expected, 0)
    service = expected > 1e-10
    continuity = np.zeros_like(delivered)
    positions = {name: i for i, name in enumerate(junctions)}
    for name, link in w.links():
        flow = r.link["flowrate"].loc[idx, name].to_numpy()
        if link.start_node_name in positions:
            continuity[:, positions[link.start_node_name]] -= flow
        if link.end_node_name in positions:
            continuity[:, positions[link.end_node_name]] += flow
    continuity -= delivered
    theoretical = positive * np.sqrt(np.clip(pressure / 15, 0, 1))
    envelope = 0.0
    bound_error = 0.0
    final = {}
    for name, tank in w.tanks():
        levels = r.node["head"].loc[idx, name].to_numpy() - tank.elevation
        envelope += float(((levels <= tank.min_level + .2)
                          | (levels >= tank.max_level - .05)).sum() * step / 3600)
        bound_error = max(bound_error, float(np.maximum(tank.min_level - levels, 0).max()),
                          float(np.maximum(levels - tank.max_level, 0).max()))
        final[name] = float((r.node["head"].loc[end, name] - tank.elevation - tank.min_level)
                            / (tank.max_level - tank.min_level))
    pdd = float(np.abs(delivered[service] - theoretical[service]).max()) if service.any() else 0.0
    negative = float(np.maximum(-delivered[service], 0).max()) if service.any() else 0.0
    continuous = float(np.abs(continuity).max())
    finite = bool(np.isfinite(pressure).all() and np.isfinite(delivered).all())
    valid = bool(finite and bound_error <= 1e-4 and continuous <= 1e-5
                 and negative <= 1e-7 and pdd <= max(1e-5, .01 * float(positive.max())))
    result = dict(
        unmet_m3=float(np.maximum(positive - np.maximum(delivered, 0), 0).sum() * step),
        requested_m3=float(positive.sum() * step), envelope_tank_h=envelope,
        minimum_pressure_m=float(pressure.min()),
        negative_pressure_samples=int((pressure < -.001).sum()),
        negative_service_pressure_samples=int(((pressure < -.001) & service).sum()),
        max_pdd_residual_m3s=pdd, max_continuity_residual_m3s=continuous,
        max_negative_service_demand_m3s=negative, tank_bound_error_m=bound_error,
        finite=finite, assessable=valid, final_tank_fractions=final,
    )
    if asset is not None:
        result["realized"] = float((r.link["status"].loc[idx, asset] == 0).mean())
    return result


def summarize_task(w, r, state, asset=None):
    start = int(state["hour"] * 3600)
    release = start + int(state["hold_h"] * 3600)
    end = release + 6 * 3600
    result = {
        "hold": window(w, r, start, release, asset),
        "whole": window(w, r, start, end),
        "terminal": window(w, r, end - 3600, end),
    }
    return result


def paired_effect(action, reference):
    effects = {}
    for horizon in ("hold", "whole", "terminal"):
        a, b = action[horizon], reference[horizon]
        delta_u = (a["unmet_m3"] - b["unmet_m3"]) / b["requested_m3"]
        delta_e = a["envelope_tank_h"] - b["envelope_tank_h"]
        effects[horizon + "_unmet_delta"] = delta_u
        effects[horizon + "_tank_hours_delta"] = delta_e
        effects[horizon + "_harm"] = bool(delta_u >= .01 or delta_e >= 1)
    deficits = [reference["whole"]["final_tank_fractions"][n] - x
                for n, x in action["whole"]["final_tank_fractions"].items()]
    effects["terminal_storage_deficit"] = max(deficits)
    effects["recovery_failure"] = bool(effects["terminal_unmet_delta"] > .001
                                       or max(deficits) > .05)
    effects["realized"] = action["hold"]["realized"]
    effects["assessable"] = bool(action["whole"]["assessable"]
                                 and reference["whole"]["assessable"])
    effects["acceptable"] = bool(effects["assessable"] and effects["realized"] == 1
                                 and not effects["whole_harm"]
                                 and not effects["recovery_failure"])
    return effects


def trajectory(state, factor, solver, asset=None, step=300):
    checkpoint = DATA / "checkpoints" / f"{state['task_id']}_{step}.pkl"
    w = (pickle.loads(checkpoint.read_bytes()) if solver == "wntr" and checkpoint.exists()
         else model(state["network"], state["scale"], step))
    w.options.hydraulic.accuracy = 1e-6
    w.options.hydraulic.trials = 500
    w.options.hydraulic.unbalanced = "STOP"
    start = int(state["hour"] * 3600)
    release = start + int(state["hold_h"] * 3600)
    end = release + 21600
    w.options.time.duration = end
    impose_future(w, start, end, factor)
    if asset is not None:
        add_isolation(w, asset, start, release)
    r, warning_list, elapsed = run(w, solver)
    return w, r, warning_list, elapsed


def select_states():
    states = []
    for network in CATALOGUES:
        for split, lo, hi in [("train", 72, 120), ("calibration", 144, 168), ("test", 192, 240)]:
            for i, hour in enumerate(np.linspace(lo, hi, 24).round().astype(int)):
                outside = split == "test" and i >= 12
                factor = ([.75, 1.25] if outside else [.9, 1.1])[i % 2]
                states.append(dict(
                    task_id=f"{network}_{split}_{i:02d}", network=network, split=split,
                    order=i, hour=int(hour), scale=[.9, 1., 1.1][i % 3],
                    hold_h=6 if network == "C-Town" else 3,
                    hidden_factor=factor, outside_grid=outside,
                ))
    return states


def features(w, r, state, asset):
    t = int(state["hour"] * 3600)
    fractions = [(r.node["head"].loc[t, n] - tank.elevation - tank.min_level)
                 / (tank.max_level - tank.min_level) for n, tank in w.tanks()]
    link = w.get_link(asset)
    result = dict(
        hour_sin=float(np.sin(2*np.pi*state["hour"]/24)),
        hour_cos=float(np.cos(2*np.pi*state["hour"]/24)),
        scale=state["scale"], hold_h=state["hold_h"],
        tank_min=min(fractions), tank_mean=float(np.mean(fractions)), tank_max=max(fractions),
        is_pump=int(asset in w.pump_name_list),
        source_adjacent=int(link.start_node_name in w.reservoir_name_list
                            or link.end_node_name in w.reservoir_name_list),
        tank_adjacent=int(link.start_node_name in w.tank_name_list
                          or link.end_node_name in w.tank_name_list),
        minimum_pressure=float(r.node["pressure"].loc[t, w.junction_name_list].min()),
    )
    for name in CATALOGUES[state["network"]]:
        result["asset_" + name] = int(name == asset)
        result["status_" + name] = int(r.link["status"].loc[t, name] > 0)
    return {"x_" + name: float(value) for name, value in result.items()}


def checkpoint_group(states, step=300):
    """Reuse full native solver state, including controls, instead of reconstructing it."""
    network, scale = states[0]["network"], states[0]["scale"]
    w = model(network, scale, step)
    checkpoint_dir = DATA / "checkpoints"
    checkpoint_dir.mkdir(exist_ok=True)
    for state in sorted(states, key=lambda s: s["hour"]):
        w.options.time.duration = int(state["hour"] * 3600) - step
        run(w, "wntr")
        expected_next = int(state["hour"] * 3600)
        if abs(w.sim_time - expected_next) > 1e-8:
            raise ValueError("Checkpoint next-time mismatch")
        destination = checkpoint_dir / f"{state['task_id']}_{step}.pkl"
        destination.write_bytes(pickle.dumps(w))
    return dict(network=network, scale=scale, step=step, checkpoints=len(states))


def prepare_checkpoints(states, workers=6, step=300):
    groups = {}
    for state in states:
        groups.setdefault((state["network"], state["scale"]), []).append(state)
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(checkpoint_group, group, step) for group in groups.values()]
        for future in as_completed(futures):
            print("native checkpoints", future.result(), flush=True)


def storage_rule(w, r, state, asset):
    t = int(state["hour"] * 3600)
    graph = nx.Graph()
    graph.add_nodes_from(w.node_name_list)
    for name, link in w.links():
        if name != asset and r.link["status"].loc[t, name] > 0:
            graph.add_edge(link.start_node_name, link.end_node_name)
    expected = wntr.metrics.expected_demand(w, start_time=t, end_time=t, timestep=300).iloc[0]
    for component in nx.connected_components(graph):
        if any(n in component for n in w.reservoir_name_list):
            continue
        storage = sum(max(float(r.node["head"].loc[t, n]) - tank.elevation - tank.min_level, 0)
                      * np.pi * tank.diameter**2/4 for n, tank in w.tanks() if n in component)
        needed = sum(max(float(expected[n]), 0) for n in component if n in w.junction_name_list)
        needed *= (state["hold_h"] + 6)*3600*1.15
        if storage + 1e-9 < needed:
            return False
    return True


def one_state(state):
    started = time.perf_counter()
    reference, native, references_meta = {}, None, {}
    keys = [("forecast", f, "epanet") for f in FORECAST]
    keys += [("actual", state["hidden_factor"], s) for s in ("wntr", "epanet")]
    for tag, factor, solver in keys:
        key = f"{tag}:{factor}:{solver}"
        try:
            w, r, warning_list, elapsed = trajectory(state, factor, solver)
            reference[key] = summarize_task(w, r, state)
            references_meta[key] = dict(seconds=elapsed, warnings=warning_list)
            if tag == "forecast" and factor == 1:
                native = (w, r)
        except Exception as error:
            reference[key] = dict(error=repr(error))
            references_meta[key] = dict(error=repr(error))
    if native is None:
        return dict(state=state, error="No nominal native trajectory", references=references_meta)
    w, r = native
    active = [a for a in CATALOGUES[state["network"]]
              if r.link["status"].loc[int(state["hour"]*3600), a] > 0
              and (state["split"] == "test" or a not in RESERVED[state["network"]])]
    offset = state["order"] % len(active)
    candidates = (active[offset:] + active[:offset])[:4]
    results = []
    for asset in candidates:
        entry = dict(asset=asset, reserved=asset in RESERVED[state["network"]],
                     features=features(w, r, state, asset),
                     storage_rule=storage_rule(w, r, state, asset), evaluations={})
        for tag, factor, solver in keys:
            key = f"{tag}:{factor}:{solver}"
            try:
                a_w, a_r, warning_list, elapsed = trajectory(state, factor, solver, asset)
                action = summarize_task(a_w, a_r, state, asset)
                if "error" in reference[key]:
                    raise RuntimeError("Paired reference failed")
                effects = paired_effect(action, reference[key])
                entry["evaluations"][key] = dict(**effects, metrics=action,
                    seconds=elapsed, warnings=warning_list)
            except Exception as error:
                entry["evaluations"][key] = dict(error=repr(error), assessable=False,
                                                 acceptable=False)
        results.append(entry)
    return dict(state=state, candidates=candidates, references=references_meta,
                results=results, seconds=time.perf_counter()-started)


def generate(workers=6, smoke=False):
    OUT.mkdir(exist_ok=True)
    states = select_states()
    if smoke:
        states = [s for s in states if s["order"] == 0 and s["split"] == "train"]
    prepare_checkpoints(states, workers)
    (OUT / ("smoke_states.json" if smoke else "states.json")).write_text(json.dumps(states, indent=2))
    frozen = dict(code_sha256=sha(__file__), protocol_sha256=sha(ROOT/"protocol.md"),
                  seed=SEED, wntr=wntr.__version__, numpy=np.__version__, pandas=pd.__version__,
                  prospective_protocol_commit=json.loads((ROOT/"freeze.json").read_text())["protocol_commit"],
                  started_utc=pd.Timestamp.now(tz="UTC").isoformat(), tasks=len(states))
    (OUT / ("smoke_manifest.json" if smoke else "generation_manifest.json")).write_text(json.dumps(frozen, indent=2))
    receipts = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(one_state, s): s for s in states}
        for future in as_completed(futures):
            state = futures[future]
            try:
                record = future.result()
            except Exception as error:
                record = dict(state=state, error=repr(error))
            receipts.append(record)
            receipts.sort(key=lambda x: (x["state"]["network"], x["state"]["split"], x["state"]["order"]))
            path = OUT / ("smoke_receipts.json" if smoke else "receipts.json")
            path.write_text(json.dumps(receipts, separators=(",", ":")))
            print(f"completed {len(receipts)}/{len(states)} {state['task_id']} "
                  f"candidates={len(record.get('results', []))} error={record.get('error')}", flush=True)
    return receipts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    prepare_inputs(args.input_dir)
    generate(args.workers, args.smoke)


if __name__ == "__main__":
    main()
