# Prospective validation of the admissibility and calibration support audit

This extension follows inspection of the primary and first follow-up outcomes.
Those two cohorts are retrospective development evidence for the new audit.
Neither is relabeled as a prospectively held-out evaluation of the new method.

The general conformal calibration and safe-set inclusion principle is prior
work (Angelopoulos and Bates; Bao et al., arXiv:2609.24496). The contribution
claimed here is an implemented water-task audit combining eligible-set scoring,
non-exclusion of invalid/failed-realization outcomes, an explicit distinction
between all-task marginal and opportunity-conditional calibration, and a fresh
two-network computational validation. Do not claim a first general conformal
safe-set method, a new universal control theorem, or physical safety.

The base gate uses only the three existing forecasts: all numerically assessable,
fully sampled-realized, and maximum six-coordinate severity strictly below one.
For each original calibration task, score the maximum positive actual-minus-
predicted severity residual over base-eligible actions. Use zero for no eligible
actions. An eligible action with invalid actual hydraulics or incomplete actual
realization contributes infinity. Retain every scheduled calibration task.

All-task calibration uses all 24 original calibration tasks per network.
Opportunity-conditional calibration uses the label-blind subset with at least
one base-eligible action. Both use alpha=0.1 and rank ceil((m+1)*0.9), with an
infinite margin if rank exceeds m. No confidence level or gate is tuned after
new outcomes. Preserve both calibration support counts and all infinity values.
Freeze the computed calibration manifest, source files and task plan before
generating new outcomes. Original RF fits and original residual margins stay
unchanged.

New cohort: 24 tasks per network, hours 384–456, observed scales alternating
0.925/1.075, three hidden factors from Uniform(0.65,1.35), seed 2026111503.
The three factors apply across the first isolation half, second half and six-hour
recovery on native pattern slots. Native trajectories and controls are continued.
The existing follow-up evaluator generates three EPANET forecasts, actual WNTR,
actual EPANET and their matched no-action metric summaries. Up to four initially
active candidates rotate from the existing test catalogue; test-reserved assets
stay outside fitting and calibration. No input, endpoint or numerical tolerance
is changed.

Evaluate Hold RF, Nominal task, Scenario task, original Residual task,
Eligible marginal and Eligible conditional gates with both catalogue and locked
learned ranking, sharing candidate pools and four attempts. Save all 576 policy
episodes, all candidate outcomes, task-score containment, numerical status and
calibration attribution. These are counterfactual software-policy evaluations,
not fresh LLM trials, independent physical experiments or a new calibration set.

Report adverse and null outcomes. The chronological shifted design does not
establish exchangeability. Any conformal probability statement must be explicitly
conditional on its mathematical assumptions, separate from measured containment.
No retry, gate, fit, calibration margin or test schedule changes are permitted
after the frozen commit except a disclosed execution-error correction.
