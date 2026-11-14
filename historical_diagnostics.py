"""Optional diagnosis of the preserved earlier research archive, never relabeling it.

Usage: python historical_diagnostics.py --legacy-dir PATH/TO/research
The primary prospective benchmark does not depend on these older source files.
"""
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import argparse
import json
import sys
import pandas as pd


def one_case(args):
    legacy, case = args
    sys.path.insert(0, str(Path(legacy) / "extension"))
    from validation import old, run, summarize
    row = old.read_data("BATADAL_dataset03.csv").iloc[int(case["row_index"])]
    result = {k:case[k] for k in ["snapshot", "row_index", "target", "status"]}
    for tag, solver, accuracy in [("original", "epanet", .01),
                                   ("tight", "epanet", 1e-6), ("newton", "wntr", 1e-6)]:
        try:
            w = old.setup(row, case["target"], int(case["status"]))
            w.options.hydraulic.accuracy = accuracy
            w.options.hydraulic.trials = 500
            w.options.hydraulic.unbalanced = "STOP"
            r, warning_list = run(w, solver)
            metrics = summarize(w, r, case["target"], int(case["status"]))
            result.update({tag + "_" + k:v for k,v in metrics.items()})
            result[tag + "_warnings"] = warning_list
        except Exception as error:
            result[tag + "_error"] = repr(error)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-dir", required=True)
    args = parser.parse_args()
    legacy = Path(args.legacy_dir).resolve()
    source = pd.read_csv(legacy / "results/physical_interventions.csv")
    selected = pd.concat([
        source[source.negative_pressure_samples > 0].sample(8, random_state=20261115),
        source[source.negative_pressure_samples == 0].sample(4, random_state=20261115),
    ])
    results = []
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(one_case, (str(legacy), row))
                   for row in selected.to_dict("records")]
        for future in as_completed(futures):
            results.append(future.result())
    out = Path(__file__).resolve().parent / "results/historical_ctown_solver_diagnostic.json"
    out.write_text(json.dumps(results, indent=2))
    print("Historical cases diagnosed:", len(results))
