# Secondary taskwise discrepancy policy fixed before test analysis

This is an explicitly secondary prospective policy addition after generation
began. It was motivated by the literature and the training-only mechanics check.
No primary test outcomes or policy results were inspected before this rule was
written. Preserve this timing; do not call it part of the initial frozen protocol.

For every candidate, form six normalized consequence coordinates: incremental
unmet fraction and added tank hours over hold and whole task, incremental shortage
over the last recovery hour, and terminal normalized tank deficit. The respective
limits are .01, 1, .01, 1, .001 and .05. Let the predicted severity be their
maximum across all three forecast scenarios. Let actual severity be the same
maximum under WNTR and the evaluator's hidden demand factor.

On each calibration task with all candidate trajectories numerically assessable,
take the maximum positive actual-minus-predicted severity residual over all
available candidates. The margin is the order statistic with rank
ceil((m+1)*0.9), where m is the number of fully assessable calibration tasks.
If the rank exceeds m, the margin is infinite and every candidate is withheld.
No test data select the margin. Reserved assets remain excluded from calibration.

The residual task gate requires all three forecast members to be numerically
assessable, sampled isolation to be fully realized, and predicted severity plus
the taskwise margin to be strictly less than one. This includes hold, whole-task
and recovery predicates. Use this gate for both existing matched-budget agents.

Conditional algebraic property: if every candidate's actual severity is bounded
by its predicted severity plus the margin, every accepted candidate satisfies
the six declared inequalities. Because the residual event is simultaneous over
the candidate set, the implication also holds for adaptive selection and retries
within that set. This is an implication under an error-containment condition.
It is not a new formal-control theorem or a plant-safety guarantee. The familiar
split-conformal order statistic motivates the calibration construction, but
chronological dependence, reserved assets and outside-grid test demand invalidate
an unqualified exchangeability-based coverage claim. Report observed containment
and all violations rather than asserting 90% coverage.

Report this gate beside the original predeclared comparisons, including cases
where the margin suppresses useful work. Do not tune its confidence level, feature
set, thresholds or task aggregation after observing the test results.
