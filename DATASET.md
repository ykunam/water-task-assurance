# Water command screening results for C-Town and Net3

Creator: Yeshwanth Reddy Kunam. Version: 15 November 2026 follow-up release.

The dataset contains simulator-derived command consequences, matched no-action
summaries, calibrated screen decisions and counterfactual software-controller
outcomes. The primary study contains 144 tasks and 530 candidate interventions;
the separately pre-specified follow-up adds 48 tasks and 186 candidates. The
primary and follow-up each contain 1,440 paired policy episodes over their
shared test task pools. They are not independent physical observations.

Primary action and reference summaries are in results/receipts.json.gz and
results/references.json.gz. Follow-up action and reference summaries are both in
results/followup_receipts.json.gz. The remaining followup_* files preserve the
locked task schedule, generation hashes, numerical/candidate summaries,
controller episodes and taskwise residual containment. The unchanged initial
protocol and original-generation manifest remain available in the same tree.

The follow-up protocol, executable script and all 48 tasks were committed before
new outcomes at 84ebcb31eba0afda32133a7099a33bd2c7883348. No original threshold,
margin, endpoint or fitted training/calibration partition was changed. The
original post-inspection feature correction remains disclosed separately.

Original C-Town input bytes belong to the BATADAL source, and Net3 is supplied by
WNTR 1.4.0. Input bytes and checkpoint pickles are not redistributed in this
repository. Their exact source and SHA-256 values are in inputs.json. Hash-checked
model preparation and executable analysis are supplied; this release does not
relicense third-party inputs or software.

The repository remains private under the author's earlier choice. The author
must arrange reviewer access or download the pinned GitHub source archive and
attach it as Supplementary Material S2. A public archival deposit and identifier
have not been created. Whether the journal accepts this private versioned
deposit at initial submission must be confirmed; no unsupported confidentiality
restriction is asserted.
