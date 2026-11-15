"""Create the author audit and supplementary detail from executed results."""
from pathlib import Path
import argparse
import csv
import json
import pandas as pd
from docx.shared import Pt
from build_paper import setup, table, ROOT, OUT, FIT, AGENTS, CANDIDATES


def compact():
    d=setup();d.styles['Normal'].font.size=Pt(11)
    d.styles['Normal'].paragraph_format.line_spacing=1.12
    d.styles['Normal'].paragraph_format.space_after=Pt(5)
    return d


def supplementary(destination):
    d=compact();d.add_paragraph('Supplementary methods and complete task screening results','Title')
    d.add_paragraph('Supplementary Material S1 for Taskwise uncertainty screening for water network isolation and recovery. All numerical values below come from the executed prospective extension. Source code, raw receipts, matched no-action metrics and amendments constitute S2 in the GitHub repository.')
    d.add_heading('S1 Implementation and interpretation',1)
    for t in [
        'The frozen design uses 144 native-trajectory tasks, up to four initially active candidates per task, and 530 candidate interventions. Native prefixes are retained as full WNTR solver/control state; hold and recovery are not reconstructed from endpoint tank levels. The input hashes, generator hash, prospective protocol, interruption/resume record and later analysis correction are retained.',
        'The original source hydraulic accuracy of 0.01 is replaced by 10⁻⁶ after the training-only smoke test. Numerical status requires both action and reference to pass the declared tolerances. These are research numerical checks, not utility validation. Actual unassessable test cases remain in task denominators and cannot count as acceptable work.',
        'C-Town local features: cyclic hour, observed base-demand scale, hold duration, minimum/mean/maximum normalized storage, pump/source/tank adjacency flags, minimum nominal pressure, eleven target indicators and eleven observed asset statuses (33 total). Net3 has the same eleven shared descriptors plus eight target/status pairs (27). Target indicators for reserved assets remain zero during development; their observed status is available as state information.',
        'Random forests have 300 trees, balanced classes, minimum leaf five and seed 20261115. Hold labels and whole-task failure labels are different targets. Indeterminate rows are excluded from fitting/calibration, never fabricated as harmful labels. A post-inspection correction removes all-missing columns from the other network; the initial fit and agent summaries remain archived.',
        'The storage rule uses an undirected current-status graph after proposed closure. Components without a reservoir must have tank water above minimum sufficient for current positive requested demand over hold plus six-hour recovery, multiplied by 1.15. It is a heuristic, not hydraulic pressure verification or an independent formal safety baseline.',
        'Forecasts use three future-demand factors; evaluation uses a different hidden factor and a different solver. The finite grid does not enclose every intermediate trajectory because native controls can make responses nonmonotone. Residual calibration uses taskwise maxima over all candidates on fully assessable actual calibration tasks with computable forecasts. Chronological dependence, exclusions and shift prevent unqualified conformal coverage.',
        'The 1,440 policy episodes reuse 48 test tasks, two controllers and fifteen gates. Both controllers have four attempts and the same candidates. Fresh execution checks Hold RF, Nominal task and Residual task choices under both controllers: 288 attempted rollouts, 170 fresh action simulations and 118 abstentions, all matching the cached categorical receipts. They do not provide independent new state samples or LLM replication.',
    ]:d.add_paragraph(t)
    d.add_page_break();d.add_heading('S2 Fitting and numerical evidence',1)
    rows=[]
    for net,m in FIT.items():
        rows.append((net,m['training_rows'],m['calibration_rows'],
            f"{m['training_indeterminate_excluded']}/{m['calibration_indeterminate_excluded']}",
            f"{m['threshold']:.2f}",f"{m['residual_margin']:.4f}",m['residual_calibration_tasks']))
    table(d,'Table S1. Development rows and thresholds',['Network','Fit n','Cal n','Unknown fit/cal','RF cutoff','Margin q','Margin tasks'],rows,[.8,.55,.55,1.3,.8,.9,1.0])
    parts=[]
    for net,m in FIT.items():
        failures=m['calibration_failures'];acceptable=m['calibration_rows']-failures
        parts.append(f"{net}: {round(m['calibration_failure_acceptance']*failures)}/{failures} calibration task failures accepted, {round(m['calibration_acceptable_retention']*acceptable)}/{acceptable} acceptable cases retained")
    d.add_paragraph('; '.join(parts)+'. These are composite task-failure targets, not the older manuscript’s harmful-command target. The residual margin ranks are 20 of 21 and 23 of 24 respectively.')
    for index,net in enumerate(['C-Town','Net3'],1):
        if index>1:d.add_page_break()
        d.add_heading(f'S3.{index} Complete controller results for '+net,1)
        a=AGENTS[AGENTS.network==net]
        rows=[]
        order=a.gate.drop_duplicates().tolist()
        for gate in order:
            c=a[(a.gate==gate)&(a.controller=='catalogue')].iloc[0]
            l=a[(a.gate==gate)&(a.controller=='learned ranking')].iloc[0]
            rows.append((gate,*[f"{int(c[k])}/{int(l[k])}" for k in ['completed','acceptable','harmful','indeterminate','recovery_failure','forecast_simulations']]))
        table(d,f'Table S{index+1}. '+net+' counts for catalogue order and learned ranking',
              ['Gate','Goals C/L','Acceptable C/L','Harm C/L','Indet. C/L','Recovery failure C/L','Forecast queries C/L'],
              rows,[1.95,.65,.95,.55,.65,.95,1.1])
        d.add_paragraph('C/L denotes catalogue/learned controller counts; Indet. denotes numerically indeterminate outcomes. Every cell uses 24 scheduled tasks per controller; abstentions and unrealized holds remain in the denominator. Harm, indeterminacy and recovery failure are distinct, potentially overlapping outcomes. Query counts represent action-forecast simulations, excluding shared reference simulations and fitting; they are not an online latency benchmark.')
        d.add_paragraph('All outcomes are simulation proxies. Equal outcomes do not establish equivalence outside this finite task pool. Numerical-validity and zero-margin joint ablations coincide with the scenario-task screen here; no additional measured benefit is attributed to an inactive predicate.')
    d.add_page_break();d.add_heading('S4 Dependence and sensitivity',1)
    contrasts=json.loads((OUT/'paired_contrasts.json').read_text())
    rows=[]
    for r in contrasts:
        if r['comparator'] in ['Hold RF','Nominal task']:
            lo,hi=r['block_interval'];rows.append((r['network'],r['controller'],r['comparator'],r['count_delta'],f"{100*lo:.1f} to {100*hi:.1f}"))
    table(d,'Table S4. Scenario-task acceptable completion minus comparator',
          ['Network','Controller','Comparator','Count difference','Descriptive interval pp'],rows,[.8,1.2,1.2,1.3,1.9])
    d.add_paragraph('Intervals use 2,000 circular task-block bootstrap replicates, block length three. Trajectories overlap and scenarios are deterministic. These intervals are descriptive; they do not resolve population dependence or establish causal effects. Forty-eight distinct test states, rather than the policy-episode count, govern the evidence scope.')
    d.add_paragraph('The fixed finer-step selection contains twelve candidates per network and compares actual-input EPANET at 300 s with 60 s using matched no-action references. All 24 whole-task harm and acceptable labels agree in this selected sample. WNTR at 60 s was not used for this sensitivity result.')
    d.add_heading('S5 Evidence map',1)
    for t in [
        'protocol.md and residual_policy.md distinguish the initial prospective design from secondary policy additions. amendments.md and analysis_amendments.md retain numerical corrections, control semantics, checkpoint reuse, the feature-column correction and the missing-dependency CI fix.',
        'results/receipts.json.gz contains all primary action metrics; results/references.json.gz contains freshly re-executed matched no-action metrics for arithmetic audit. results/candidate_outcomes.csv and candidate_decisions.csv retain continuous effects, class status, exclusions and every gate decision.',
        'results/agent_episodes.csv and agent_traces.json preserve proposals, denials, choices and workload. fresh_agent_rollouts.json and fresh_agent_summary.json retain the fresh execution checks. fit_manifest.json, residual_containment.json and paired_contrasts.json retain calibration and uncertainty evidence.',
        'historical_ctown_solver_diagnostic.json preserves twelve earlier cases under loose/tight EPANET and Newton solving. Tightening reduces residuals but does not eliminate all historical negative pressures. Historical Net3 control diagnostics identify different future link statuses after snapshot reconstruction; the new primary experiment uses full native continuation instead. Historical results are not silently relabeled.',
    ]:d.add_paragraph(t)
    d.save(destination)


