# Calibration support for water-network command screening

This repository supports the Knowledge-Based Systems research manuscript
**Calibration support and recovery-aware command screening in water networks**.
The current main manuscript is an editable regular research article under twenty pages
with two figures, two tables, five equations and 26 cited sources. The original
builders and all prior evidence remain available for historical reproducibility.

## Methodological contribution

`admissibility_audit.py` implements a task-set calibration support audit for
symbolic screening rules and learned or catalogue ranking. It distinguishes
all-task marginal calibration from opportunity-conditional calibration. Only
forecast-eligible candidates contribute to eligible-set scores. Invalid actual
hydraulics and incomplete sampled actuation contribute infinite losses instead
of being excluded. All 24 scheduled calibration tasks remain in the marginal
version. There are only four C-Town and seven Net3 opportunity tasks, fewer than
the nine needed for a finite 90% opportunity-conditional empirical rank.

The original margin-defining witnesses are already forecast-ineligible: PU7
fails sampled realization in two forecasts; pipe 240 exceeds the predicted
consequence limit. The generic conformal and safe-set inclusion principle is
prior work, including Bao et al., arXiv:2609.24496v1, cited as a preprint. The
contribution is the implemented water-task audit, traceable mechanism diagnosis
and original prospective computational evidence. No first general conformal
algorithm, universal coverage or plant-safety guarantee is claimed.

## Evidence chronology

| Cohort | Tasks | Candidate interventions | Role for the new audit |
| --- | ---: | ---: | --- |
| Primary | 144 | 530 | Includes training/calibration; its test outcomes are retrospective |
| First follow-up | 48 | 186 | Retrospective motivation |
| New third cohort | 48 | 186 | Prospectively frozen validation |

The primary protocol and amendments are retained in `protocol.md`,
`amendments.md`, `residual_policy.md` and `analysis_amendments.md`.
The first follow-up protocol and states were frozen at
84ebcb31eba0afda32133a7099a33bd2c7883348 before its outcomes.

The new method, all calibration scores, all 48 third-cohort task definitions and
`ssrn_validation_protocol.md` were frozen at
8d6c41cd81e97dcd110f191522eced3c17ccff65 before new outcomes. Times are hours
384–456, observed scales 0.925/1.075 and three hidden Uniform(0.65,1.35) demand
factors, seed 2026111503. Original fits, historical margins, numerical tolerances
and endpoints remain unchanged. The `ssrn_*` filenames are historical cohort
identifiers: the author corrected the preliminary destination from SSRN to KBS
after the freeze. The scientific protocol and all adverse outcomes were kept.

The new six-gate/two-controller comparison contains 576 counterfactual policy
episodes over 48 task pools. Eligible marginal screening gives 3/24 and 8/24
acceptable catalogue completions, with zero and two proxy-harmful outcomes.
Opportunity-conditional screening abstains throughout. The marginal rule
coincides with the prior zero-margin joint rule in these data. These are not
controlled LLM experiments or 576 independent physical trials. The earlier
288 fresh attempted rollouts (170 executions, 118 abstentions) remain archived.

## Rebuild and verify

Python 3.12, CPU only, with the pinned requirements:

```bash
python -m pip install -r requirements.txt
python -m unittest -v test_assurance test_followup test_admissibility
python audit_evidence.py
python build_compact.py --out /tmp/prior_manuscript.docx
python audit_revision.py --manuscript /tmp/prior_manuscript.docx
python analyze_ssrn.py
python build_methodology_revision.py --out /tmp/journal_manuscript.docx
python audit_methodology_manuscript.py --manuscript /tmp/journal_manuscript.docx
```

There are 18 code tests, 35 original numerical/evidence checks, 30 previous
revision checks, 17 new scientific checks and 18 current manuscript checks.
The new audit recomputes continuous effects and labels from matched no-action
metrics, checks frozen hashes, preserves all tasks, and validates table/figure
source data. These counts are not an originality or research-accuracy score.
The Word document is rendered and visually checked separately; office rendering
is not bundled with this repository. Check pagination in the target Word setup.

`build_methodology_review.py` prepares the current compliance report, highlights
and cover letter. `build_methodology_revision.py` can also extend S1 when supplied
with the preserved earlier supplement and an immutable source-archive URL.
All full outcome comparisons and conditional proofs are retained in S1.

## Regeneration and versions

To regenerate the new hydraulics in an isolated checkout:

```bash
python ssrn_validation.py --generate --workers 6
python analyze_ssrn.py
```

Do not rerun `--freeze` after observing outcomes or overwrite the pre-outcome
calibration manifest. The original input hashes and source URLs remain in
`inputs.json`; downloaded third-party INP files and native checkpoints are not
redistributed here. The primary and first-follow-up regeneration commands remain
in their scripts and protocols. This study continues full native solver/control
state and does not reconstruct prefixes from endpoint tank levels.

Primary/first-follow-up dataset:
https://github.com/ykunam/water-task-assurance/tree/49f0d2a6516885ec281a4a83e93ed63787b6c869

Third-cohort evidence and analysis:
https://github.com/ykunam/water-task-assurance/tree/fb9b53e2523346d50347d749f3e41fbc91397384

The repository remains private, as verified against the connected author-owned
account. Reviewer-access arrangements are outside the requested blocking audit.
The manuscript accurately states restricted visibility. No public DOI or
unsupported confidentiality explanation is invented.

Twenty-two selected DOI records were verified against Crossref, two official
technical URLs resolve, and the additional arXiv citation was checked at its
primary record. Essential method/software/data citations and the closest prior
preprint are retained; an all-Q1 bibliography is not certified. Author details,
originality/exclusive submission and submission rights were confirmed. The final
revised Word manuscript still needs author review and completion of the
publisher's declarations-tool workflow.
