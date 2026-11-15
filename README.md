# Water task assurance

Reproducible simulation research on screening water-network commands over an
isolation hold and recovery phase. The study compares learned prediction,
connectivity/storage rules, nominal hydraulic prediction and finite-demand-scenario
verification. It separates authorization, numerical assessability, command
realization, proxy harm and acceptable task completion.

This is a computational benchmark, not utility validation or independent human
engineering certification. The main controllers are software planning agents.
No new controlled multi-model LLM result is claimed.

## Executed evidence

The completed extension contains 144 tasks (72 per network), 530 candidate
interventions and 2,650 primary action-solver evaluations. There are 24 test tasks
per network. Fifteen screens and two matched-budget software controllers produce
1,440 policy episodes over those shared test tasks, not 1,440 independent cases.
An additional 288 attempted fresh rollouts include 170 hydraulic action
executions and 118 abstentions; all categorical outcomes match cached receipts.

For catalogue-order selection, three-scenario task screening completes 13/24
Net3 tasks acceptably, compared with 8/24 under Hold RF. Nominal task screening
completes 14/24 acceptably with one recovery failure. The secondary residual
screen completes 12/24 Net3 tasks and withholds every C-Town task. Its taskwise
residual containment is 19/20 in assessable C-Town test tasks and only 13/21 in
Net3. These results do not support an unqualified 90% test-coverage guarantee or
universal improvement. The methodological contribution is incremental.

All 530 paired whole-task binary harm labels agree across the two solvers;
acceptable-completion labels differ in six C-Town cases. A fixed 24-case EPANET
60-second sensitivity sample changes neither harm nor acceptable labels. Both
solvers share model equations, so agreement is not physical validation.

The manuscript has two main figures, two editable main tables and 29 references.
The journal/reference checks are in `journal_compliance.csv` and
`reference_verification.csv`. All-Q1 certification is **not** claimed. The author
audit recommends **major revisions** for a competitive Knowledge-Based Systems
submission: independent uncertainty validation, a stronger originality case,
reviewer/data access, current portal checks and author declarations remain open.
This repository remains private; a public data DOI has not been minted.

## Prospective revision and disclosed corrections

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

`residual_policy.md` records the separately timestamped secondary margin and
zero-margin policy additions. `analysis_amendments.md` records a feature-column
correction made after initial aggregate inspection, and preserves the initial
analysis. No test trajectory, endpoint or demand factor was changed to improve
performance. The initial source accuracy was tightened after a training-only
mechanics check; numerical validity thresholds were not relaxed.

## Audit saved evidence

Python 3.12, CPU only. Install the pinned environment:

```bash
python -m pip install -r requirements.txt
python -m unittest -v test_assurance
python audit_evidence.py
```

Saved compressed receipts and matched no-action metrics allow arithmetic
verification without rerunning the full hydraulic campaign. The numerical audit
checks 35 evidence/provenance conditions. Supplying the revised DOCX with
`--manuscript PATH` adds ten citation, equation, table and reporting checks; the
delivered manuscript passes 45/45. Ten code-invariant tests also pass. These are
implementation checks, not a research accuracy or novelty percentage.

To refit the locked analysis and regenerate figures and manuscript content:

```bash
python analyze.py
python build_paper.py --out manuscript.docx
python audit_evidence.py --manuscript manuscript.docx
python build_review.py --report author_audit.docx --supplement S1.docx --pages 14
```

The final command's page count describes the delivered render; check pagination
again in the target Word/LibreOffice environment. Rendering DOCX requires a local
office/PDF renderer; this repository does not claim to supply that application.

## Rerun the hydraulic campaign

```bash
python assurance.py --workers 6
python analyze.py
python fine_step.py
python fresh_rollouts.py
python save_references.py
python build_paper.py --out manuscript.docx
python audit_evidence.py --manuscript manuscript.docx
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
controllers under every gate. The post-inspection implementation correction is
disclosed separately. No test scenarios or endpoint cutoffs were tuned on test
performance. Cached prediction work is counted as equivalent simulator
queries; cached replay time is not online verification latency.

The full campaign uses CPU parallelism and can take substantial time. Original
model inputs, trusted checkpoint pickles, smoke outputs and renderer images are
excluded from version control. `resume_generation.py` documents continuation of
the interrupted original run; a clean reproduction normally uses `assurance.py`.
`historical_diagnostics.py` is an optional diagnostic for the earlier study and
requires its separately retained archive through `--legacy-dir`; no primary
experiment depends on that archive.

`results/receipts.json.gz` holds primary action summaries;
`results/references.json.gz` holds matched no-action summaries. Other result files
retain fits, continuous outcomes, every gate decision, controller traces, fresh
execution checks and sensitivity diagnostics. `artwork/` contains exact-data
CSVs and separate vector EPS/PDF figures. `release_sha256.json` records the stored
source/evidence byte hashes; commit history provides the immutable versions.

## Scientific scope

Research thresholds are illustrative, not regulatory limits. Both solvers share
hydraulic equations; different algorithms do not create independent physical
ground truth. Demand scenarios do not model treatment chemistry, water quality,
pipe damage, all actuator faults or human behavior. Future datasets, broader
uncertainty and independent utility/engineering review are needed for deployment.

Only executed results may enter the manuscript. Novelty and submission status are
assessed separately from passing tests. No journal acceptance guarantee or
fabricated novelty/accuracy percentage is provided.