def review(destination,pages):
    d=compact();d.add_paragraph('Scientific revision and submission readiness audit','Title')
    d.add_paragraph('Knowledge-Based Systems author review | 14 November 2026 | Recommendation: MAJOR REVISIONS')
    d.add_paragraph('The coding, prospective experiments, arithmetic verification and manuscript rewrite are complete. The revised contribution is a taskwise discrepancy construction and reproducible study of isolation/recovery screening limits. The mixed outcomes do not justify declaring a field-safe system, guaranteed uncertainty coverage or a submission-ready Q1 contribution. This is AI-assisted technical and editorial review, not an official journal decision or external human water/OT certification.')
    d.add_heading('1 What changed and what the evidence supports',1)
    outcomes=[
        ('GitHub coding','Dedicated private repository ykunam/water-task-assurance; source, protocol history, dependency list and automated tests.'),
        ('New primary evidence','144 native-trajectory tasks; 530 candidate interventions; 2,650 action solver evaluations and matched references; no state/actual-solver failures.'),
        ('Numerical correction','Tightened EPANET accuracy; complete-state checkpoint continuation; all 530 paired binary harm labels agree, with six acceptable-completion disagreements.'),
        ('Agent experiment','1,440 policy episodes across 48 distinct test tasks; 288 fresh attempted rollouts, including 170 action executions and 118 abstentions; every categorical receipt matches.'),
        ('Methodological addition','Taskwise maximum discrepancy margin over all candidate actions, a conditional implication for adaptive selection, and a matched zero-margin ablation.'),
        ('Scientific result','Scenario task screening yields 13/24 acceptable Net3 completions per controller; residual task screening yields 12/24 and withholds all C-Town tasks.'),
        ('Integrity corrections','Initial aggregate inspection exposed empty cross-network features. Corrected fits/comparisons and initial summaries are both retained; no test trajectory or endpoint was changed.'),
    ]
    table(d,'Revision evidence',['Component','Verified change or result'],outcomes,[1.45,5.35])
    audit=json.loads((OUT/'evidence_audit.json').read_text())
    d.add_paragraph(f"The numerical/reporting audit passes {audit['passed']}/{audit['total']} checks. Ten code-invariant tests pass locally and in a clean GitHub Actions installation after declaring WNTR’s missing explicit six dependency. These counts verify implementation and reporting; they are not research-accuracy or novelty scores.")
    d.add_heading('2 Research gap and novelty assessment',1)
    d.add_paragraph('The previous authority/gates/C-Town framing overlaps RDFR-CI. Temporal safety and recovery are already studied by MARIS-TRA; predictive safety filters and conformal order-statistic calibration are established. The new paper explicitly cites and distinguishes this work. Its narrower gap concerns simultaneous candidate-set discrepancy, actuator realization, numerical indeterminacy and useful whole-task completion under hidden demand and solver differences.')
    d.add_paragraph('The methodological originality is incremental: a taskwise calibration construction and conditional error-containment implication, coupled with a new prospective benchmark and negative findings. The empirical contribution is stronger than the earlier descriptive gate comparison. It does not establish a new general safety-filter theory or a universal performance advantage. Assigning a precise novelty percentage would create false precision; competitive KBS originality remains an editorial judgment.')
    d.add_paragraph('Important contrary evidence remains: residual containment is only 13/21 in assessable Net3 test tasks; C-Town’s margin exceeds the decision boundary and causes universal abstention; the zero-margin task screen retains one more acceptable Net3 completion than the residual screen; numerical-validity ablation produces no additional binary-decision benefit here. These results are retained prominently, not converted into positive superiority claims.')
    d.add_heading('3 Journal compliance checklist',1)
    checklist=[
        ('Authority','Verified dated source','All 20 pages of the supplied official guide captured 23 October 2026 were examined before the earlier editing. The live guide still returned HTTP 403; current portal currency remains unresolved.'),
        ('Article type','Regular article',f'{pages} rendered double-spaced pages, within the supplied preferred 20-page regular-article length. Exceeds the ten-page Short Communication limit.'),
        ('Editable structure','Applied','Single-column DOCX; numbered introduction, related work, methods, results, discussion, limitations/conclusion. Five native editable equations.'),
        ('Abstract and keywords','Verified','198-word abstract, no citations; six keywords within supplied range 1–7.'),
        ('Main artwork','Verified','Exactly two programmatic figures; source CSVs and separate vector EPS/PDF; all points checked against executed outputs.'),
        ('Main tables','Verified','Exactly two editable tables with captions and prose callouts, horizontal header rules and no shading/vertical borders. Counts match raw evidence.'),
        ('Highlights','Prepared','Four separate editable bullets, each no longer than 85 characters.'),
        ('References','29 entries','27 DOI-bearing sources and two official technical URLs; first-use numbering and citation completeness checked. All-Q1 certification is not met.'),
        ('Correspondence','Proposed','Personal email filled from the connected ykunam profile. Author must confirm final corresponding address and institutional affiliation.'),
        ('Supplementary files','Prepared','S1 methods/full comparisons; S2 source, raw receipts, references and amendments in GitHub. Portal handling still requires confirmation.'),
        ('Research data policy','Unresolved','Repository remains private as approved. Reviewer access or an approved public archival deposit and persistent dataset citation remain necessary.'),
        ('Funding interests CRediT','Prepared author action','No-funding/no-interest statements retained. Author must verify contributions and complete Elsevier’s declaration-tool workflow.'),
        ('AI disclosure','Applied','Assistance with software, analysis, writing and plots disclosed. Scripted policies are not described as a new controlled LLM experiment.'),
        ('Graphical abstract','No mandate verified','No graphical-abstract requirement was identified in the supplied guide. Any current portal-specific rule remains unverified.'),
        ('Originality clearance','Partial','No accepted-paper material copied. No commercial similarity-service, retraction-database clearance or copyright certificate is claimed.'),
        ('Formal submission','Not performed','No journal submission, external expert endorsement or acceptance assurance was made.'),
    ]
    table(d,'Compliance status',['Item','Status','Evidence or remaining action'],checklist,[1.25,1.1,4.45])
    with (ROOT/'journal_compliance.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['Item','Status','Evidence']);w.writerows(checklist)
    d.add_heading('4 Reference and citation verification',1)
    d.add_paragraph('The bibliography contains 29 sources: 24 journal articles, two NIST frameworks/standards, one conference paper and two official software/manual references. Twenty-one of the 24 journal articles come from MDPI, IEEE or Elsevier. Foundational method/data/conformal attribution requires three other publishers. Every source is cited, all citation numbers resolve and duplicate DOIs are absent. Three new DOI records were fetched for the temporal-assurance, conformal and TwinAI studies.')
    d.add_paragraph('reference_verification.csv maps every entry to its claim, metadata status, content-review scope and ranking qualification. Essential directly overlapping work is retained regardless of quartile. Water’s CiteScore and JCR quartiles differ; IEEE Access and TCST have metric-dependent statuses; the closest Information article does not establish an all-Q1 bibliography. The added studies’ current category/year rankings were not certified. DOI identity does not establish full scientific correctness; a comprehensive full-text and retraction review of every source is not claimed.')
    d.add_heading('5 Remaining scientific and submission issues',1)
    for t in [
        'MAJOR SCIENTIFIC: Nonvacuous cross-network uncertainty containment is not established. New independent operating profiles and calibration/uncertainty validation are needed for a stronger method claim; testing another threshold on the now-seen cases would not provide that evidence.',
        'MAJOR SCIENTIFIC: Only 48 correlated test tasks and eleven assessable harmful whole-task candidates limit generalization. Both solvers share model equations. The conditional proposition does not certify actual realization, numerical validity or plant safety. Human oversight and controlled LLM efficacy remain outside the demonstrated scope.',
        'MAJOR EDITORIAL: The novelty claim is now narrower and better supported, but remains incremental relative to established temporal assurance and calibration methods. A stronger KBS submission may require broader independent validation or a materially new mechanism, rather than additional citations or a higher self-assigned score.',
        'ACCESS AND AUTHOR ACTION: Approve suitable reviewer access/public archival deposit, add the linked dataset citation, confirm email/affiliation/contributions, complete Elsevier declarations, and conduct final human review. Private visibility has not been changed without authorization.',
        'POLICY AND BIBLIOGRAPHY: Verify current portal requirements. The requested universal Q1 condition and exhaustive full-text/retraction/plagiarism clearance remain unmet. Neither perfect references nor journal acceptance can be certified from the checks performed.',
    ]:d.add_paragraph(t)
    d.add_paragraph('Final recommendation: MAJOR REVISIONS for a competitive Knowledge-Based Systems submission. The code and evidence package are reviewable, and the manuscript accurately reports a computational failure-boundary study. The remaining scientific and access issues prevent a Ready for Submission declaration.')
    d.save(destination)
    highlights=[
        'Whole-task screening separates isolation success from acceptable recovery.',
        'Two native water models support 530 candidate interventions and paired solvers.',
        'Taskwise margins can withhold all work despite favorable containment counts.',
        'Net3 test residual containment falls below the nominal 90% calibration level.',
    ]
    assert all(len(x)<=85 for x in highlights)
    (ROOT/'highlights.txt').write_text('\n'.join('- '+x for x in highlights)+'\n')
    prepared=compact();prepared.add_paragraph('Declaration of competing interests','Title')
    prepared.add_paragraph('The author declares no competing interests.')
    prepared.add_paragraph('Prepared for author review. This statement is not the journal declarations tool’s generated output; the author must complete that workflow before submission.')
    prepared.save(destination.parent/'Competing_Interests_Prepared_Statement.docx')
    print('Created S1, scientific audit, compliance matrix, highlights and prepared interests statement.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True)
    p.add_argument('--supplement',type=Path,required=True);p.add_argument('--pages',type=int,required=True)
    args=p.parse_args();supplementary(args.supplement);review(args.report,args.pages)
