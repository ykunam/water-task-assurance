"""Ten-page revision using exact frozen and prospectively extended evidence."""
from pathlib import Path
import argparse
import csv
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from docx.shared import Inches,Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import build_paper as b
from analyze import load_receipts,frame_from_receipts,severity

ROOT=b.ROOT;OUT=b.OUT;ART=ROOT/'revision_artwork'
ART.mkdir(exist_ok=True)
EXCLUDE={'saltzer','airmf','leveson','agentdojo','abdar'}
TITLE='Recovery-aware command screening in water networks under demand shift'


def load_followup():
    import gzip
    return json.loads(gzip.decompress((OUT/'followup_receipts.json.gz').read_bytes()))


def save(fig,name):
    for suffix in ['eps','pdf']:fig.savefig(ART/f'{name}.{suffix}',format=suffix)
    fig.savefig(ART/f'{name}.png',dpi=1000)
    fig.savefig(ART/f'{name}_preview.png',dpi=180);plt.close(fig)


def figures():
    primary,_=frame_from_receipts(load_receipts());new,_=frame_from_receipts(load_followup())
    rows=[]
    for cohort,data in [('Primary',primary[primary.split!='train']),('Follow-up',new)]:
        for (net,task_id),g in data.groupby(['network','task_id']):
            ok=bool(g.assessable.all()) and all(all('error' not in x for x in r.forecasts) for r in g.itertuples())
            residual=max([0.]+[severity(r.actual)-max(map(severity,r.forecasts)) for r in g.itertuples()]) if ok else np.nan
            category='Calibration' if g.split.iloc[0]=='calibration' else ('Follow-up' if cohort=='Follow-up' else 'Primary test')
            rows.append(dict(network=net,task_id=task_id,cohort=cohort,category=category,assessable=ok,residual=residual))
    points=pd.DataFrame(rows);points.to_csv(ART/'Figure_1_source.csv',index=False)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(7.5,3.1),sharey=True)
    for ax,net in zip(axes,['C-Town','Net3']):
        for i,category in enumerate(['Calibration','Primary test','Follow-up']):
            z=points[(points.network==net)&(points.category==category)&points.assessable]
            ax.scatter(i+np.linspace(-.14,.14,len(z)),z.residual,s=19,color=['#64748b','#0072b2','#d55e00'][i],zorder=3)
        q=b.FIT[net]['residual_margin'];ax.axhline(q,color='black',linestyle='--',linewidth=1)
        ax.set_title(f'{net} (q={q:.3f})');ax.set_xticks(range(3),['Calibration','Primary\ntest','Follow-up'])
        ax.tick_params(axis='x',labelsize=8);ax.set_yscale('symlog',linthresh=.05)
        ax.grid(axis='y',color='#dddddd',linewidth=.6)
    upper=1.3*max(float(points.residual.max()),max(x['residual_margin'] for x in b.FIT.values()))
    for ax in axes:ax.set_ylim(-.01,upper)
    axes[0].set_ylabel('Positive task residual');fig.tight_layout(pad=.8);save(fig,'Figure_1')
    old=pd.read_csv(OUT/'agent_episodes.csv');old['cohort']='Primary'
    fresh=pd.read_csv(OUT/'followup_agent_episodes.csv');fresh['cohort']='Follow-up'
    episodes=pd.concat([old,fresh],ignore_index=True)
    gates=['Hold RF','Nominal task','Robust task','Residual task']
    labels=['Acceptable','Recovery failure','Unrealized','Harm','Indeterminate','Abstained']
    colors=['#009e73','#e69f00','#56b4e9','#d55e00','#cc79a7','#d2d2d2']
    rows=[]
    for r in episodes[(episodes.controller=='catalogue')&episodes.gate.isin(gates)].itertuples():
        stage=('Abstained' if r.abstained else 'Indeterminate' if r.indeterminate else
               'Harm' if r.harmful else 'Unrealized' if not r.completed else
               'Recovery failure' if r.recovery_failure else 'Acceptable')
        if stage=='Acceptable':assert r.acceptable
        rows.append(dict(network=r.network,cohort=r.cohort,gate=r.gate,task_id=r.task_id,stage=stage))
    stages=pd.DataFrame(rows);stages.to_csv(ART/'Figure_2_source.csv',index=False)
    fig,axes=plt.subplots(1,2,figsize=(7.5,3.1),sharey=True)
    for ax,net in zip(axes,['C-Town','Net3']):
        for ci,cohort in enumerate(['Primary','Follow-up']):
            bottom=np.zeros(4);x=np.arange(4)+(ci-.5)*.35
            for stage,color in zip(labels,colors):
                heights=np.array([len(stages[(stages.network==net)&(stages.cohort==cohort)&(stages.gate==gate)&(stages.stage==stage)]) for gate in gates])
                ax.bar(x,heights,width=.32,bottom=bottom,color=color,label=stage if ci==0 else None,
                    edgecolor='white',linewidth=.25,hatch='///' if ci else None)
                bottom+=heights
            assert (bottom==24).all()
        ax.set_title(net);ax.set_xticks(range(4),['Hold\nRF','Nominal\ntask','Scenario\ntask','Residual\ntask'])
        ax.set_yticks([0,6,12,18,24]);ax.set_ylim(0,25);ax.tick_params(axis='x',labelsize=8)
    axes[0].set_ylabel('Scheduled tasks');fig.legend(*axes[0].get_legend_handles_labels(),ncol=3,
        loc='upper center',bbox_to_anchor=(.5,1.03),frameon=False,fontsize=8)
    fig.tight_layout(rect=(0,0,1,.90),pad=.8);save(fig,'Figure_2')


