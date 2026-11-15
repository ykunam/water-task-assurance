"""Build the concise revision audit and extend the verified supplementary methods."""
from pathlib import Path
import argparse
import csv
import json
import pandas as pd
from docx import Document
from docx.shared import Pt
from build_paper import setup,table,ROOT,OUT
from build_compact import TITLE


def compact():
    d=setup();d.styles['Normal'].font.size=Pt(11)
    d.styles['Normal'].paragraph_format.line_spacing=1.1
    d.styles['Normal'].paragraph_format.space_after=Pt(5)
    return d


def supplement(source,destination,source_archive=None):
    d=Document(source)
    for p in d.paragraphs:
        if 'calibration task failures' in p.text:p.text=p.text.replace('calibration task failures','calibration candidate failures')
    d.paragraphs[1].text=('Supplementary Material S1 for '+TITLE+'. Sections S1–S5 retain the primary 144-task study; Sections S6–S8 document the separately pre-specified 48-task follow-up and subsequent diagnostic analysis. S2 is the pinned GitHub source-and-data archive.')
    d.add_page_break();d.add_heading('S6 Locked follow-up design and verification',1)
    dataset=json.loads((ROOT/'revision_dataset.json').read_text())
    summary=json.loads((OUT/'followup_summary.json').read_text())
    d.add_paragraph('The follow-up protocol, script and all 48 task definitions were committed before new outcomes at '+dataset['freeze_commit']+'. It was motivated by the primary results. Hours are 288–360, observed scales alternate 0.95/1.05, and three hidden continuous factors drawn from Uniform(0.70,1.30) with seed 2026111502 apply during the first isolation half, second half and recovery. Changes occur on native pattern slots; forecasts retain the original three constant factors. Training rows, calibration rows, cutoffs and margins remain unchanged. This is a new computational validation cohort, not independent physical validation.')
    d.add_paragraph('All 48 task records complete, with 186 candidate interventions and 930 action-solver evaluations. Each task stores five matched no-action metric summaries. The additional 1,440 policy episodes reuse this cohort and are counterfactual evaluations; they do not duplicate the primary study’s 288 fresh attempted executions or constitute new LLM trials. Numerically assessable primary and follow-up controller outcomes remain separate.')
    d.add_paragraph('The three new invariants check the later task schedule, hidden-profile separation from forecast labels, and preservation of the native demand prefix and negative injections. The revision audit independently recomputes continuous effects, proxy labels, numerical status, selected outcomes, figure data and table cells from the saved references and action receipts. The follow-up paired solvers agree on all binary whole-task proxy-harm labels; four acceptable-completion labels differ. No new 60-second sensitivity experiment is claimed.')
    rows=[]
    for net in summary['networks']:
        c=summary['containment'][net['network']]
        rows.append((net['network'],net['tasks'],net['candidates'],net['assessable'],net['acceptable'],net['harmful'],net['feasible_tasks'],f"{c['contained']}/{c['assessable']}"))
    table(d,'Table S5. Follow-up opportunities and containment',
        ['Network','Tasks','Candidates','Assessable','Acceptable','Harmful','Feasible tasks','Contained'],rows,[.8,.5,.85,.9,.9,.75,.95,.85])
    d.add_paragraph('Feasible tasks contain at least one actually acceptable candidate; they provide a finite-pool opportunity ceiling, not an implementable oracle or deployment guarantee. Residual containment excludes five numerically indeterminate C-Town tasks and retains them in all scheduled-task reporting. All 24 Net3 follow-up tasks are assessable.')
    a=pd.DataFrame(json.loads((OUT/'followup_agent_summary.json').read_text()))
    for number,net in enumerate(['C-Town','Net3'],6):
        d.add_page_break();d.add_heading(f'S7.{number-5} Complete follow-up controller results for '+net,1)
        rows=[]
        for gate in a[a.network==net].gate.drop_duplicates():
            c=a[(a.network==net)&(a.gate==gate)&(a.controller=='catalogue')].iloc[0]
            l=a[(a.network==net)&(a.gate==gate)&(a.controller=='learned ranking')].iloc[0]
            rows.append((gate,*[f'{int(c[k])}/{int(l[k])}' for k in ['completed','acceptable','harmful','indeterminate','recovery_failure','abstained']]))
        table(d,f'Table S{number}. '+net+' follow-up counts',
            ['Gate','Goals C/L','Acceptable C/L','Harm C/L','Indet. C/L','Recovery failure C/L','Abstained C/L'],rows,[1.95,.65,.95,.55,.65,.95,1.1])
        d.add_paragraph('C/L denotes catalogue/learned ranking. Each outcome uses 24 scheduled tasks per controller. Harm and recovery failure are reported only for assessable selected outcomes; indeterminacy is separate. Counts can overlap and do not define the mutually exclusive priority stages used in Figure 2.')
    d.add_page_break();d.add_heading('S8 Counterexamples and exploratory calibration diagnosis',1)
    d.add_paragraph('Both follow-up Net3 proxy-harmful residual-screen selections target pipe 20. At hour 319, scale 0.95, hidden factors are 0.95168875, 1.29835860 and 1.01956304. Forecast severity is 0.500, the locked margin is 0.30429962, and actual severity is 1.500. At hour 326 the profile is 1.03101699, 1.19445485 and 1.15641417; forecast severity is 0.49674988 and actual severity is 1.41666667. Both actual closures are fully sampled-realized, numerically assessable and satisfy the terminal recovery criteria. The violated constraint is added tank-envelope duration; whole-task added shortage is zero. These are explicit failures of the declared proxy screen, not observed utility damage.')
    d.add_paragraph('An exploratory post-primary diagnostic restricts calibration residuals to candidates that the existing scenario/joint screen could admit before adding a nonnegative margin. Among the same fully assessable calibration tasks, only four C-Town and 27 Net3 candidates are eligible. Their restricted 90% order-statistic margins are zero, versus 3.7052/0.3043 over all candidates. This diagnoses how actions already rejected by other predicates can dominate a global margin. It is not a newly validated alternative gate: restricting the eligible set creates sparse calibration evidence and empty tasks. No follow-up policy or threshold was changed using this diagnostic.')
    d.add_paragraph('Data are pinned at '+dataset['url']+'. The source archive available to the author is '+(source_archive or dataset['archive_url'])+'. Repository access remains restricted. The author must supply reviewer access or attach the archive as S2 and confirm the publisher accepts the chosen data deposit/access arrangement.')
    d.save(destination)


