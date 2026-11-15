# Recovery-aware water command screening

This repository supports the ten-page manuscript **Recovery-aware command screening
in water networks under demand shift**. It is a computational study of screening
limits, not a validated autonomous utility controller or a controlled LLM study.

The primary study contains 144 tasks, 530 candidate interventions and 1,440
counterfactual software-controller episodes. Its fresh-execution check has 288
attempted rollouts, comprising 170 action executions and 118 abstentions. The
separately locked follow-up adds 48 later tasks, 186 candidates and 1,440 policy
episodes under new baseline scales and time-varying hidden demand. Both solvers
share equations; these are not independent physical observations.

## Main evidence

Primary Net3 scenario screening increases acceptable catalogue completions from
8/24 under Hold RF to 13/24. In the follow-up it yields 7/24 and admits two
proxy-harmful tasks. The residual screen also admits those two Net3 cases and
withholds every C-Town task. Follow-up residual containment is 19/19 assessable
C-Town tasks and 20/24 Net3 tasks. The two Net3 failures exceed the declared
added tank-envelope-duration proxy, with zero added service shortage; no utility
damage is demonstrated. Negative findings are preserved.

The paper retains two figures, two editable main tables and five editable
equations. It cites 24 external sources plus the versioned dataset. Twenty-two
DOI entries match current Crossref records and two official documentation URLs
resolve. All-Q1, universal safety, nominal 90% test coverage, high novelty scores
and journal acceptance are not certified. The author review retains major
revision concerns for a competitive Knowledge-Based Systems submission.

## Protocol and data versions

The original protocol precedes outcomes at commit
153a985501389da24be5a7c73c43abaa57c19238 in the earlier repository
`ykunam/data-quality-budgeted-deferral`; that other study was not changed.
Read `protocol.md`, `amendments.md`, `residual_policy.md` and
`analysis_amendments.md` for the primary design and disclosed corrections.

The follow-up script, all 48 states and `followup_protocol.md` were committed
before new outcomes at 84ebcb31eba0afda32133a7099a33bd2c7883348. No training,
calibration, threshold, margin or endpoint was adapted to follow-up outcomes.
The immutable data release cited in the manuscript is
[49f0d2a6516885ec281a4a83e93ed63787b6c869](https://github.com/ykunam/water-task-assurance/tree/49f0d2a6516885ec281a4a83e93ed63787b6c869).
`DATASET.md` explains its provenance. The repository remains private; author
reviewer-access/public-release decisions and journal declarations remain pending.
No public data DOI is asserted and no unsupported confidentiality reason is used.

## Audit and rebuild from saved evidence

Python 3.12, CPU only:

```bash
python -m pip install -r requirements.txt
python -m unittest -v test_assurance test_followup
python audit_evidence.py
python build_compact.py --out manuscript.docx
python audit_revision.py --manuscript manuscript.docx
```

There are thirteen code invariants. The original arithmetic audit checks 35
conditions. The revision audit checks 30 conditions including compact-manuscript
citations, equations, table values and exact-data figures. Counts are accounting
and implementation checks, not a research-accuracy or originality percentage.
The delivered document was rendered and visually checked at ten pages. Check
pagination again in the target Word environment; this repository does not bundle
an office renderer. `build_paper.py` is retained as the earlier manuscript builder
and provides common document helpers; use `build_compact.py` for the new revision.

For the author audit and extended S1, use `build_revision_review.py` with the
preserved primary S1 as `--supplement-source`, output DOCX paths, `--pages 10`,
and an optional `--source-archive` pointing to the final reviewed commit archive.
The review package preserves that source S1. `revision_reference_verification.csv`,
`revision_journal_compliance.csv` and `revision_highlights.txt` accompany the paper.

## Full hydraulic regeneration

```bash
python assurance.py --workers 6
python analyze.py
python fine_step.py
python fresh_rollouts.py
python save_references.py
python followup_validation.py --write-states --generate --analyze --workers 6
python build_compact.py --out manuscript.docx
python audit_revision.py --manuscript manuscript.docx
```

The first preparation downloads the public BATADAL C-Town input and obtains
Net3 from WNTR 1.4.0, checking exact input hashes in `inputs.json`. Input bytes,
trusted local checkpoint pickles, smoke outputs and renderer pages are excluded.
Respect the original sources and terms; this project does not relicense those
models. Native full-state continuation avoids reconstructing hold/recovery from
telemetry endpoints. Solver validity and sampled actuator realization remain
explicit. A full campaign can take substantial time on different hardware.

`results/receipts.json.gz` and `references.json.gz` preserve primary action and
matched reference summaries. `followup_receipts.json.gz` includes both for every
new task. CSV/JSON files preserve candidates, fit manifests, controller episodes,
calibration/containment, fresh execution and sensitivity diagnostics. Original
`artwork/` remains unchanged; `revision_artwork/` supplies the new exact-data CSVs
and vector EPS/PDF figures. `release_sha256.json` describes the current reviewed
source/evidence bytes, excluding itself. Git history retains previous versions.

The candidate-restriction calculation in S1 is explicitly exploratory and was
not introduced as a new follow-up gate. It diagnoses sparse calibration and how
already-ineligible actions can dominate a global margin. The stored diagnostics
are independently reproduced by `audit_revision.py`.
