"""Build an editable Knowledge-Based Systems methodology revision."""
from pathlib import Path
import argparse
import csv
import json
import math
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from docx.shared import Inches,Pt
from docx import Document
from docx.oxml import OxmlElement
import build_paper as b
from admissibility_audit import forecast_summary,task_score
from analyze import load_receipts,frame_from_receipts,severity

ROOT=b.ROOT;OUT=b.OUT;ART=ROOT/'methodology_artwork';ART.mkdir(exist_ok=True)
TITLE='Calibration support and recovery-aware command screening in water networks'
AI=('ChatGPT Work assisted with research design, software, numerical analysis, literature verification, plots and manuscript drafting. The author is responsible for substantive review, interpretation and the final content. The figures are programmatic plots of recorded simulations; no generative image model produced experimental evidence.')


def para(d,text):
    value=b.resolve(text);d.add_paragraph(value);return value


def equation(d,text,number):
    p=d.add_paragraph();p.paragraph_format.line_spacing=1.15
    m=OxmlElement('m:oMath');r=OxmlElement('m:r');t=OxmlElement('m:t');t.text=text;r.append(t);m.append(r);p._p.append(m);p.add_run(f'    ({number})')


def save(fig,name):
    for ext in ['eps','pdf']:fig.savefig(ART/f'{name}.{ext}')
    fig.savefig(ART/f'{name}_preview.png',dpi=220);plt.close(fig)


def figures():
    cal=json.loads((OUT/'ssrn_calibration.json').read_text());primary,_=frame_from_receipts(load_receipts());rows=[]
    for net,g in primary[primary.split=='calibration'].groupby('network'):
        for tid,t in g.groupby('task_id',sort=True):
            valid=t.assessable.all() and all(all('error' not in e for e in r.forecasts) for r in t.itertuples())
            score=max([0.]+[severity(r.actual)-max(map(severity,r.forecasts)) for r in t.itertuples()]) if valid else np.nan
            eligible=next(r for r in cal[net]['marginal']['scores'] if r['task_id']==tid)
            rows.append(dict(network=net,task_id=tid,original_assessable=bool(valid),original_score=score,eligible_score=eligible['score'],eligible_candidates=eligible['eligible']))
    points=pd.DataFrame(rows);points.to_csv(ART/'Figure_1_source.csv',index=False)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(7.2,3.25),sharey=True)
    for ax,net in zip(axes,['C-Town','Net3']):
        g=points[points.network==net].reset_index(drop=True);x=np.arange(1,25)
        ax.scatter(x-.12,g.original_score,s=24,label='Original all-candidate score',color='#64748b')
        ax.scatter(x+.12,g.eligible_score,s=28,marker='x',label='Eligible-set score',color='#0072b2')
        ax.axhline(b.FIT[net]['residual_margin'],color='black',ls='--',lw=1,label='Original margin')
        ax.set_title(f"{net}: eligible tasks {int((g.eligible_candidates>0).sum())}/24")
        ax.set_xlabel('Calibration task');ax.set_xticks([1,6,12,18,24]);ax.set_yscale('symlog',linthresh=.01);ax.grid(axis='y',color='#dddddd',lw=.6)
    axes[0].set_ylabel('Positive task residual');fig.legend(*axes[0].get_legend_handles_labels(),loc='upper center',bbox_to_anchor=(.5,1.04),ncol=3,frameon=False,fontsize=8)
    fig.tight_layout(rect=(0,0,1,.9));save(fig,'Figure_1')
    ep=pd.read_csv(OUT/'ssrn_agent_episodes.csv');gates=['Scenario task','Original residual','Eligible marginal','Eligible conditional'];rows=[]
    for r in ep[(ep.cohort=='Prospective')&ep.gate.isin(gates)].itertuples():
        stage='Abstained' if r.abstained else 'Indeterminate' if r.indeterminate else 'Harm' if r.harmful else 'Unrealized' if not r.completed else 'Recovery failure' if r.recovery_failure else 'Acceptable'
        if stage=='Acceptable':assert r.acceptable
        rows.append(dict(network=r.network,gate=r.gate,controller=r.controller,task_id=r.task_id,stage=stage))
    stages=pd.DataFrame(rows);stages.to_csv(ART/'Figure_2_source.csv',index=False)
    labels=['Acceptable','Recovery failure','Unrealized','Harm','Indeterminate','Abstained'];colors=['#009e73','#e69f00','#56b4e9','#d55e00','#cc79a7','#d2d2d2']
    fig,axes=plt.subplots(1,2,figsize=(7.2,3.4),sharey=True)
    for ax,net in zip(axes,['C-Town','Net3']):
        for ci,controller in enumerate(['catalogue','learned ranking']):
            bottom=np.zeros(4);x=np.arange(4)+(ci-.5)*.35
            for label,color in zip(labels,colors):
                heights=np.array([len(stages[(stages.network==net)&(stages.controller==controller)&(stages.gate==gate)&(stages.stage==label)]) for gate in gates])
                ax.bar(x,heights,width=.32,bottom=bottom,color=color,edgecolor='white',linewidth=.25,hatch='///' if ci else None,label=label if ci==0 else None);bottom+=heights
            assert (bottom==24).all()
        ax.set_title(net);ax.set_xticks(range(4),['Scenario','Original\nresidual','Eligible\nmarginal','Eligible\nconditional']);ax.tick_params(axis='x',labelsize=8);ax.set_yticks([0,6,12,18,24]);ax.set_ylim(0,25)
    axes[0].set_ylabel('Scheduled prospective tasks');fig.legend(*axes[0].get_legend_handles_labels(),loc='upper center',bbox_to_anchor=(.5,1.03),ncol=3,frameon=False,fontsize=8)
    fig.tight_layout(rect=(0,0,1,.9));save(fig,'Figure_2')