def review(destination,pages):
    d=compact();d.add_paragraph('Ten page revision and submission readiness review','Title')
    d.add_paragraph('Knowledge-Based Systems | 15 November 2026 | Scientific and editorial assessment')
    d.add_paragraph('The requested ten-page revision is complete, with the original fourteen-page document preserved. Repetition and five broad/out-of-scope references were removed; detailed methods and full comparisons remain in S1. A prospective 48-task follow-up and refreshed bibliographic verification materially strengthen the evidence. Formal submission readiness is not certified: data/reviewer access, current portal rules and author declarations remain pending, and the methodological novelty remains incremental.')
    build=json.loads((OUT/'compact_build_summary.json').read_text());audit=json.loads((OUT/'revision_evidence_audit.json').read_text())
    d.add_heading('1 Verified changes',1)
    rows=[
      ('Main document',f"{pages} rendered pages; 12-point double-spaced body; {build['abstract_words']}-word abstract; six keywords; five editable equations; two editable tables; two figures."),
      ('Evidence extension','48 later tasks, 186 candidate interventions, 930 action-solver evaluations and 1,440 additional counterfactual policy episodes; original fitted/calibrated screens locked.'),
      ('Audit',f"13 code tests passed; the original 35-condition numerical audit is retained. Revision/manuscript audit: {audit['passed']}/{audit['total']} checks passed."),
      ('References','24 external sources plus one versioned dataset: 22 DOI records matched to Crossref and two official URLs resolved HTTP 200. All 25 entries cited in first-use order.'),
      ('Data citation','An immutable dataset commit and source-archive link are now cited. The private visibility has not been changed without authorization.'),
      ('Integrity','No original findings or endpoints changed. New adverse outcomes, sparse calibration, proxy definitions and solver limitations remain explicit.'),
    ]
    table(d,'Verified revision evidence',['Area','Outcome'],rows,[1.25,5.55])
    d.add_heading('2 Scientific findings and novelty',1)
    d.add_paragraph('The new cohort uses hours 288–360, unseen observed baseline scales 0.95/1.05 and time-varying hidden demand. It follows the protocol committed at 84ebcb31eba0afda32133a7099a33bd2c7883348. It is a prospective computational follow-up, not an independent physical validation or a post hoc reclassification of the primary test set.')
    d.add_paragraph('Follow-up catalogue scenario screening completes 6/24 C-Town and 7/24 Net3 tasks acceptably. Net3 admits two proxy-harmful tasks under both scenario and residual screening. Residual containment is 19/19 assessable C-Town tasks and 20/24 Net3 tasks; the C-Town margin still withholds every action. Both Net3 failures target pipe 20 and violate the added tank-envelope threshold despite zero added service shortage. The paper now explains a specific counterexample, including the forecast, margin, hidden profile and observed severity.')
    d.add_paragraph('The stronger contribution is a reproducible two-cohort diagnosis of recovery, realization, numerical assessability and availability tradeoffs under changing demand. Temporal assurance and conformal calibration are established prior work, cited directly. A new general assurance algorithm, unconditional 90% coverage, field safety, controlled LLM efficacy and human-oversight benefit are not demonstrated. Originality is incremental; a competitive KBS novelty judgment cannot be converted into a defensible percentage or guaranteed by shortening the paper.')
    d.add_heading('3 Journal and reference compliance',1)
    checklist=[
      ('Length and article type','Verified',f'{pages} pages including references, tables and figures; regular-article format retained. A ten-page length alone does not establish Short Communication eligibility.'),
      ('Guide authority','Partially verified','All twenty pages of the supplied official guide dated 23 October 2026 were available and examined. Live ScienceDirect and Elsevier guide requests returned HTTP 403; current portal currency remains unverified.'),
      ('Main text','Verified','Concise introduction, related work, methods, results, discussion/conclusion and declarations. Methods retain exact endpoints, numerical tolerances and locked comparisons.'),
      ('Figures and tables','Verified','Two exact-data figures, separate EPS/PDF artwork and source CSVs; two editable tables. Figure data and every table cell checked against outputs. The main Word document was rendered and inspected page by page.'),
      ('References','Verified within scope','22 selected DOI titles/authors/year/volume/issue/pages checked; two official documentation URLs resolve; a dataset citation points to the retained immutable evidence commit. Bibliographic identity does not certify every source’s methodology.'),
      ('All-Q1 preference','Not met/certified','The closest overlapping work and necessary method/data/software sources remain cited. Quartile metric, category and year qualifications are retained. The supplied journal guide does not require an all-Q1 bibliography.'),
      ('Data deposit and access','Author action pending','Versioned private GitHub deposit and dataset citation prepared. Source archive link supplied for S2. Arrange reviewer access or upload S2; confirm that the publisher accepts this deposit or approve a suitable public archive.'),
      ('Highlights','Prepared','Four editable highlights, each no longer than 85 characters.'),
      ('Funding and interests','Prepared','No-funding and no-competing-interest statements retained from author instructions. The required Elsevier declarations-tool workflow still needs author completion.'),
      ('Author and AI disclosure','Prepared','Corresponding details and previously supplied affiliation retained; CRediT and substantive AI assistance disclosed. Author approval of this new revision remains necessary.'),
      ('Graphical abstract','No mandate verified','No mandate identified in the supplied guide; any live-portal-specific requirement remains unverified.'),
      ('Full-text/retraction/similarity clearance','Limited','No comprehensive commercial similarity test or full-text/retraction-database clearance is claimed. Crossref metadata exposed no withdrawal/retraction notice for selected journal records; the NIST record’s update points to its superseded earlier edition.'),
    ]
    table(d,'Submission checklist',['Item','Status','Evidence or remaining action'],checklist,[1.3,1.15,4.35])
    with (ROOT/'revision_journal_compliance.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['Item','Status','Evidence']);w.writerows(checklist)
    d.add_heading('4 Figure table and citation verification',1)
    d.add_paragraph('Figure 1 has 144 source task records across calibration, primary test and follow-up; only assessable records are plotted. Residual values are independently reconstructed from the action and matched no-action summaries. Figure 2 has 384 task-stage records and uses a mutually exclusive priority order under catalogue selection; every bar retains 24 scheduled tasks. Table 1 reports candidate opportunities, assessability, acceptable outcomes and harm per cohort. Table 2 gives catalogue/learned counts, not rates; its note defines the slash notation. All cells are matched to the recorded outputs.')
    d.add_paragraph('The 25-entry reference report distinguishes 21 journal articles, one NIST document, two software/manual URLs and one generated dataset. Eighteen journal articles come from MDPI, IEEE or Elsevier; three necessary method/data/calibration sources have other publishers. The five removed entries concern general least privilege, general AI-risk management, broad system-safety theory, deep-learning uncertainty and an LLM benchmark that this study does not reproduce. All remaining citations have a stated limited purpose; no accepted-paper content was copied.')
    d.add_heading('5 Remaining blockers and final recommendation',1)
    for text in [
      'SCIENTIFIC POSITIONING: The revised computational failure-analysis claims are supported, but a stronger new-method or safety-guarantee claim would require a substantive mechanism and genuinely independent validation. Two-hour editing and another small simulator cohort cannot provide utility certification or guarantee competitive KBS novelty.',
      'ACCESS AND AUTHOR ACTION: Supply reviewer access or attach the pinned source archive as S2, settle the acceptable repository/public release arrangement, confirm author details and roles, approve the revised findings, and complete the journal’s declarations workflow.',
      'CURRENT POLICY AND REFERENCE PREFERENCE: Recheck live portal requirements. The all-Q1 preference remains unmet and must not be falsely certified; essential nearest prior work and original software/data attribution have been retained.',
    ]:d.add_paragraph(text)
    d.add_paragraph('Final recommendation: MAJOR REVISIONS for a competitive Knowledge-Based Systems submission. The ten-page document and reproducibility evidence are complete for author review. Formal Ready for Submission status remains conditional on unresolved access/author requirements and scientific positioning; no acceptance, novelty percentage or research-accuracy percentage is asserted.')
    d.save(destination)
    highlights=[
      'Recovery-aware screening changes which water-network tasks count as useful work.',
      'Forty-eight locked follow-up tasks test unseen time-varying hidden demand.',
      'Two Net3 proxy-harmful tasks pass both scenario and residual screens.',
      'Global calibration can eliminate availability while missing shifted outcomes.',
    ]
    assert all(len(s)<=85 for s in highlights)
    (ROOT/'revision_highlights.txt').write_text('\n'.join('- '+s for s in highlights)+'\n')
    print('Created revised supplement, audit report, checklist and highlights')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--supplement-source',type=Path,required=True);p.add_argument('--supplement',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--pages',type=int,required=True);p.add_argument('--source-archive');args=p.parse_args()
    supplement(args.supplement_source,args.supplement,args.source_archive);review(args.report,args.pages)
