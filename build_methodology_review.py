"""Create the journal revision audit, highlights and cover letter."""
from pathlib import Path
import argparse
import csv
import json
from docx.shared import Pt
from build_paper import setup,table,ROOT,OUT
from build_methodology_revision import TITLE,AI


def report(destination,pages,source_url,ci_url):
    d=setup();d.styles['Normal'].font.size=Pt(11);d.styles['Normal'].paragraph_format.line_spacing=1.1;d.styles['Normal'].paragraph_format.space_after=Pt(5)
    d.add_paragraph('Journal compliance and methodological revision audit','Title')
    d.add_paragraph('Knowledge-Based Systems | Regular research article | 15 November 2026')
    d.add_paragraph('The manuscript has been revised as an editable regular research article within the author’s latest limit of fewer than twenty pages. The methodological contribution is an implemented calibration-support audit, with explicit loss handling, two conditional propositions, exact margin-defining witnesses and a prospectively frozen third cohort. The prior general conformal and safe-set ideas are credited. Recommendation: MINOR REVISIONS for final author review and submission administration; neither acceptance nor a numerical novelty score is asserted.')
    s=json.loads((OUT/'ssrn_summary.json').read_text());build=json.loads((OUT/'methodology_build_summary.json').read_text());audit=json.loads((OUT/'ssrn_evidence_audit.json').read_text());ma=json.loads((OUT/'methodology_manuscript_audit.json').read_text())
    d.add_heading('1 Methodological and scientific improvements',1)
    table(d,'Revision evidence',['Issue','Implemented change and evidence'],[
        ('Methodological specificity','Forecast-eligible action sets are scored explicitly. Invalid actual hydraulics or failed sampled actuation receive infinite loss. Marginal calibration retains all 24 scheduled calibration tasks per network.'),
        ('Calibration target','All-task marginal and opportunity-conditional calibration are separated. The latter has only four C-Town and seven Net3 opportunity tasks; a finite 90% empirical order statistic needs at least nine.'),
        ('Traceable mechanism','Both original margins are set by forecast-ineligible actions: PU7 fails forecast realization; pipe 240 already exceeds the forecast consequence limit. Values and causes are reconstructed from raw outputs.'),
        ('Prospective validation',f"The untouched third cohort contains 48 tasks, {s['candidates']} candidate interventions, {s['action_solver_evaluations']} action-solver evaluations and 576 matched counterfactual policy episodes. Original fits and historical margins remain locked."),
        ('Claim discipline','The new marginal gate coincides with the prior zero-margin joint gate in these data; the conditional gate abstains. The novelty claim is an executable water-task audit with original computational evidence, not a first general conformal algorithm or demonstrated plant safety.'),
    ],[1.25,5.55])
    d.add_paragraph('The third cohort uses hours 384–456, new observed scales 0.925/1.075 and three hidden Uniform(0.65,1.35) demand factors. Its policy, calibration scores and all states were frozen at 8d6c41cd81e97dcd110f191522eced3c17ccff65 before outcomes. The first two cohorts are retrospective for this extension. Eligibility-aware marginal screening gives 3/24 and 8/24 acceptable catalogue completions, with zero and two proxy-harmful outcomes. Conditional screening abstains on all 48 tasks. These negative or vacuous findings remain visible.')
    d.add_paragraph('The contribution fits the supplied KBS aims through symbolic screening rules, learned ranking, interpretable decision support and a balance of conditional analysis with engineering experiments. Its originality remains domain-specific and must be judged against the journal’s innovation threshold. It is not represented as a new general machine-learning or control theorem.')
    d.add_heading('2 Compliance checklist',1)
    rows=[
      ('Article type','Verified','Regular research article. The supplied guide prefers no more than 20 double-spaced pages; Short Communications have a separate ten-page maximum. Length does not automatically change article type.'),
      ('Main document','Verified',f"{pages} rendered pages; 12-point double-spaced body; {build['abstract_words']}-word abstract; six keywords; five editable equations; two editable tables; two figures. References are readable 10.5-point text."),
      ('Structure and scope','Verified','Introduction, related work, methods, propositions, results, discussion/conclusion and declarations; aligned with intelligent decision support, knowledge-based rules and data-science methodology.'),
      ('Figure and table accuracy','Verified','Two EPS/PDF artwork sets and source CSVs. All main table cells, 48 Figure 1 records and 384 Figure 2 stage records independently matched. Every bar retains 24 scheduled tasks.'),
      ('References','Verified within scope','26 cited entries in first-use order: 22 Crossref-verified DOI records, two official technical URLs, one arXiv preprint with its assigned DOI, and one pinned dataset. All identities checked; no full-text or commercial similarity clearance is claimed.'),
      ('Reference preference','Qualified','An all-Q1 or publisher-exclusive bibliography is not certified. Essential method/data/software attribution and the closest new preprint remain cited. Quartile qualifications are retained in the reference CSV.'),
      ('Highlights','Prepared','Four highlights, each no longer than 85 characters, supplied in a separate editable Word file.'),
      ('Funding and interests','Prepared','No specific funding and no competing interests retained from prior author instructions. The Elsevier declarations tool still needs to be completed and its generated Word file uploaded.'),
      ('Author attestations','Confirmed','Sole author, affiliation/contact, originality/exclusive journal submission and submission rights confirmed in this conversation. The newly revised final manuscript still requires the author’s own review.'),
      ('AI declaration','Prepared','Substantive ChatGPT Work assistance in design, code, analysis, references, plots and drafting is disclosed before the references. No false statement that final author review has already occurred is inserted.'),
      ('Data access','Out of blocker scope','Versioned evidence and accurate restricted-visibility statement retained. Reviewer-access arrangements are excluded from the blocking assessment at the author’s explicit instruction.'),
      ('Guide and template','Verified supplied sources','The complete newly attached twenty-page official guide dated 23 October 2026 and the full supplied reference paper were examined. The reference labels itself Short Communication but renders at nineteen pages here; its layout is not evidence of current compliance. No reference-paper text, data, figures or contribution was copied.'),
      ('Guideline currency','Partially verified','The supplied guide controls formatting; current live guide requests returned HTTP 403. Any later policy or portal-specific change remains unverified.'),
      ('Graphical abstract','No mandate verified','No mandatory graphical abstract identified in the supplied guide. No extra figure is added on an assumed requirement.'),
    ]
    table(d,'Journal checklist',['Item','Status','Evidence or remaining step'],rows,[1.2,1.05,4.55])
    with (ROOT/'methodology_journal_compliance.csv').open('w',newline='') as stream:
        w=csv.writer(stream);w.writerow(['Item','Status','Evidence']);w.writerows(rows)
    d.add_heading('3 Reproducibility and independent checks',1)
    d.add_paragraph(f"Eighteen code tests passed. The original 35-condition numerical audit and prior 30-condition manuscript/evidence audit remain passing. New scientific audit: {audit['passed']}/{audit['total']}; new manuscript audit: {ma['passed']}/{ma['total']}. These are implementation and accounting checks, not an accuracy or originality percentage. All new continuous effects and endpoint labels were recalculated using matched no-action references. Both solvers agree on whole-task harm labels; six acceptable-completion labels differ in the fresh cohort.")
    d.add_paragraph('Pinned source archive: '+source_url+'. Verification run: '+ci_url+'. The dataset citation points to evidence commit fb9b53e2523346d50347d749f3e41fbc91397384. Historical ssrn_* code/data filenames reflect the preliminary destination considered before the author corrected the target to KBS; the frozen scientific protocol was not changed.')
    d.add_heading('4 Remaining issues and recommendation',1)
    d.add_paragraph('The author should review the final revised Word file, confirm that the disclosed work reflects their scholarly contribution, complete the publisher’s declarations-tool workflow and verify the final portal fields. The cover letter and prepared competing-interest text are editable author materials, not a completed online submission or publisher-generated declaration. No manuscript was sent to the journal.')
    d.add_paragraph('Scientific limits remain: few opportunity-calibration tasks, shared hydraulic equations, overlapping trajectories, analyst-selected proxy thresholds, a finite forecast grid and no independent utility or physical validation. The paper reports a computational audit and observed failures. No unconditional 90% coverage, utility safety, LLM-agent efficacy or measured financial return is claimed.')
    d.add_paragraph('Final recommendation: MINOR REVISIONS for final author review and submission administration. The methodological shortcoming has been addressed with explicit implementation, proofs, support diagnostics, traceable witnesses and new prospective evidence. KBS editorial acceptance and the competitiveness of the domain-specific contribution remain external judgments.')
    d.core_properties.title='Knowledge-Based Systems journal compliance and methodological revision audit';d.core_properties.author='Yeshwanth Reddy Kunam';d.save(destination)


