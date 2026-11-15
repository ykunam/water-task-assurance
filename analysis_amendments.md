# Analysis correction after the first aggregate inspection

The first combined-data analysis retained all-missing feature columns belonging
only to the other network. This accidentally enlarged the random forest's feature
sampling universe, despite fitting a separate model per network. It was corrected
by selecting only columns present in that network, giving 33 C-Town and 27 Net3
features. Reserved-asset indicator columns that are zero during training remain
present; they are not removed. Unexpected missing local features raise an error.

This correction was made after initial test aggregates had been inspected and
must not be described as outcome-blind. No physical trajectories, state selection,
future demand factors, endpoint cutoffs or policy definitions changed. All model
fitting, calibration and matched policy analysis were rerun consistently. The
initial fit and agent summaries are preserved in
results/initial_feature_join_analysis.json. No version was selected on the basis
of more favorable test performance.

Fresh agent execution uses the corrected, final choices. The generator's original
code hash and prospective protocol remain unchanged. The interrupted campaign
resumed from 70 saved task records after verifying the generator and state list;
results/resume_manifest.json records that continuation.

Clean GitHub Actions installation exposed a missing explicit `six` dependency
required by WNTR 1.4.0. The local numerical environment already used six 1.17.0.
It was added to requirements without changing the experiment environment or
outcomes. The initial failed CI run remains in the repository history.