def add_paragraph(d,text):
    text=b.resolve(text);d.add_paragraph(text);return text


def picture(d,name,caption):
    p=d.add_paragraph();p.paragraph_format.line_spacing=1;p.paragraph_format.keep_with_next=True
    p.add_run().add_picture(str(ART/f'{name}_preview.png'),width=Inches(6.8))
    p=d.add_paragraph(caption);p.paragraph_format.line_spacing=1
    for r in p.runs:r.font.size=Pt(10)


def build(destination):
    figures();b.ORDER.clear();d=b.setup();text=[]
    d.add_paragraph(TITLE,'Title')
    for value in ['Yeshwanth Reddy Kunam','Doctor of Business Administration Program, Midwest University, 851 Parr Road, Wentzville, MO 63385, United States','Correspondence: yeshwanth.kunam@gmail.com']:
        p=d.add_paragraph(value);p.paragraph_format.line_spacing=1;p.paragraph_format.space_after=Pt(3)
    fs=json.loads((OUT/'followup_summary.json').read_text())
    new=pd.DataFrame(json.loads((OUT/'followup_agent_summary.json').read_text()))
    def val(net,gate,key='acceptable',controller='catalogue'):
        return int(new[(new.network==net)&(new.gate==gate)&(new.controller==controller)].iloc[0][key])
    def count(net,key):return next(x[key] for x in fs['networks'] if x['network']==net)
    def containment(net):
        x=fs['containment'][net];return f"{x['contained']}/{x['assessable']}"
    abstract=('Command screening confined to isolation can miss failures during recovery. We compare knowledge-based screens over complete isolation-and-recovery tasks in two water-network simulators. '
        'The primary study contains 144 chronological tasks, 530 candidate interventions and 1,440 paired software-controller episodes. A separately pre-specified follow-up uses 48 later tasks, new baseline scales and time-varying hidden demand, with all fitted screens and thresholds locked. '
        'In primary Net3 tasks, three-scenario screening increases acceptable catalogue-controller completions from 8/24 to 13/24; adding a taskwise residual margin yields 12/24 and withholds all C-Town work. '
        f"Follow-up scenario screening completes {val('C-Town','Robust task')}/24 and {val('Net3','Robust task')}/24 tasks acceptably, respectively. "
        f"Follow-up residual containment is {containment('C-Town')} and {containment('Net3')} assessable tasks; two Net3 proxy-harmful tasks pass both scenario and residual screens. "
        'The evidence supports a reproducible diagnosis of screening limits and availability costs. It does not establish unconditional uncertainty coverage or physical safety.')
    d.add_heading('Abstract',1);d.add_paragraph(abstract)
    d.add_paragraph('Keywords: water distribution; command screening; recovery; uncertainty; operational technology; decision support')
    sections=[
      ('1 Introduction',[
       'Water operational technology couples cyber authority to hydraulic consequences @{nist,humayed}. Reviews of water cyberattacks and detection identify substantial benchmark and process-model limitations @{tuptuk,watersurvey,waterreview}. An authorized pump-closure request may be superseded by native controls, or may complete isolation while leaving storage depleted. A useful screen must therefore distinguish permission, sampled realization, numerical assessability and recovery.',
       'We ask how screening changes when evaluation covers the complete isolation-and-recovery task under demand shift. The contribution is a reproducible comparison with matched candidate and retry budgets, explicit indeterminate outcomes, and a taskwise discrepancy analysis. A later, prospectively locked validation tests the original screens under new operating conditions. The study evaluates failure boundaries; it does not introduce temporal safety filtering itself.'
      ]),
      ('2 Related work',[
       'Water-SCADA models study stealthy deception and hydrodynamic detection @{scada1,scada2}; Deep H2O addresses learned attack detection @{deeph2o}. Hydraulic attack consequences, reliability tradeoffs and digital-twin control motivate process-aware evaluation @{breaking,optimising,twinai}. We evaluate command screening, without claiming superiority over these detection or control algorithms.',
       'Predictive safety filters, control-barrier methods and learning-control assurance already constrain proposed actions @{psf,pcb,fisac}. MARIS-TRA separates temporal hard safety and recovery @{temporal}; RDFR-CI composes authority/assurance gates and examines C-Town consequences @{rdfr}. Our narrower addition is an auditable joint assessment of realization, numerical validity, recovery and candidate-set discrepancy under hidden demand. Random forests are a practical comparator @{breiman}; threshold choice differs from probability recalibration @{rfcal}. Rejection changes completed work @{rejectviz}, while conformal calibration requires coverage assumptions that this chronological shifted design does not establish @{conformal}.'
      ]),
      ('3 Methods',[]),
      ('3.1 Networks and locked evaluations',[
       'C-Town uses the BATADAL hydraulic model @{batadal}; Net3 is supplied with WNTR 1.4.0 @{wntrpaper,wntrsoftware}. EPANET 2.2 provides forecasts @{epanet}; WNTR provides evaluator outcomes, with actual-input EPANET cross-checks. Both share hydraulic equations. Pressure-dependent demand uses minimum/required pressure 0/15 m and exponent 0.5; hydraulic, report and rule steps are 300 s. EPANET accuracy is 10⁻⁶, with 500 trials and STOP on nonconvergence.',
       'Per network, the primary design has 24 training, 24 calibration and 24 test tasks over hours 72–120, 144–168 and 192–240. Baseline scales cycle 0.9/1/1.1. Up to four initially active candidates rotate from a fixed catalogue; PU10/PU11 in C-Town and pipes 60/20 in Net3 are withheld from development. Complete native solver/control states are continued, with six-hour C-Town or three-hour Net3 isolation and six-hour recovery. Forecast factors are 0.85/1/1.15; evaluator factors differ, with half the primary test tasks outside that grid.',
       'The follow-up fixes 24 tasks per network over hours 288–360, scales 0.95/1.05 and three hidden Uniform(0.70,1.30) factors across isolation halves and recovery. Its code and schedule were committed before outcomes. Original training/calibration data, gates and thresholds remain locked. Supplementary Material S1 gives assets, profiles, numerical checks and the disclosed post-inspection feature correction.'
      ]),
      ('3.2 Endpoints and screens',[
       'For positive requested demand D⁺ and delivered demand Q, both in m³/s, service shortage over horizon h is integrated at left endpoints:',
       '@@EQ1',
       'Let Vₕ be matched no-action requested volume and δeₕ the added tank-envelope duration in hours, using the same solver/demand reference. Envelope proximity is 0.2 m from minimum or 0.05 m from maximum:',
       '@@EQ2',
       'Hₕ is a research proxy, not a regulatory safety criterion. Acceptable completion additionally requires closed status at every isolation report, numerical assessability, last-hour added shortage ≤0.001 and terminal tank deficit δz≤0.05 of operating range. Invalid outputs remain indeterminate and cannot count as acceptable.',
       'Assessability requires finite, complete action/reference outputs, tank-bound error ≤10⁻⁴ m, junction-continuity residual ≤10⁻⁵ m³/s, negative delivered flow at positive-demand nodes ≤10⁻⁷ m³/s, and pressure-dependent-demand residual ≤max(10⁻⁵ m³/s, 1% of maximum requested node demand). Numerical status is separate from proxy harm. Raw negative pressures, residuals and continuous effects remain in S2.',
       'Hold RF predicts isolation harm; Whole RF predicts failure of acceptable completion. Separate network fits use 300 balanced trees, minimum leaf five, seed 20261115 and 33/27 pre-command state/action features. Only numerically assessable development rows are fitted/calibrated. Uncalibrated cutoffs are 0.50. Calibration searches 0–0.50 in steps of 0.01, maximizing acceptable retention while accepting ≤5% of calibration failures; its cutoffs are 0.50/0.26. Table 2 reports uncalibrated Whole RF; S1 includes both. Nominal-task screening uses factor 1 alone. Scenario-task screening requires all three forecasts to be numerically assessable, to realize isolation, and to satisfy whole-task/recovery limits.',
       'A secondary margin uses six normalized consequence coordinates:',
       '@@EQ3',
       'With worst-scenario severity Ŝ, calibration residuals maximize discrepancy over each task’s candidate set Aᵢ. For m eligible calibration tasks:',
       '@@EQ4',
       'If the rank exceeds m, q is infinite. With V/C denoting forecast validity/realization, the residual screen is:',
       '@@EQ5',
       'Conditionally, S(a)≤Ŝ(a)+q simultaneously over all candidates implies that any accepted adaptive choice satisfies the six continuous constraints. This does not certify actual realization or physical safety. Since Ŝ≥0, q≥1 necessarily withholds every action. Coverage is measured rather than assumed.'
      ]),
      ('3.3 Controllers and integrity',[
       'Catalogue-order and learned-ranking controllers share four attempts and receive evaluator outcomes after selection. Fifteen gates yield 1,440 primary and 1,440 follow-up counterfactual policy episodes over shared task pools. The primary study additionally executes 288 fresh attempted rollouts: 170 actions and 118 abstentions. No new controlled LLM or human-oversight result is claimed. Protocol timestamps, all failures, matched references, corrections and descriptive block-bootstrap comparisons are retained in S1/S2.'
      ]),
      ('4 Results',[
       '@@TABLE1',
       f"All 530 primary solver pairs agree on binary whole-task harm, but six C-Town acceptable-completion labels differ. A fixed 24-case EPANET 60 s check changes neither label. The follow-up adds {fs['candidates']} candidate interventions; Table 1 retains opportunities and indeterminacy separately from execution success.",
       '@@TABLE2',
       'Primary scenario screening yields 2/24 acceptable C-Town and 13/24 Net3 completions under either controller. Nominal screening yields 6/24 and 14/24, with three and one recovery failures. The residual margins are 3.7052 and 0.3043; the former necessarily suppresses all C-Town work. Primary containment is 19/20 and 13/21 assessable tasks.',
       f"In the follow-up, scenario screening yields {val('C-Town','Robust task')}/24 and {val('Net3','Robust task')}/24 acceptable catalogue completions, with {val('C-Town','Robust task','harmful')} and {val('Net3','Robust task','harmful')} harmful outcomes. Residual containment is {containment('C-Town')} and {containment('Net3')}; neither cohort establishes an unconditional 90% guarantee. Figure 1 shows discrepancies; Figure 2 separates availability from failure stages. Full controller comparisons and numerical ablations are in S1.",
       'A traceable counterexample occurs at Net3 hour 319 for pipe 20 and scale 0.95. Hidden factors are 0.952, 1.298 and 1.020. Worst forecast severity is 0.500; adding q=0.304 permits the action. Actual severity is 1.500, driven by 1.5 added tank-envelope hours with zero added service shortage. The second failure at hour 326 also concerns pipe 20 and exceeds the envelope criterion. These are violations of the declared proxy, not demonstrated utility damage. Both are numerically assessable and pass both controller orderings.',
       '@@FIG1','@@FIG2'
      ]),
      ('5 Discussion and conclusion',[
       'Recovery-aware screening changes which actions count as useful work. Finite-scenario screening improves some primary Net3 outcomes, while a global residual margin can eliminate availability. The later shifted validation tests persistence of these limits without retuning. Managers should track acceptable completions alongside harm, indeterminacy, abstention and simulation effort; this study does not measure labor savings or financial return.',
       'Both networks are public simulation models; operating tasks overlap and both solvers share equations. Small harmful samples, analyst-selected thresholds, limited demand profiles and incomplete actuator realization restrict generalization. The contribution is a reproducible computational diagnosis and conditional discrepancy construction. Utility validation, richer disturbances and stronger coverage evidence remain necessary for deployment.'
      ]),
      ('Data and code availability',[
       'Derived data and code are deposited in the versioned GitHub dataset @{studydata}. Supplementary Material S1 gives methods and full comparisons; S2 is the pinned source-and-data archive. Repository access is currently restricted.'
      ]),
      ('Funding and competing interests',[
       'This research did not receive any specific grant from funding agencies in the public, commercial, or not-for-profit sectors. The author declares no competing interests.'
      ]),
      ('Author contributions',[
       'Yeshwanth Reddy Kunam: Conceptualization, Methodology, Project administration, Writing – review and editing.'
      ]),
      ('Declaration of generative AI and AI-assisted technologies in the manuscript preparation process',[
       'ChatGPT Work assisted with software, analysis, reproducible plots, drafting and language editing. No generative image model produced experimental evidence. Scientific accountability and approval of the final work remain with the author.'
      ]),
    ]
    for heading,paragraphs in sections:
        d.add_heading(heading,2 if heading.startswith('3.') else 1);text.append(heading)
        for value in paragraphs:
            if value.startswith('@@EQ'):b.equation(d,int(value[-1]));continue
            if value=='@@TABLE1':
                rows=[]
                for net in ['C-Town','Net3']:
                    p=b.RAW[(b.RAW.network==net)&(b.RAW.split=='test')]
                    rows.append((net,'Primary',24,len(p),int(p.assessable.sum()),int(p.acceptable.sum()),int((p.assessable&p.whole_harm).sum())))
                    rows.append((net,'Follow-up',24,count(net,'candidates'),count(net,'assessable'),count(net,'acceptable'),count(net,'harmful')))
                b.table(d,'Table 1. Test opportunities and numerically assessable outcomes',
                    ['Network','Cohort','Tasks','Candidates','Assessable','Acceptable','Harmful'],rows,[.8,.9,.5,.9,.95,.95,.8]);continue
            if value=='@@TABLE2':
                rows=[]
                for net in ['C-Town','Net3']:
                    for gate in ['Hold RF','Whole RF','Nominal task','Robust task','Residual task']:
                        values=[]
                        for frame in [b.AGENTS,new]:
                            vals=[]
                            for controller in ['catalogue','learned ranking']:
                                r=frame[(frame.network==net)&(frame.gate==gate)&(frame.controller==controller)].iloc[0]
                                vals.append((int(r.acceptable),int(r.harmful)))
                            values.extend([f'{vals[0][0]}/{vals[1][0]}',f'{vals[0][1]}/{vals[1][1]}'])
                        rows.append((net,'Scenario task' if gate=='Robust task' else gate,*values))
                b.table(d,'Table 2. Acceptable completions and harmful outcomes by controller',
                    ['Network','Screen','Primary acceptable','Primary harm','Follow-up acceptable','Follow-up harm'],rows,[.75,1.35,1.2,1.05,1.3,1.15])
                p=d.add_paragraph('Cells report catalogue/learned counts, each out of 24 scheduled tasks. Harm includes only numerically assessable outcomes. Scenario task is labeled Robust task in code; all indeterminate outcomes remain in task denominators.');p.paragraph_format.line_spacing=1
                for r in p.runs:r.font.size=Pt(10)
                continue
            if value=='@@FIG1':
                picture(d,'Figure_1','Fig. 1. Taskwise residuals among assessable calibration, primary-test and follow-up tasks. Dashed lines are locked calibration margins. The axis is linear near zero and logarithmic above 0.05. Programmatic plot from recorded outputs using AI-assisted code.');continue
            if value=='@@FIG2':
                picture(d,'Figure_2','Fig. 2. Mutually exclusive outcome stages under catalogue selection. Each screen pairs primary (plain) and follow-up (hatched) bars, with 24 scheduled tasks each. Priority is abstention, indeterminacy, harm, unrealized isolation, recovery failure, then acceptable completion. Programmatic plot from recorded outputs using AI-assisted code.');continue
            text.append(add_paragraph(d,value))
    assert len(b.ORDER)==25 and not set(b.ORDER)&EXCLUDE,(len(b.ORDER),set(b.ORDER))
    d.add_heading('References',1)
    for i,key in enumerate(b.ORDER,1):
        if key=='studydata':
            dataset=json.loads((ROOT/'revision_dataset.json').read_text())
            value=f"[dataset] Y.R. Kunam, {dataset['title']}, GitHub, version {dataset['version']}, 2026. {dataset['url']} (accessed 15 November 2026)."
        else:value=b.reference(key).replace('accessed 14 November 2026','accessed 15 November 2026')
        p=d.add_paragraph(f'[{i}] '+value);p.paragraph_format.line_spacing=2;p.paragraph_format.space_after=Pt(3)
        for r in p.runs:r.font.size=Pt(10.5)
    d.save(destination)
    (ROOT/'revision_reference_order.json').write_text(json.dumps(b.ORDER,indent=2))
    (ROOT/'revision_manuscript_text.md').write_text('\n\n'.join(text))
    (OUT/'compact_build_summary.json').write_text(json.dumps(dict(abstract_words=len(abstract.split()),body_words=len(' '.join(text).split()),references=len(b.ORDER),tables=len(d.tables),figures=len(d.inline_shapes)),indent=2))
    print((OUT/'compact_build_summary.json').read_text())


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args();build(args.out)
