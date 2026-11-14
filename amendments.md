# Implementation clarifications before the primary run

The pre-outcome protocol commit is 153a985501389da24be5a7c73c43abaa57c19238 in
ykunam/data-quality-budgeted-deferral on research/water-task-assurance-20261114.
Only the protocol, input hashes and dependency list were committed there.
The user subsequently requested a dedicated repository.

The training-only smoke run checks mechanics and is not part of the primary
results. It must not be used to choose more favorable test states or cutoffs.

1. Whole-task RF predicts failure of acceptable completion, including endpoint
   harm, recovery failure or unrealized hold. Hold RF predicts the hold harm
   endpoint. Indeterminate training/calibration cases are excluded from fitting
   and threshold calibration and counted explicitly; no unknown outcome is
   invented as a harmful label. Calibration's 5% target applies to this composite
   task failure and is distinct from the older manuscript's harmful-command target.
2. Numerical assessability is recorded for all windows; primary whole-task
   assessability requires both action and matched reference to pass. A failed
   trajectory remains indeterminate and never counts as acceptable completion.
3. Robust task verification without numerical checks is an explicit ablation,
   never the primary rule. Three-scenario checking is a finite forecast ensemble,
   not a continuous uncertainty-set guarantee.
4. Candidate verification is precomputed for reproducibility and joined by key.
   Controllers use only forecasts, fitted scores and denial receipts. Actual
   evaluator outcomes are joined after the selected asset is fixed. Report
   equivalent simulation workload, not cached execution as online speed.
5. The source C-Town model uses hydraulic accuracy 0.01. The training-only smoke
   run exposed PDD residuals exceeding the predeclared numerical tolerance.
   Before the primary campaign, both networks use accuracy 1e-6, 500 trials and
   STOP on nonconvergence. No numerical validity threshold was relaxed. WNTR
   uses its documented default Newton convergence tolerance. This is a numerical
   solver correction, not a change selected from held-out performance.
6. Native controls remain active. A highest-priority rule is a requested
   override, not proof that all native control processing honors it continuously.
   Sampled unrealization in the smoke run is preserved and is a reason to withhold
   a forecast action; no realized command or failed goal is silently relabeled.
7. Native WNTR prefixes are cached by pausing with the complete solver model
   before task start, then deep-copying that complete state for continuation.
   No head/tank/status-only reconstruction is used. Full-run equivalence must
   be tested before primary generation. This does not split hold from recovery.
