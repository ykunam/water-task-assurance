# Locked follow-up validation for the ten-page revision

This protocol is written after inspecting the original 144-task study. It is a
separate prospective extension, not a replacement for the original test set.
No follow-up hydraulic outcomes may be inspected before this file, the script
and the task list have been committed to GitHub.

Use 24 new tasks per network, at rounded equally spaced integer hours 288–360.
Alternate observed baseline scales 0.95 and 1.05, which were not used in the
original design. Draw three continuous hidden factors independently from
Uniform(0.70,1.30), NumPy default_rng seed 2026111502. Apply them over the first
half of isolation, the second half, and recovery; changes take effect on native
demand-pattern sampling slots. Original forecast factors remain constant at
0.85, 1 and 1.15 and never receive the hidden profile.

Keep all original assets, candidate rotation, maximum four candidates/attempts,
hold/recovery lengths, hydraulic settings, numerical tolerances and endpoints.
Use full native state continuation. Preserve every scheduled task and any
failure. The original random-forest fits, score cutoffs and residual margins
are locked: fit only the original training rows and calibrate only the original
calibration rows. Check their metadata against the saved original manifest.
Do not adapt any gate, endpoint or cutpoint using follow-up outcomes.

Report all fifteen gates and both software-controller orderings, candidate
outcomes, eligibility, harm, acceptable completion, abstention, recovery and
taskwise residual containment. These are counterfactual software-policy
evaluations on new simulated tasks, not independent physical observations,
human-oversight experiments or new LLM trials. Both solvers share equations.

The explicit objective is to test whether the original screening/availability
tradeoff and residual-coverage limitations persist under new baseline scales,
later operating times and time-varying hidden demands. No positive result is
required. This follow-up was motivated by the earlier results and must be
identified as such. The 48 follow-up tasks are not merged into the original
calibration set. Six-worker CPU execution is time-bounded by the user's overall
two-hour revision limit; any interruption must retain partial results and be
reported instead of selecting favorable completed cases.