def picture(d,name,caption):
    p=d.add_paragraph();p.paragraph_format.line_spacing=1;p.paragraph_format.keep_with_next=True;p.add_run().add_picture(str(ART/f'{name}_preview.png'),width=Inches(6.8))
    p=d.add_paragraph(caption);p.paragraph_format.line_spacing=1.1;p.paragraph_format.keep_together=True
    for r in p.runs:r.font.size=Pt(10)


def build(destination,regenerate_artwork=True):
    if regenerate_artwork:figures()
    b.ORDER.clear();d=b.setup();d.styles['Normal'].paragraph_format.line_spacing=2
    d.styles['Normal'].paragraph_format.space_after=Pt(0)
    d.add_paragraph(TITLE,'Title')
    p=d.add_paragraph('Yeshwanth Reddy Kunam');p.add_run('a').font.superscript=True;p.paragraph_format.line_spacing=1;p.paragraph_format.space_after=Pt(3)
    p=d.add_paragraph();p.add_run('a').font.superscript=True;p.add_run('Doctor of Business Administration Program, Midwest University, 851 Parr Road, Wentzville, MO 63385, United States');p.paragraph_format.line_spacing=1;p.paragraph_format.space_after=Pt(3)
    p=d.add_paragraph('Corresponding author: yeshwanth.kunam@gmail.com');p.paragraph_format.line_spacing=1;p.paragraph_format.space_after=Pt(3)
    summary=json.loads((OUT/'ssrn_summary.json').read_text());agents=pd.DataFrame(summary['agent_summary'])
    def result(net,gate,field='acceptable',controller='catalogue'):
        r=agents[(agents.network==net)&(agents.cohort=='Prospective')&(agents.gate==gate)&(agents.controller==controller)].iloc[0];return int(r[field])
    abstract=('A conservative command screen can discard useful water-network interventions while lacking calibration support when action is possible. We develop an executable audit for knowledge-based screening that connects forecast eligibility, sampled actuation, numerical validity and calibration support. Using established conformal set-inclusion principles, it retains invalid actual trajectories as infinite losses and separates marginal from opportunity-conditional calibration. '
        'In C-Town and Net3, both original margins are set by actions already excluded by forecast rules. The calibration sets contain four and seven eligible tasks; eligibility-aware marginal calibration yields zero margins, whereas the conditional version yields infinite margins at a nominal 90% level. '
        'Following two previously inspected cohorts, a frozen third cohort tests 48 later tasks with unseen scales and time-varying hidden demand. '
        f"Marginal screening produces {result('C-Town','Eligible marginal')}/24 and {result('Net3','Eligible marginal')}/24 acceptable catalogue completions, with {result('C-Town','Eligible marginal','harmful')} and {result('Net3','Eligible marginal','harmful')} proxy-harmful outcomes. "
        'Conditional screening abstains throughout. The findings expose calibration scarcity and availability costs; the shifted chronological design establishes neither exchangeability nor unconditional uncertainty coverage or physical safety.')
    d.add_heading('Abstract',1);d.add_paragraph(abstract)
    d.add_paragraph('Keywords: water distribution; calibration; selective prediction; recovery; operational technology; decision support')
    d.add_heading('1 Introduction',1)
    para(d,'Water operational technology couples cyber authority to hydraulic consequences @{nist,humayed}. Security reviews identify process-model limitations @{tuptuk,watersurvey,waterreview}. We study knowledge-based decision support: symbolic rules define admissible actions and calibration constrains learned or catalogue ranking. The research question is whether recovery-aware screening has calibration support precisely when it can admit an action.')
    d.add_heading('2 Related work and contribution',1)
    para(d,'Water-SCADA studies examine stealthy deception and hydrodynamic detection @{scada1,scada2}; Deep H2O addresses learned attack detection @{deeph2o}. Hydraulic attack consequences, cyber reliability and digital-twin management motivate process-aware evaluation @{breaking,optimising,twinai}. These algorithms address different tasks; this study does not claim superiority over them.')
    para(d,'Predictive safety filters, control-barrier methods and learning-control assurance already constrain actions @{psf,pcb,fisac}. MARIS-TRA treats temporal safety and recovery @{temporal}; RDFR-CI examines authority gates and C-Town consequences @{rdfr}. Random forests (RF) provide a practical ranking comparator @{breiman}; threshold selection differs from probability recalibration @{rfcal}, and rejection changes completed work @{rejectviz}.')
    para(d,'Conformal calibration provides finite-sample statements under assumptions @{conformal}; DISC calibrates decision-set inclusion @{disc}. Building on these principles, our contribution is an executable water-task audit linking forecast eligibility, numerical indeterminacy, sampled actuation and calibration support, tested on an untouched third cohort.')
    d.add_heading('3 Methods',1)
    para(d,'C-Town uses the BATADAL hydraulic model @{batadal}; Net3 is supplied with the Water Network Tool for Resilience (WNTR) 1.4.0 @{wntrpaper,wntrsoftware}. EPANET 2.2 supplies forecasts @{epanet}; actual WNTR outcomes have actual-input EPANET cross-checks. The solvers share hydraulic equations. Pressure-dependent demand uses minimum/required pressure 0/15 m and exponent 0.5. Hydraulic, report and rule steps are 300 s; EPANET accuracy is 10⁻⁶, with 500 trials and STOP on nonconvergence.')
    para(d,'The primary study contains 144 tasks and 530 candidate interventions: 24 training, calibration and test tasks per network over hours 72–120, 144–168 and 192–240, with scales 0.9/1/1.1. A first 48-task follow-up uses hours 288–360, scales 0.95/1.05 and hidden factors in [0.70,1.30]. Both are retrospective for this audit; only the third is prospective. S1 preserves full methods and amendments.')
    d.add_heading('3.1 Endpoints and numerical status',2)
    para(d,'Full native solver/control states are continued. Up to four initially active candidates rotate from a fixed catalogue; PU10/PU11 in C-Town and pipes 60/20 in Net3 remain outside development. Isolation lasts six hours in C-Town or three in Net3, followed by six-hour recovery. Forecast demand factors are 0.85/1/1.15. Positive requested demand D⁺ and delivered demand Q, both in m³/s, yield left-endpoint integrated shortage in Eq. (1), with Δt=300 s:')
    b.equation(d,1)
    para(d,'For matched no-action requested volume Vₕ, δuₕ=[Uₕ(a)−Uₕ(0)]/Vₕ. Added tank-envelope duration δeₕ is in hours. Envelope proximity is 0.2 m from minimum or 0.05 m from maximum. The declared proxy is harmful if whole-task δu≥0.01 or δe≥1 h. Acceptable completion additionally requires closed status at every isolation report, numerical assessability, last-hour δu≤0.001 and terminal tank deficit δz≤0.05 of operating range.')
    para(d,'Numerical checks require finite complete outputs, tank-bound error ≤10⁻⁴ m, continuity residual ≤10⁻⁵ m³/s, negative delivered flow at positive-demand nodes ≤10⁻⁷ m³/s and pressure-dependent-demand residual ≤max(10⁻⁵ m³/s, 1% of maximum requested node demand). Invalid cases remain indeterminate in outcome reporting. Severity in Eq. (2) combines six normalized coordinates:')
    b.equation(d,3)
    d.paragraphs[-1].runs[-1].text='    (2)'
    para(d,'Numerical validity and proxy harm are separate. This severity is a research endpoint, not a regulatory or plant-safety certificate. The original margin maximizes positive actual-minus-predicted severity over every candidate on fully assessable calibration tasks. It excludes three C-Town calibration tasks; that exclusion is retained and disclosed for the historical comparator.')
    d.add_heading('3.2 Locked learned comparators',2)
    para(d,'Network-specific forests use 300 balanced trees, minimum leaf five, seed 20261115 and 33/27 pre-command features. Only assessable development rows are fitted/calibrated. Hold RF predicts isolation harm with cutoff 0.5; learned ranking uses the fixed whole-task model. Original residual margins are 3.7052/0.3043. No model, endpoint or historical margin is refitted using the third cohort.')
    para(d,'Nominal task requires the factor-1 forecast to be numerically assessable, fully realized, non-harmful over the whole task and free of recovery failure. Scenario task requires these predicates under all three forecasts. Original residual instead applies the full six-coordinate severity bound with its historical margin. The joint severity additionally constrains hold consequences. Both eligible-set variants use that same joint forecast eligibility and differ in the calibration population. Thus predicate changes and calibration changes remain distinct.')
    d.add_heading('3.3 Admissibility and calibration support audit',2)
    para(d,'Let Ŝᵢ(a) be maximum forecast severity. Bᵢ contains actions whose three forecasts are numerically assessable, fully sampled-realized and have severity strictly below one. Set Lᵢ(a)=Sᵢ(a) when actual hydraulics are assessable and closure is fully realized; otherwise Lᵢ(a)=∞. Equation (3) assigns score zero to empty Bᵢ:')
    equation(d,'Rᵢᴮ = max({0} ∪ {[Lᵢ(a) − Ŝᵢ(a)]₊ : a ∈ Bᵢ}).',3)
    para(d,'The all-task marginal version retains all 24 scheduled calibration tasks. The opportunity-conditional version uses only calibration tasks satisfying the label-blind event Eᵢ={Bᵢ≠∅}. It does not discard invalid eligible outcomes: their infinite losses remain. Equation (4) sets the margin for m scores; Eq. (5) defines accepted actions:')
    equation(d,'k = ⌈(m + 1)(1 − α)⌉;  q = Rᴮ₍ₖ₎ if k ≤ m, else ∞.',4)
    equation(d,'Dᵢ(q) = {a ∈ Bᵢ : Ŝᵢ(a) + q < 1},    α = 0.10.',5)
    para(d,'The procedure first computes the forecast-eligible set, then the frozen margin, then permits catalogue or fixed learned ranking within Dᵢ(q). At most four candidate proposals are tried, stopping at the first allowed action. No actual outcome enters a permission decision. The same candidate pool and budgets apply to every gate.')
    d.add_heading('3.4 Conditional implications and evidence limit',2)
    para(d,'Proposition 1. If Rᵢᴮ≤q<∞, every action in Dᵢ(q) is numerically assessable, fully sampled-realized and has Sᵢ(a)<1. Proof: membership gives Lᵢ(a)≤Ŝᵢ(a)+Rᵢᴮ≤Ŝᵢ(a)+q<1; an infinite loss is impossible. This simultaneous implication survives any ranking or retry sequence within the fixed candidate set. It does not cover a changed state or a new candidate.')
    para(d,'With fixed predictors/base gate and exchangeable calibration/test task scores, the standard conformal rank argument supplies a marginal 1−α bound for this containment event. Conditioning on a nonempty eligible set requires the opportunity score sample to be exchangeable with the next opportunity task. Proposition 2. A finite empirical rank at α=0.10 requires m≥9: ⌈0.9(m+1)⌉≤m implies m≥9. Infinite observed scores can still make q infinite above that minimum. These are applications of established calibration principles, not new distribution-free control theory. Chronological demand shift here does not establish either exchangeability assumption.')
    d.add_heading('3.5 Programming and evaluation protocol',2)
    para(d,'The Python implementation separates hydraulic generation, score calibration, permission decisions, controller ranking and outcome analysis. Gate inputs contain only forecasts, fixed margins and permitted pre-command features. Hidden evaluator profiles and actual outcomes are withheld from ranking and permission decisions. Per-network feature selection excludes all-missing columns from the other network; the prior post-inspection feature correction is disclosed in S1. Input hashes, frozen task definitions, numerical receipts, amendments and package versions are retained for reproducibility.')
    para(d,'The implemented audit follows four steps. First, construct forecast-eligible candidate sets on the original calibration tasks and compute Eq. (3), preserving empty sets and infinite losses. Second, select all tasks or only opportunity tasks and freeze Eq. (4), together with support counts and hashes. Third, compute Eq. (5) on each test task and apply catalogue order or the locked forest ranking with four proposal attempts, stopping at the first allowed action. Finally, evaluate selected outcomes against matched no-action references and retain abstention, indeterminacy and adverse outcomes. No observed test outcome changes the frozen gate.')
    para(d,'The unit of evidence is a scheduled task, not a policy episode or candidate row. Both controllers and all gates share candidate pools. Counts use 24 scheduled tasks per network and cohort, including unsuccessful or indeterminate tasks. Full retrospective comparisons and descriptive block-bootstrap intervals are in S1. A fixed 24-candidate EPANET check at 60 s supplies a primary-cohort step-size sensitivity analysis; no equivalent finer-step experiment is claimed for the new cohort.')
    d.add_heading('4 Prospective validation and results',1)
    para(d,'Before generating new outcomes, code, calibration scores and all 48 task definitions were committed. The third cohort uses hours 384–456, observed scales 0.925/1.075 and three hidden Uniform(0.65,1.35) factors across the first isolation half, second half and recovery, seed 2026111503. Changes occur on native pattern slots. Forecasts remain the original constant factors. Six gates and two controllers yield 576 counterfactual policy episodes over shared task pools. The study does not add controlled LLM or human trials.')
    rows=[]
    for r in summary['calibration']:
        rows.append((r['network'],24,r['eligible_tasks'],r['eligible_candidates'],f"{r['original_margin']:.4f}",'0','∞'))
    b.table(d,'Table 1. Calibration support and frozen margins',['Network','Tasks','Eligible tasks','Eligible actions','Original q','Marginal q','Conditional q'],rows,[.75,.5,.85,.9,.9,.9,1.0])
    para(d,'Table 1 contrasts calibration support and margins. Original q uses 21/24 fully assessable C-Town tasks and 24/24 Net3 tasks. New marginal q uses all 24 tasks per network; conditional q uses only 4/7 opportunity tasks. Comparing margins without matching score definitions and denominators cannot establish dominance.')
    para(d,'Earlier results explain why the prospective audit is necessary. In primary Net3 tasks, scenario screening yields 13/24 acceptable catalogue completions versus 8/24 for Hold RF; the original residual gate yields 12/24. In the first follow-up, scenario screening yields 6/24 acceptable C-Town and 7/24 Net3 completions, admitting two proxy-harmful Net3 tasks. The original residual gate admits both Net3 failures and withholds all C-Town work. These cohorts motivate the new analysis and are not reclassified as independent prospective tests of the revised audit.')
    rows=[]
    for net in ['C-Town','Net3']:
        for gate in ['Hold RF','Nominal task','Scenario task','Original residual','Eligible marginal','Eligible conditional']:
            vals=[f"{result(net,gate,key)}/{result(net,gate,key,'learned ranking')}" for key in ['acceptable','harmful','indeterminate','abstained']]
            rows.append((net,gate,*vals))
    b.table(d,'Table 2. Prospective outcomes for catalogue and learned ranking',['Network','Gate','Acceptable C/L','Harm C/L','Indet. C/L','Abstained C/L'],rows,[.7,1.7,1.15,.9,.95,1.1])
    p=d.add_paragraph('C/L reports counts for catalogue/learned ranking, each out of 24 scheduled tasks. Indeterminate outcomes remain in denominators. Harm is reported only for assessable outputs; these columns are not mutually exclusive stages.');p.paragraph_format.line_spacing=1.05
    for r in p.runs:r.font.size=Pt(10)
    d.add_heading('4.1 Calibration attribution and availability',2)
    picture(d,'Figure_1','Fig. 1. Original all-candidate and new eligible-set calibration scores. Plotted tasks 1–24 correspond to ID suffixes 00–23. Invalid original task scores are omitted as in the historical procedure; new eligible scores retain all 24 tasks. Dashed lines show original margins. The vertical scale is linear near zero and logarithmic above 0.01. Exact programmatic plot from saved outputs using AI-assisted code.')
    para(d,'Figure 1 traces both original margin-defining witnesses to forecast-ineligible actions. C-Town_calibration_10 targets PU7: two forecasts realize closure only 0.458 and 0.014 of sampled times, despite worst predicted severity 0.946. Net3_calibration_22 targets pipe 240 with worst predicted severity 1.785. Their residuals set the original margins. Eligibility-aware marginal calibration yields zero margins here, while opportunity-conditional calibration yields abstention. Those rules coincide with the existing zero-margin joint and deny-all behaviors; the contribution is exposing their different evidence contracts and tracing the calibration mechanism, not relabeling a controller improvement.')
    para(d,'Only four C-Town and 27 Net3 candidate actions occur in eligible calibration sets, spread over four and seven tasks. Numerous empty sets can make all-task coverage appear strong while leaving sparse support for interventions. An all-task marginal guarantee does not imply the same conditional probability among tasks where a command can be accepted. The sample-support test makes this distinction visible before deployment.')
    para(d,'The prospective zero-margin residual is contained on 21/24 C-Town and 18/24 Net3 tasks overall, but only 2/5 and 5/11 tasks with eligible actions. Empty eligible sets contribute zero scores to the all-task denominator. This measured gap exposes the distinction between the calibration targets. Containment bounds every eligible candidate and differs from selected-action acceptability; a positive residual need not make the selected action unacceptable.')
    d.add_heading('4.2 Prospective outcomes and interpretation',2)
    picture(d,'Figure_2','Fig. 2. Prospective outcome stages for catalogue (plain) and learned ranking (hatched). Each bar retains 24 tasks. Priority is abstention, indeterminacy, harm, unrealized isolation, recovery failure, then acceptable completion. Exact programmatic plot from saved outputs using AI-assisted code.')
    para(d,f"Figure 2 separates prospective outcome stages. The fresh cohort contains {summary['candidates']} candidate interventions and {summary['action_solver_evaluations']} action-solver evaluations. Eligible marginal screening gives {result('C-Town','Eligible marginal')}/24 and {result('Net3','Eligible marginal')}/24 acceptable catalogue completions, with {result('C-Town','Eligible marginal','harmful')} and {result('Net3','Eligible marginal','harmful')} proxy-harmful outcomes. Opportunity-conditional screening abstains on all 48 tasks. Table 2 retains ordering effects and numerical indeterminacy rather than excluding unsuccessful tasks.")
    opportunities=json.loads((OUT/'methodology_opportunity_summary.json').read_text())
    ceilings={r['network']:r['feasible_tasks'] for r in opportunities if r['cohort']=='Prospective'}
    para(d,f"An actually acceptable candidate exists in {ceilings['C-Town']}/24 C-Town and {ceilings['Net3']}/24 Net3 prospective task pools. These are finite-pool opportunity ceilings, not deployable oracles. The distinction prevents attributing every incomplete task to screening and shows how much useful work is withheld even when an acceptable intervention exists. The audit uses no oracle outcome in its permission decisions.")
    para(d,f"Paired solvers disagree on {summary['cross_solver_harm_disagreements']} binary whole-task harm labels and {summary['cross_solver_acceptable_disagreements']} acceptable-completion labels in this new cohort. Their shared equations limit the independence of this cross-check. Neither a zero count nor a vacuous gate establishes field safety. Empirical counts are descriptive: trajectories overlap, task pools are reused and no population-level significance or causal effect is claimed.")
    para(d,'For managers, the relevant distinction is between completed work and evidence supporting the decision to intervene. The audit reports eligible calibration tasks, excluded or invalid trajectories, calibration target and abstention alongside outcome counts. Financial return, labor savings and human-oversight benefit were not measured.')
    d.add_heading('5 Discussion and conclusion',1)
    para(d,'The audit scores forecast-eligible actions, preserves invalid hydraulics and failed realization as infinite losses, and distinguishes marginal from opportunity-conditional calibration. Its simultaneous containment implication and support test expose where a knowledge-based screening rule lacks evidence. A frozen third cohort separates validation from the outcomes motivating the design.')
    para(d,'The general set-inclusion and conformal arguments are prior work. The finite calibration support is too small to make the conditional version useful, while the marginal version can coincide with an existing unbuffered gate. The novel empirical contribution is an auditable analysis of that tradeoff for complete isolation-and-recovery tasks across two native water models and three chronological test cohorts. More expressive disturbances, additional eligible calibration tasks, external utility expertise and independent physical validation remain necessary for operational conclusions.')
    d.add_heading('Data and code availability',1)
    para(d,'Code and derived evidence are versioned in the study repository @{studydata}. Repository visibility is currently restricted. Supplementary Material S1 supplies full implementation, prior results and proofs. This study concerns simulations and does not report live utility interventions.')
    d.add_heading('Funding and competing interests',1)
    d.add_paragraph('This research received no specific grant from funding agencies in the public, commercial or not-for-profit sectors. The author declares no competing interests.')
    d.add_heading('CRediT authorship contribution statement',1)
    d.add_paragraph('Yeshwanth Reddy Kunam: Conceptualization, Methodology, Project administration, Writing – review and editing.')
    d.add_heading('Declaration of generative AI and AI-assisted technologies in the manuscript preparation process',1)
    d.add_paragraph(AI)
    d.add_heading('References',1)
    assert len(b.ORDER)==26,(len(b.ORDER),b.ORDER)
    for i,key in enumerate(b.ORDER,1):
        if key=='disc':value='Y. Bao, Y. Min, H. Ren, C. Zou, Conformalized Safe Feasible Sets in Uncertain Decision Systems, arXiv:2609.24496v1 (2026), preprint, not peer reviewed. https://doi.org/10.48550/arXiv.2609.24496.'
        elif key=='studydata':
            dataset=json.loads((ROOT/'methodology_dataset.json').read_text());value=f"[dataset] Y.R. Kunam, Water command screening results for C-Town and Net3, GitHub, version 2026-11-15. {dataset['url']}."
        else:value=b.reference(key).replace('accessed 14 November 2026','accessed 15 November 2026')
        p=d.add_paragraph(f'[{i}] '+value);p.paragraph_format.line_spacing=2;p.paragraph_format.space_after=Pt(3)
        for r in p.runs:r.font.size=Pt(10.5)
    d.core_properties.title=TITLE
    d.core_properties.author='Yeshwanth Reddy Kunam'
    d.core_properties.subject='Knowledge-Based Systems research manuscript on calibration support and recovery-aware command screening'
    d.core_properties.keywords='water distribution; calibration; selective prediction; recovery; operational technology; decision support'
    destination.parent.mkdir(exist_ok=True,parents=True);d.save(destination)
    (ROOT/'methodology_reference_order.json').write_text(json.dumps(b.ORDER,indent=2)+'\n')
    (OUT/'methodology_build_summary.json').write_text(json.dumps(dict(title=TITLE,abstract=abstract,abstract_words=len(abstract.split()),references=26,tables=len(d.tables),figures=len(d.inline_shapes),equations=len(d._element.xpath('.//m:oMath'))),indent=2)+'\n')
    (OUT/'journal_submission_abstract.txt').write_text(abstract+'\n')
    source_rows={r['key']:r for r in csv.DictReader((ROOT/'revision_reference_verification.csv').open())}
    fields=list(next(iter(source_rows.values())))
    with (ROOT/'methodology_reference_verification.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for number,key in enumerate(b.ORDER,1):
            if key=='disc':
                row=dict.fromkeys(fields,'')
                row.update(number=number,key=key,title='Conformalized Safe Feasible Sets in Uncertain Decision Systems',journal='arXiv preprint, not peer reviewed',doi='10.48550/arXiv.2609.24496',url='https://arxiv.org/abs/2609.24496v1',metadata='Title/authors/version/submission date and assigned preprint DOI verified at official arXiv record 15 November 2026',citation_purpose='Established general conformal safe-set inclusion principle; not claimed as our novelty',content_review='Official abstract and relevant full-text sections reviewed; not a full independent methodological audit',quartile_status='Not applicable',ranking_basis='Preprint; no journal quartile',ranking_url='https://arxiv.org/abs/2609.24496v1',access_date='2026-11-15')
            else:
                row=dict(source_rows[key]);row['number']=number
                if key=='studydata':row.update(url=json.loads((ROOT/'methodology_dataset.json').read_text())['url'],title='Water command screening results for C-Town and Net3',metadata='Immutable evidence commit retained in the study GitHub repository')
            writer.writerow(row)
    print((OUT/'methodology_build_summary.json').read_text())


def supplement(source,destination,archive_url):
    d=Document(source)
    d.paragraphs[1].text=('Supplementary Material S1 for '+TITLE+'. Sections S1–S8 retain the primary and first follow-up evidence; Sections S9–S10 document the new admissibility audit and prospectively frozen third cohort. The first two cohorts are retrospective for the new method.')
    for p in d.paragraphs:
        if p.text.startswith('Data are pinned at '):
            p.text='The original data are pinned at https://github.com/ykunam/water-task-assurance/tree/49f0d2a6516885ec281a4a83e93ed63787b6c869. Third-cohort provenance and source are documented in S9.'
    d.add_page_break();d.add_heading('S9 Audit derivation and prospective provenance',1)
    d.add_paragraph('The admissibility audit scores the fixed forecast-eligible action set. It is not DISC itself and does not claim the general conformal set-inclusion idea as new. A candidate whose actual hydraulics are invalid or whose closure is not fully realized receives infinite loss. Empty eligible sets receive task score zero. All scheduled calibration tasks are kept in the marginal analysis, including tasks with invalid candidates outside the eligible set. The opportunity analysis conditions only on forecast eligibility, without looking at actual outcomes to select tasks.')
    d.add_paragraph('Containment proof. For any a in the accepted set, the positive-part residual definition implies L(a)−Ŝ(a)≤Rᴮ, including negative residuals. On Rᴮ≤q<∞, L(a)≤Ŝ(a)+q<1. Thus the actual loss is finite, hydraulics and sampled realization are valid, and each normalized consequence coordinate is below one. Because the inequality holds for all base-eligible candidates simultaneously, changing their order cannot invalidate the implication. It applies only to the recorded initial task and finite action set, not a sequence of plant states after intervention.')
    d.add_paragraph('Statistical qualification. With a predictor and eligibility rule fixed independently of calibration labels, exchangeable task scores give the usual rank bound P(Rnew≤q)≥1−α; ties make the bound conservative. Conditioning on the event of a nonempty eligible set instead requires exchangeability of the selected opportunity tasks with the next such task. These are assumptions for a generic rank argument, not findings about chronological shifted simulator tasks. All-task marginal coverage cannot be relabeled as coverage conditional on accepted commands.')
    d.add_paragraph('Support proof. For a finite calibration order statistic at α, ceil((m+1)(1−α))≤m is equivalent to m≥(1−α)/α. At α=0.10, at least nine opportunity tasks are necessary. The four C-Town and seven Net3 opportunity tasks therefore yield infinite conditional margins without inspecting their labels. Nine tasks are not sufficient for a finite margin if the required order statistic is itself infinite. Empty tasks contribute no opportunity information even though their zero scores contribute to marginal calibration.')
    d.add_paragraph('Chronology. The method, calibration scores, all 48 new states and protocol were frozen before new outcomes at commit 8d6c41cd81e97dcd110f191522eced3c17ccff65. The new cohort uses hours 384–456, scales 0.925/1.075 and Uniform(0.65,1.35) hidden factors, seed 2026111503. It preserves original development data, thresholds, native controls, endpoints and numerical tolerances. The initial two cohorts had already been examined and are explicitly retrospective for this extension.')
    dataset=json.loads((ROOT/'methodology_dataset.json').read_text())
    d.add_paragraph('Versioned third-cohort evidence: '+dataset['url']+'. Pinned source archive: '+archive_url+'. Repository visibility is restricted.')
    result=json.loads((OUT/'ssrn_summary.json').read_text());a=pd.DataFrame(result['agent_summary'])
    for number,net in enumerate(['C-Town','Net3'],8):
        d.add_page_break();d.add_heading(f'S10.{number-7} Complete new-audit comparisons for '+net,1)
        rows=[]
        for cohort in ['Primary','Follow-up','Prospective']:
            for gate in ['Hold RF','Nominal task','Scenario task','Original residual','Eligible marginal','Eligible conditional']:
                g=a[(a.network==net)&(a.cohort==cohort)&(a.gate==gate)].set_index('controller')
                vals=[f"{int(g.loc['catalogue',key])}/{int(g.loc['learned ranking',key])}" for key in ['acceptable','harmful','indeterminate','recovery_failure','abstained']]
                rows.append((cohort,gate,*vals))
        b.table(d,f'Table S{number}. '+net+' outcomes for new-audit comparisons',['Cohort','Gate','Acceptable C/L','Harm C/L','Indet. C/L','Recovery failure C/L','Abstained C/L'],rows,[.8,1.7,.9,.7,.7,1.0,1.0])
        d.add_paragraph('Each C/L count is catalogue/learned ranking out of 24 scheduled tasks. Only the Prospective rows provide untouched test evidence for the new audit. The other rows are descriptive retrospective comparisons. Indeterminacy is distinct from harm; outcome columns may overlap. Figure 2 instead uses mutually exclusive stages. These policies share action pools and do not constitute independent samples.')
    d.add_page_break();d.add_heading('S11 Margin-defining witness audit',1)
    witnesses=json.loads((OUT/'ssrn_calibration_witnesses.json').read_text());rows=[]
    for r in witnesses:
        w=r['witness'];rows.append((r['network'],w['task_id'].rsplit('_',1)[1],w['asset'],f"{w['predicted_severity']:.6f}",f"{w['actual_severity']:.6f}",f"{w['residual']:.6f}",'No'))
    b.table(d,'Table S10. Original order-statistic witnesses',['Network','Cal task','Asset','Predicted S','Actual S','Residual','Eligible'],rows,[.8,.7,.65,1.1,1.1,1.1,.7])
    d.add_paragraph('The original C-Town margin is the twentieth order statistic of 21 task scores; its PU7 witness is ineligible because two forecast scenarios do not fully realize the requested isolation. Their realized fractions are 0.458333 and 0.013889, while the low-demand member realizes isolation fully. All three forecasts are numerically assessable. Maximum predicted severity is 0.946226 and actual severity is 4.651382. The residual is 3.705156. An action whose forecast actuation already fails cannot enter the base-eligible set even before adding a margin.')
    d.add_paragraph('The Net3 margin is the twenty-third order statistic of 24 task scores. The pipe-240 witness is ineligible because two forecast severities exceed one: 1.785475 and 1.365632; the third is 0.908500. All three forecasts are numerically assessable and fully realize isolation. Actual severity is 2.089775, yielding residual 0.304300. This case fails the consequence predicate rather than sampled realization.')
    d.add_paragraph('These witnesses are calibration-set mechanism diagnoses. They do not show that removing ineligible actions preserves conditional coverage among future interventions, nor do they justify replacing the chronology with an exchangeable sample. Actual failures in the prospective cohort remain failures. The independently reconstructed witness file, complete score manifest and native simulator receipts are retained in the source archive.')
    d.core_properties.title='Supplementary methods and evidence for '+TITLE
    d.core_properties.author='Yeshwanth Reddy Kunam'
    d.save(destination)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--supplement-source',type=Path);p.add_argument('--supplement',type=Path);p.add_argument('--archive-url');p.add_argument('--reuse-artwork',action='store_true');args=p.parse_args();build(args.out,regenerate_artwork=not args.reuse_artwork)
    if args.supplement:supplement(args.supplement_source,args.supplement,args.archive_url)
