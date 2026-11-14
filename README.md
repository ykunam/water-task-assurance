# Water task assurance

Reproducible simulation research on screening water-network commands over an
isolation hold and recovery phase. The study compares learned prediction,
connectivity/storage rules, nominal hydraulic prediction and finite-demand-scenario
verification. It separates authorization, numerical assessability, command
realization, proxy harm and acceptable task completion.

This is a computational benchmark, not utility validation or independent human
engineering certification. The main controllers are software planning agents.
No new controlled multi-model LLM result is claimed.

## Prospective revision

Read `protocol.md` and `amendments.md` before interpreting results. The original
prospective protocol was committed before new intervention outcomes at
`ykunam/data-quality-budgeted-deferral`, commit
`153a985501389da24be5a7c73c43abaa57c19238`. The user then requested this dedicated
repository. That earlier branch contains only the protocol and input/dependency
records for this extension; the earlier deferral study is unchanged.

The revised experiment uses 144 tasks across C-Town and Net3, with chronological
training/calibration/test partitions and reserved assets. Demand forecasts see
factors 0.85, 1 and 1.15. Evaluation uses a hidden future factor and a different
hydraulic solver. Half the new test tasks lie outside the finite forecast grid.
The discrete grid is not a guarantee over all intermediate demands or disturbances.

## Reproduction

Python 3.12, CPU only. Install the pinned environment:

```bash
python -m pip install -r requirements.txt
python -m unittest -v test_assurance
python assurance.py --workers 6
python analyze.py
```

The first generation run downloads C-Town's public input from BATADAL and copies
Net3 from the installed WNTR 1.4.0 distribution. Input hashes are checked against
`inputs.json`. Respect the original model sources and their terms; this repository
does not relicense or redistribute the original model input bytes. Supply an
existing exact input directory with `--input-dir PATH` for offline execution.

Generation caches the entire native WNTR model state before task start, including
control and solver state, then continues each task without a hold/recovery
restart. Checkpoint objects are trusted local intermediates and are not committed.
Do not load pickle or joblib files obtained from untrusted sources. EPANET runs
the full native prefix independently. Results remain solver-based proxies.

`--smoke` runs only the first training state per network. It checks mechanics and
does not reproduce or replace the primary results. `analyze.py --smoke` summarizes
that engineering check. Failure records and all denominators remain visible.

`analyze.py` fits only on assessable training rows, calibrates only on assessable
calibration rows, and evaluates each test candidate and two matched-budget
controllers under every gate. It never changes test scenarios or cutoffs based
on test performance. Cached prediction work is counted as equivalent simulator
queries; cached replay time is not online verification latency.

## Scientific scope

Research thresholds are illustrative, not regulatory limits. Both solvers share
hydraulic equations; different algorithms do not create independent physical
ground truth. Demand scenarios do not model treatment chemistry, water quality,
pipe damage, all actuator faults or human behavior. Future datasets, broader
uncertainty and independent utility/engineering review are needed for deployment.

Only executed results may enter the manuscript. Novelty and submission status are
assessed separately from passing tests. No journal acceptance guarantee or
fabricated novelty/accuracy percentage is provided.