def extras(directory):
    highlights=[
      'An admissibility audit connects screening rules to calibration evidence.',
      'Invalid hydraulics and failed command realization remain explicit losses.',
      'Only four and seven calibration tasks support eligible interventions.',
      'A frozen 48-task cohort tests availability and uncertainty tradeoffs.',
    ]
    assert all(len(x)<=85 for x in highlights)
    d=setup();d.styles['Normal'].paragraph_format.line_spacing=1.15;d.add_paragraph('Highlights','Title')
    for text in highlights:d.add_paragraph(text,'List Bullet')
    d.core_properties.author='Yeshwanth Reddy Kunam';d.save(directory/'Highlights.docx')
    (ROOT/'methodology_highlights.txt').write_text('\n'.join('- '+x for x in highlights)+'\n')
    d=setup();d.styles['Normal'].paragraph_format.line_spacing=1.15;d.styles['Normal'].paragraph_format.space_after=Pt(8)
    d.add_paragraph('Cover letter to Knowledge Based Systems','Title');d.add_paragraph('15 November 2026');d.add_paragraph('Dear Editors,')
    d.add_paragraph('Please consider “'+TITLE+'” as a regular research article in Knowledge-Based Systems.')
    d.add_paragraph('The manuscript studies intelligent decision support for water-network interventions. It combines symbolic screening predicates with learned ranking and an explicit audit of calibration evidence. The audit distinguishes all-task marginal calibration from calibration among tasks with eligible actions and retains invalid hydraulics and failed realization as explicit losses.')
    d.add_paragraph('The contribution includes conditional containment analysis, a calibration-support test and exact witnesses showing why both original margins are determined by already-ineligible actions. A separately frozen third cohort of 48 tasks tests the audit on two native water-network models with new scales and time-varying hidden demand. All results, including proxy-harmful selections and vacuous abstention, are reported. The work balances methodological analysis, interpretable decision rules and reproducible engineering experiments within the journal’s intelligent decision-support scope.')
    d.add_paragraph('The author confirms that the manuscript is original, is not under consideration by another journal and has the necessary submission rights. No specific funding or competing interests are declared. Substantive AI assistance is disclosed in the manuscript. The general conformal and safe-set principles are credited to prior work; the paper’s contribution is the implemented water-task audit and its original computational evidence.')
    d.add_paragraph('Sincerely,\nYeshwanth Reddy Kunam\nMidwest University\nyeshwanth.kunam@gmail.com')
    d.core_properties.author='Yeshwanth Reddy Kunam';d.save(directory/'Cover_Letter_KBS.docx')
    d=setup();d.styles['Normal'].paragraph_format.line_spacing=1.15;d.add_paragraph('Declaration of competing interests','Title');d.add_paragraph('The author declares no competing interests.');d.add_paragraph('Prepared for author review. Complete Elsevier’s declarations tool and upload its generated Word statement during submission. This prepared file is not represented as tool generated.');d.save(directory/'Competing_Interests_Prepared_Statement.docx')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);p.add_argument('--pages',type=int,required=True);p.add_argument('--source-url',required=True);p.add_argument('--ci-url',required=True);args=p.parse_args();report(args.report,args.pages,args.source_url,args.ci_url);extras(args.report.parent)
