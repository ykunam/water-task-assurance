"""Build the manuscript and exact-data figures from the audited frozen outputs."""
from pathlib import Path
import argparse
import csv
import html
import json
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from analyze import frame_from_receipts, severity, load_receipts

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"
ART = ROOT / "artwork"
REFERENCES = json.loads((ROOT / "reference_catalog.json").read_text())
ORDER = []
AGENTS = pd.DataFrame(json.loads((OUT / "agent_summary.json").read_text()))
CANDIDATES = pd.read_csv(OUT / "candidate_metrics.csv")
RAW = pd.read_csv(OUT / "candidate_outcomes.csv", dtype={"asset":str})
FIT = json.loads((OUT / "fit_manifest.json").read_text())
NUMERICAL = json.loads((OUT / "numerical_summary.json").read_text())


def citation(keys):
    numbers = []
    for key in keys.split(","):
        if key not in ORDER:
            ORDER.append(key)
        numbers.append(str(ORDER.index(key)+1))
    return "[" + ",".join(numbers) + "]"


def resolve(text):
    return re.sub(r"@\{([a-z0-9_,]+)\}", lambda m:citation(m.group(1)), text)


def reference(key):
    r = REFERENCES[key]
    authors = []
    for a in r.get("author", []):
        family = a.get("family", "")
        given = a.get("given", "")
        authors.append(("".join(x[0]+"." for x in given.split() if x) + " " + family)
                       if family else given or a.get("name", ""))
    if len(authors) > 6:
        authors = authors[:6] + ["et al."]
    year = str(r.get("published", {}).get("date-parts", [[2020 if key == "epanet" else "n.d."]])[0][0])
    journal = html.unescape((r.get("container-title") or [""])[0])
    abbreviations = {"Knowledge-Based Systems":"Knowl.-Based Syst.", "Water Research":"Water Res.",
        "Safety Science":"Saf. Sci.", "Reliability Engineering & System Safety":"Reliab. Eng. Syst. Saf.",
        "Environmental Modelling & Software":"Environ. Modell. Softw.", "Machine Learning":"Mach. Learn.",
        "Information Fusion":"Inf. Fusion", "Pattern Recognition":"Pattern Recognit.",
        "Journal of Water Process Engineering":"J. Water Process Eng.",
        "IEEE Transactions on Automatic Control":"IEEE Trans. Autom. Control",
        "IEEE Transactions on Control Systems Technology":"IEEE Trans. Control Syst. Technol.",
        "IEEE Internet of Things Journal":"IEEE Internet Things J.", "Proceedings of the IEEE":"Proc. IEEE",
        "Machine Learning and Knowledge Extraction":"Mach. Learn. Knowl. Extr.",
        "Foundations and Trends® in Machine Learning":"Found. Trends Mach. Learn.",
        "Journal of Water Resources Planning and Management":"J. Water Resour. Plann. Manage.",
        "Internet of Things":"Internet Things", "Advances in Neural Information Processing Systems":"Adv. Neural Inf. Process. Syst."}
    journal = abbreviations.get(journal, journal)
    volume = r.get("volume", "")
    if r.get("issue"):
        volume += "("+r["issue"]+")"
    pages = r.get("page") or r.get("article-number") or ""
    source = (journal + " " + volume).strip()
    title = html.unescape(r["title"][0])
    tail = f"{source} ({year}) {pages}." if source else year.rstrip(".")+"."
    url = "https://doi.org/" + r["DOI"] if r.get("DOI") else r.get("URL", "")
    accessed = " (accessed 14 November 2026)" if not r.get("DOI") else ""
    return ", ".join(authors)+", "+title+", "+tail+" "+url+accessed+"."


def setup():
    d = Document()
    s = d.sections[0]
    s.page_width, s.page_height = Inches(8.5), Inches(11)
    s.top_margin = s.bottom_margin = Inches(.7)
    s.left_margin = s.right_margin = Inches(.75)
    for style in d.styles:
        if style.type == 1:
            style.font.name = "Times New Roman"
            style.font.color.rgb = RGBColor(0,0,0)
            for border in style.element.xpath(".//w:pBdr"):
                border.getparent().remove(border)
    normal = d.styles["Normal"]
    normal.font.size = Pt(12)
    normal.paragraph_format.line_spacing = 2
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.widow_control = True
    d.styles["Title"].font.size = Pt(18)
    d.styles["Title"].font.bold = True
    d.styles["Title"].paragraph_format.space_after = Pt(10)
    for name in ["Heading 1", "Heading 2"]:
        d.styles[name].font.size = Pt(12)
        d.styles[name].font.bold = True
        d.styles[name].paragraph_format.space_before = Pt(8)
        d.styles[name].paragraph_format.space_after = Pt(2)
        d.styles[name].paragraph_format.keep_with_next = True
    p = s.footer.paragraphs[0]
    p.alignment = 1
    field = OxmlElement("w:fldSimple");field.set(qn("w:instr"), "PAGE");p._p.append(field)
    return d


def table(d, caption, headers, rows, widths):
    p = d.add_paragraph(caption)
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.line_spacing = 1
    for r in p.runs:r.font.size = Pt(10);r.bold = True
    t = d.add_table(rows=1, cols=len(headers))
    t.autofit = False
    for col,width in zip(t.columns,widths):
        col.width=Inches(width)
    for i, h in enumerate(headers):t.rows[0].cells[i].text = str(h)
    for row in rows:
        for c, value in zip(t.add_row().cells, row):c.text = str(value)
    for row_i, row in enumerate(t.rows):
        for c, width in zip(row.cells, widths):
            c.width = Inches(width)
            pr = c._tc.get_or_add_tcPr()
            borders = OxmlElement("w:tcBorders")
            for side in ["top", "bottom", "left", "right"]:
                b = OxmlElement("w:"+side)
                b.set(qn("w:val"), "single" if (row_i == 0 and side in ["top","bottom"]) else "nil")
                b.set(qn("w:sz"), "6");borders.append(b)
            pr.append(borders)
            for p in c.paragraphs:
                p.paragraph_format.line_spacing = 1
                p.paragraph_format.space_after = Pt(3)
                p.paragraph_format.space_before = Pt(2)
                p.paragraph_format.keep_with_next = row_i < len(t.rows)-1
                for r in p.runs:r.font.size = Pt(10);r.bold = row_i == 0
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
    t.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    d.add_paragraph().paragraph_format.line_spacing = 1
    return t


def equation(d, number):
    def run(text):
        r=OxmlElement("m:r");t=OxmlElement("m:t");t.text=text;r.append(t);return r
    def sub(base, index, superscript=None):
        e=OxmlElement("m:sSubSup" if superscript else "m:sSub")
        b=OxmlElement("m:e");b.append(run(base));e.append(b)
        s=OxmlElement("m:sub");s.append(run(index));e.append(s)
        if superscript:
            s=OxmlElement("m:sup");s.append(run(superscript));e.append(s)
        return e
    pieces = {
        1:[sub("U","h"),run("(a) = Δt "),sub("∑","t∈h"),sub("∑","j"),run(" max["),sub("D","jt","+"),run(" − max("),sub("Q","jt"),run("(a), 0), 0].")],
        2:[sub("δu","h"),run("(a) = ["),sub("U","h"),run("(a) − "),sub("U","h"),run("(0)] / "),sub("V","h"),run(";  "),sub("H","h"),run("(a) = 1{"),sub("δu","h"),run(" ≥ 0.01 or "),sub("δe","h"),run(" ≥ 1 h}. ")],
        3:[run("S(a) = max{"),sub("δu","hold"),run("/0.01, "),sub("δe","hold"),run(", "),sub("δu","whole"),run("/0.01, "),sub("δe","whole"),run(", "),sub("δu","last"),run("/0.001, δz/0.05, 0}. ")],
        4:[sub("R","i"),run(" = "),sub("max","a∈Aᵢ"),run(" [Sᵢ(a) − Ŝᵢ(a)]₊;  q = "),sub("R","(⌈0.9(m+1)⌉)"),run(". ")],
        5:[run("Accept(a) = scope(a) ∧ V(a) ∧ C(a) ∧ [Ŝ(a) + q < 1].")],
    }[number]
    p=d.add_paragraph();p.paragraph_format.line_spacing=1.3
    m=OxmlElement("m:oMath")
    if number==3:
        array=OxmlElement("m:eqArr")
        rows=[
            [run("S(a) = max{"),sub("δu","hold"),run("/0.01, "),sub("δe","hold"),run("/(1 h), "),sub("δu","whole"),run("/0.01,")],
            [sub("δe","whole"),run("/(1 h), "),sub("δu","last"),run("/0.001, δz/0.05, 0}. ")],
        ]
        for pieces in rows:
            row=OxmlElement("m:e")
            for x in pieces:row.append(x)
            array.append(row)
        m.append(array)
    else:
        for x in pieces:m.append(x)
    p._p.append(m);p.add_run("    ("+str(number)+")")


def make_figures():
    ART.mkdir(exist_ok=True)
    receipts = load_receipts()
    data,_ = frame_from_receipts(receipts)
    points=[]
    for (net, split, task_id), group in data[data.split != "train"].groupby(["network","split","task_id"]):
        assessable=bool(group.assessable.all()) and all(all("error" not in v for v in x) for x in group.forecasts)
        residual=max(0., max(severity(r.actual)-max(severity(f) for f in r.forecasts)
                            for r in group.itertuples())) if assessable else np.nan
        points.append(dict(network=net,split=split,task_id=task_id,
            outside_grid=bool(group.outside_grid.iloc[0]), assessable=assessable,residual=residual))
    points=pd.DataFrame(points);points.to_csv(ART/"Figure_1_source.csv",index=False)
    plt.rcParams.update({"font.size":10,"font.family":"DejaVu Sans","axes.spines.top":False,"axes.spines.right":False})
    fig,axes=plt.subplots(1,2,figsize=(7.5,3.6),sharey=True)
    for ax,(net,g) in zip(axes,points.groupby("network",sort=True)):
        categories=[("Calibration",g[g.split=="calibration"]),
                    ("Test within grid",g[(g.split=="test")&~g.outside_grid]),
                    ("Test outside grid",g[(g.split=="test")&g.outside_grid])]
        for x,(label,z) in enumerate(categories):
            z=z[z.assessable]
            offset=np.linspace(-.12,.12,len(z)) if len(z) else []
            ax.scatter(x+np.asarray(offset),z.residual,s=22,
                       color=["#64748b","#0072b2","#d55e00"][x],zorder=3)
        q=FIT[net]["residual_margin"]
        if q is not None:ax.axhline(q,color="black",linestyle="--",linewidth=1,label=f"Margin q = {q:.3f}")
        ax.set_title(f"{net}  (q = {q:.3f})");ax.set_xticks(range(3),["Calibration","Within grid","Outside grid"])
        ax.tick_params(axis="x",labelsize=8);ax.set_yscale("symlog",linthresh=.05)
        ax.set_ylim(-.01,None);ax.grid(axis="y",color="#dddddd",linewidth=.6)
    upper=1.35*max(float(points.residual.max()),max(v['residual_margin'] or 0 for v in FIT.values()))
    for ax in axes:ax.set_ylim(-.01,upper)
    axes[0].set_ylabel("Maximum positive task residual")
    fig.tight_layout(pad=.7);save(fig,"Figure_1")
    keep=["Hold RF","Whole RF","Nominal task","Robust task","Residual task"]
    selected=AGENTS[AGENTS.gate.isin(keep)].copy()
    selected.to_csv(ART/"Figure_2_source.csv",index=False)
    fig,axes=plt.subplots(1,2,figsize=(7.5,3.6),sharey=True)
    for ax,net in zip(axes,["C-Town","Net3"]):
        for controller,shift,marker,color in [("catalogue",-.10,"o","#0072b2"),("learned ranking",.10,"s","#d55e00")]:
            g=selected[(selected.network==net)&(selected.controller==controller)].set_index("gate").loc[keep]
            x=np.arange(len(keep))+shift;y=g.acceptable.to_numpy()
            ax.scatter(x,y,marker=marker,s=35,color=color,label=controller,zorder=3)
            for xx,yy in zip(x,y):ax.annotate(str(yy),(xx,yy),xytext=(0,6 if shift<0 else -13),textcoords="offset points",ha="center",fontsize=8)
        ax.set_title(net);ax.set_xticks(range(len(keep)),["Hold\nRF","Whole\nRF","Nominal\ntask","Scenario\ntask","Residual\ntask"])
        ax.set_ylim(-1.5,25.5);ax.set_yticks([0,6,12,18,24]);ax.grid(axis="y",color="#dddddd",linewidth=.6)
    axes[0].set_ylabel("Acceptable completions out of 24 tasks")
    axes[0].legend(loc="upper left",frameon=False,fontsize=8)
    fig.tight_layout(pad=.8);save(fig,"Figure_2")


def save(fig,name):
    fig.savefig(ART/(name+".eps"),format="eps")
    fig.savefig(ART/(name+".pdf"))
    fig.savefig(ART/(name+".png"),dpi=1000)
    fig.savefig(ART/(name+"_preview.png"),dpi=180)
    plt.close(fig)


def image(d,name,caption):
    p=d.add_paragraph();p.paragraph_format.keep_with_next=True;p.paragraph_format.line_spacing=1
    p.add_run().add_picture(str(ART/(name+"_preview.png")),width=Inches(7))
    p=d.add_paragraph(caption);p.paragraph_format.line_spacing=1
    for r in p.runs:r.font.size=Pt(10)


def manuscript(destination):
    make_figures()
    d=setup()
    d.add_paragraph("Taskwise uncertainty screening for water network isolation and recovery","Title")
    d.add_paragraph("Yeshwanth Reddy Kunam")
    d.add_paragraph("Doctor of Business Administration Program, Midwest University, 851 Parr Road, Wentzville, MO 63385, United States")
    d.add_paragraph("Corresponding author: Yeshwanth Reddy Kunam. Email: yeshwanth.kunam@gmail.com")
    d.add_heading("Abstract",1)
    abstract=("Screening a water-network command over its isolation interval can miss consequences during recovery. "
        "We evaluate whole-task screening with explicit numerical assessability, sampled actuator realization and "
        "finite demand scenarios. A secondary taskwise residual margin bounds six normalized consequence coordinates "
        "simultaneously over candidate actions under a stated error-containment condition. A prospective extension "
        "uses native C-Town and Net3 trajectories, 144 chronologically partitioned tasks, 530 candidate actions and "
        "paired hydraulic solvers. Forecasts do not receive the evaluator's future demand factor; half the test tasks "
        "lie outside the forecast grid. Across 48 test tasks, two software controllers are compared under 15 screens. "
        "For catalogue-order selection, three-scenario whole-task screening increases acceptable Net3 completions "
        "from 8 to 13 of 24, while nominal task screening completes 14 acceptably with one recovery failure. "
        "The residual screen completes 12 Net3 tasks acceptably and withholds all C-Town tasks. Its observed "
        "residual containment is 13 of 21 assessable Net3 tasks, so a nominal 90% coverage claim is unsupported. "
        "All 530 paired runs agree on whole-task binary harm, but six disagree on acceptable completion. "
        "The findings identify conditional gains and availability costs rather than universal safety improvement. "
        "The contribution is an auditable benchmark and taskwise discrepancy construction with explicit validity limits.")
    d.add_paragraph(abstract)
    d.add_paragraph("Keywords: water distribution; knowledge-based screening; uncertainty; recovery; operational technology; autonomous controllers")
    sections=[
    ("1 Introduction",[
    "Delegating an operational-technology command requires evidence about its consequences as well as permission to issue it. OT systems couple cybersecurity with process reliability and safety @{nist,humayed}. Least privilege restricts authority @{saltzer}; AI risk management also requires accountable evaluation @{airmf}. Neither condition proves that an authorized isolation will be realized or that service will recover. System-safety analysis therefore motivates evaluating an action within its operating process @{leveson}.",
    "Consider an agent permitted to close one pump. A screen trained on the hold interval may accept it, while subsequent automation leaves storage depleted or fails to restore service. A controller can also request an override that native controls partly supersede. These outcomes should be separated from numerical failures. Treating every completed simulation or denied command as evidence of safety obscures these distinctions.",
    "The major research question is how command screening changes when uncertainty and verification cover the complete isolation-and-recovery task. Two subordinate questions concern the difference between hold and whole-task prediction, and whether a simultaneous discrepancy margin preserves useful work across candidate selection and retries. The contribution is an executable comparison joining prediction, numerical assessability, sampled realization and recovery. A taskwise residual construction provides a conditional implication for adaptively selected actions. It does not introduce temporal safety filtering itself or establish a plant-safety guarantee."]),
    ("2 Related work and contribution boundary",[
    "Water-cybersecurity reviews distinguish cyber detection from process-aware evaluation and emphasize benchmark limitations @{tuptuk,watersurvey,waterreview}. Water SCADA studies analyze deception and hydrodynamic detection @{scada1,scada2}; learned detectors such as Deep H2O address attack identification @{deeph2o}. Hydraulic attack consequences and reliability tradeoffs motivate consequence-based evaluation @{breaking,optimising}. TwinAI studies graph reinforcement learning for water-network management @{twinai}. The present study evaluates the screen independently of the planner and does not reproduce or claim superiority over these detection or learning algorithms.",
    "Predictive safety filters, control-barrier methods and learning-control assurance already constrain proposed actions using predicted behavior @{psf,pcb,fisac}. MARIS-TRA explicitly separates temporal hard-safety conditions from bounded recovery in a different simulated setting @{temporal}. RDFR-CI already composes authority and assurance gates and examines C-Town action consequences @{rdfr}. Our narrower addition is a simultaneous candidate-set discrepancy margin and a native-trajectory water benchmark that tests recovery, actuator realization, numerical indeterminacy and outside-grid demand together. No priority claim is made for combining gates, uncertainty or recovery.",
    "Random forests provide a practical predictive comparator @{breiman}. Score threshold selection differs from probability recalibration @{rfcal}, and uncertainty estimates require validation under the evaluated conditions @{abdar}. Rejection changes both risk exposure and completed work @{rejectviz}. The residual order statistic is motivated by split-conformal calibration @{conformal}; chronological dependence and distribution shift prevent an unconditional coverage interpretation here. Tool-agent benchmarks such as AgentDojo evaluate LLM interactions @{agentdojo}. Our primary controllers are bounded software policies; the earlier shared-context LLM demonstration is excluded from comparative efficacy claims."]),
    ("3 Methods",[]),
    ("3.1 Prospective design and native trajectories",[
    "C-Town is the public BATADAL hydraulic model @{batadal}; Net3 is supplied with EPA's WNTR software @{wntrpaper,wntrsoftware}. EPANET 2.2 supplies the forecast engine @{epanet}. Both use pressure-dependent demand with minimum pressure 0 m, required pressure 15 m and exponent 0.5. Hydraulic, report and rule steps are 300 s. EPANET accuracy is tightened to 10⁻⁶ with 500 trials and STOP on nonconvergence after a training-only mechanics check exposed large residuals under C-Town's source accuracy of 0.01. The numerical validity cutoffs are not relaxed.",
    "Each network has 24 training, 24 calibration and 24 test tasks at integer hours spaced over 72–120, 144–168 and 192–240. Base demand multipliers cycle 0.9, 1 and 1.1. Up to four initially open candidates are selected by rotating a fixed catalogue before observing consequences. C-Town uses PU1–PU11, withholding PU10/PU11 from development; Net3 uses pumps 10/335 and pipes 238/240/241/243/60/20, withholding 60/20. States with fewer active candidates retain that smaller set. All 144 tasks and 530 candidate actions remain in the evidence.",
    "Native model trajectories replace the earlier telemetry-state reconstruction. Complete WNTR solver and control state is paused before task start and copied for continuation; hold and recovery remain continuous. EPANET runs the full native prefix. A full-versus-checkpoint C-Town check differs by less than 6.3×10⁻¹⁰ m in head. Isolation requests last six hours in C-Town and three in Net3, followed by a reopen request and six hours of native automation. A highest-priority close rule requests the hold, but actual sampled status is checked because native control processing may supersede it.",
    "Forecast positive demands change at task start by factors 0.85, 1 or 1.15. The evaluator uses a hidden factor 0.9 or 1.1 in development and half the test tasks; the other half uses 0.75 or 1.25, outside the forecast grid. Negative demands remain injections. Actual outcomes use WNTR's Newton solver; an actual-input EPANET run is retained for every candidate. The engines share equations and model assumptions, so this is algorithmic cross-checking, not independent physical ground truth."]),
    ("3.2 Endpoints and numerical assessability",[
    "For junction j, report t and horizon h, requested positive demand is D⁺ and delivered demand is Q, in m³/s. Positive-demand service shortage uses left-endpoint integration:",
    "@@EQ1",
    "V_h is the matched no-action requested volume. The added tank-envelope duration δe_h counts hours within 0.2 m of minimum or 0.05 m of maximum, relative to the same-solver, same-demand reference:",
    "@@EQ2",
    "Whole-task harm covers hold plus recovery. Acceptable completion additionally requires the requested closed status at every hold report, numerical assessability, last-hour incremental shortage no greater than 0.001, and terminal tank deficit no greater than 5% of operating range relative to reference. These are illustrative research endpoints. Reopening does not prove verified physical maintenance or restoration of every operating variable.",
    "Numerical assessability requires finite complete output, tank-bound error ≤10⁻⁴ m, junction-continuity residual ≤10⁻⁵ m³/s, negative delivered flow at positive-demand nodes ≤10⁻⁷ m³/s, and PDD residual ≤max(10⁻⁵ m³/s, 1% of maximum requested node demand). Both action and reference must pass. Invalid or failed cases remain indeterminate, including in task denominators; they cannot count as acceptable work. Raw negative pressures and continuous metrics are retained separately."]),
    ("3.3 Prediction and taskwise discrepancy screening",[
    "Separate balanced random forests use 300 trees, minimum leaf size five and seed 20261115. There are 33 C-Town and 27 Net3 local state/action features. Hold RF predicts hold harm; Whole RF predicts failure of acceptable completion. Only assessable training rows are fitted. Calibration alone selects a threshold from 0 to 0.50 in steps of 0.01, maximizing acceptable retention subject to at most 5% empirical acceptance of calibration task failures. This is an operating point, not a statistical risk guarantee.",
    "Comparators include scope-only, deny-all, a connectivity/storage-budget heuristic, both forests, calibrated Whole RF, nominal hold/task prediction, three-scenario hold/whole/task prediction, a numerical-check ablation, and a learned-then-scenario screen. Predictive rules see forecasts, not actual-input evaluation outcomes. Scenario task screening requires assessable forecasts, predicted realization, whole-task limits and recovery across all three demand factors. The rule is finite-scenario verification, not robust optimization over a continuous uncertainty set.",
    "The secondary residual screen normalizes six continuous constraints by their declared limits, with δz the maximum terminal tank deficit:",
    "@@EQ3",
    "Ŝ is the maximum predicted severity across forecast scenarios. For every calibration task with all candidate outcomes assessable, take the maximum positive actual-minus-predicted residual over its candidate set. With m eligible tasks:",
    "@@EQ4",
    "If the rank exceeds m, q is infinite and every action is withheld. The residual gate is:",
    "@@EQ5",
    "V and C require every forecast member to be numerically assessable and to realize the sampled hold respectively. A zero-margin joint ablation uses identical six-coordinate predicates. Conditional implication: if actual severity is bounded by Ŝ+q simultaneously for every available candidate, every accepted candidate satisfies the six continuous constraints. The implication survives adaptive candidate selection because its premise holds over the entire candidate set. It does not guarantee actual realization or numerical validity, and chronological dependence, excluded assets and shifted demand invalidate an unqualified 90% coverage claim. Observed containment is measured explicitly."]),
    ("3.4 Controller execution analysis and integrity",[
    "Catalogue-order and Whole-RF-ranked controllers share the candidate set and four-attempt limit. They propose, consume gate denials and retry; selected actions receive evaluator outcomes only after selection. Fifteen screens across 48 test tasks and two controllers yield 1,440 policy episodes over a shared deterministic hydraulic environment. They are not 1,440 independent physical cases. Hold RF, Nominal task and Residual task choices additionally receive 288 fresh attempted rollouts, including abstentions, to verify execution receipts against the cached environment. No independently callable LLM endpoint is claimed.",
    "Descriptive uncertainty uses 2,000 circular moving-block bootstrap replicates over ordered test tasks, block length three. Overlapping trajectories and deterministic demand cycles limit interpretation; no population causal claim or confirmatory p-value follows. A fixed outcome-blind selection of twelve candidates per network is rerun with EPANET at 60 s, using paired references. Primary labels are retained.",
    "The initial protocol was committed before new outcomes; the residual policy and its zero-margin ablation are separately timestamped secondary additions before test analysis. An interrupted run retained 70 records and resumed after checking frozen code and state hashes. After the first aggregates, an all-missing cross-network feature-column bug was corrected and all fits/comparisons rerun; the initial summaries are preserved. No trajectory, endpoint or test scenario was changed to improve results."]),
    ("4 Results",[]),
    ("4.1 Numerical behavior and available task opportunities",[
    "All 144 states complete without a state-level or actual-solver simulation failure. Table 1 distinguishes numerical agreement from task validity. Of 181 test candidates, only 43 are acceptable under all declared task conditions. Acceptable candidates exist in 11/24 C-Town and 16/24 Net3 tasks. Forty-five C-Town and five Net3 test candidates do not realize the requested closed status at every report. Numerical indeterminacy affects eight and three test candidates respectively; these cases remain visible.",
    "@@TABLE1",
    "The paired engines agree on binary whole-task harm in all 530 candidates, yet acceptable completion differs in six C-Town cases. Maximum incremental-shortage disagreement is 0.0000332 in C-Town and 0.001197 in Net3; maximum added-envelope disagreement is 0.25 and 1.0833 tank-hours. The 24-case finer-step sample changes no whole-task harm label. These selected checks do not certify physical pressures, all event timing or all task predicates."]),
    ("4.2 Prediction uncertainty and candidate screening",[
    "The C-Town hold training sample contains no harmful hold labels; Hold RF therefore supplies no effective task screening there. Whole-task fitting recognizes a different target but retains only 2/12 acceptable C-Town test candidates and none of 31 in Net3 at its evaluated threshold. Calibration thresholds are 0.50 and 0.26. Candidate-level results appear in Table 2; the composite calibration target must not be confused with the older manuscript's harmful-command target.",
    "@@TABLE2",
    "The residual margins are 3.7052 from 21 eligible C-Town calibration tasks and 0.3043 from 24 Net3 tasks. The former exceeds the unit decision boundary even when predicted severity is zero, necessarily withholding every action. In test data, residual containment holds in 19/20 assessable C-Town tasks and only 13/21 Net3 tasks. Figure 1 shows the discrepancy distribution. The Net3 result contradicts any nominal 90% test-coverage claim; broad deployment guarantees are not inferred from the order-statistic construction.",
    "@@FIG1"]),
    ("4.3 Agent work and availability tradeoffs",[
    "For catalogue selection, Hold RF accepts every test task and yields 1/24 acceptable C-Town completions and 8/24 in Net3. Learned ranking changes these to 6/24 and 3/24, illustrating planner sensitivity. Nominal task screening yields 6/24 and 14/24 acceptably under either ordering, with three and one recovery failures. Three-scenario task screening yields 2/24 and 13/24; it has two C-Town recovery failures and no Net3 recovery failures. Its selected cases include no numerically indeterminate outcomes.",
    "The residual screen completes 12/24 Net3 tasks acceptably under either ordering and abstains on every C-Town task. Its added conservatism loses one acceptable Net3 completion relative to the zero-margin joint screen. Numerical-validity ablation and zero-margin joint screening give the same binary decisions as scenario task screening in this sample, so an independent incremental benefit of the validity predicate is not demonstrated. Figure 2 presents completed acceptable work, rather than treating denial as success. Detailed goals, harm, abstentions and verification workload are in Supplementary Material S1.",
    "The 288 fresh attempted rollouts include 170 hydraulic action executions and 118 abstentions. Every recorded categorical outcome matches its cached counterpart, with no execution error. This verifies deterministic environment receipts after action selection; it does not create new independent starting states or demonstrate LLM performance.",
    "@@FIG2"]),
    ("5 Discussion",[
    "The central finding is conditional: extending the screening target to recovery changes which actions count as useful work, but additional conservatism does not produce a uniform improvement. Net3 scenario screening avoids the catalogue controller's recovery failures while completing more tasks acceptably. C-Town's larger discrepancy margin collapses availability. The nominal screen can retain more acceptable work while tolerating some recovery failures; selecting an operating point requires explicit risk and availability criteria rather than a single accuracy score.",
    "A taskwise maximum addresses an agent's ability to select among several candidates, but a calibration construction cannot repair unsupported containment assumptions. A three-point demand grid is particularly vulnerable to nonmonotone native-control transitions and outside-grid disturbances. The observed containment failures should motivate new scenarios and improved uncertainty models, not retrospective threshold tuning. The conditional proposition is useful for identifying the precise missing premise; it is not a replacement for process assurance.",
    "Managers should distinguish an authorized request, a realized intervention and verified acceptable task completion. Forecast simulation effort and withheld work create operational costs, but this study does not measure labor savings, financial return, operator effectiveness or treatment safety. A controller that abstains on every task has no demonstrated service benefit. The strongest contribution is the joint evidence trail and failure boundaries, together with a limited residual-screen construction, rather than universal algorithmic superiority."]),
    ("6 Limitations and conclusion",[
    "Both systems are public simulation models without participating-utility calibration. Native initialization removes one reconstruction mechanism but does not make either solver physical ground truth. The test set contains only 24 correlated tasks per network and few harmful whole-task candidates. The finite forecast grid omits many demand trajectories, leaks, equipment faults, sensing errors and water-quality dynamics. Numerical tolerances and recovery thresholds are analyst-selected. Reserved assets provide a limited transfer challenge, not broad unseen-network generalization.",
    "The secondary residual policy and the post-inspection feature correction are disclosed. Earlier shared-context LLM episodes cannot establish controlled LLM efficacy and are excluded from primary comparisons. There is no human-oversight experiment or external human engineering certification. Broader independent scenarios, uncertainty models and utility-relevant endpoints remain necessary before operational deployment.",
    "The benchmark demonstrates why whole-task completion, numerical assessability, realization and uncertainty containment must be reported together. Scenario checking improves some Net3 outcomes, while a taskwise margin can suppress all useful work in C-Town. These findings support a reproducible computational study of screening limits; they do not establish a field-safe autonomous water controller."]),
    ("Data and code availability",[
    "The implementation, frozen protocols, amendments, original-input hashes and executed numerical outputs are maintained in the author's private GitHub repository https://github.com/ykunam/water-task-assurance on branch research/task-horizon-validation. The corresponding author must arrange reviewer access or approve a public archival release and dataset citation before submission. No public data DOI is asserted. Original BATADAL and EPA model sources retain their own attribution and terms. Supplementary Material S1 records additional methods and complete comparison tables; the repository supplies S2 reproducibility material."]),
    ("Funding",["This research did not receive any specific grant from funding agencies in the public, commercial, or not-for-profit sectors."]),
    ("Declaration of competing interests",["The author declares no competing interests."]),
    ("Author contributions",["Yeshwanth Reddy Kunam: Conceptualization, Methodology, Project administration, Writing – review and editing. Software, analysis and drafting received substantial AI assistance. The author must verify the applicable CRediT roles and approve the final work."]),
    ("Declaration of generative AI and AI-assisted technologies in the manuscript preparation process",["ChatGPT Work assisted with code generation, computational analysis, visualization, drafting and language editing. The figures are reproducible plots of executed outputs, not generated depictions of observed physical evidence. The primary planning controllers are software policies; no new controlled LLM benchmark is claimed. Scientific accountability remains with the author, who must verify and approve the final work before submission."]),
    ]
    textlog=[]
    for heading, paragraphs in sections:
        d.add_heading(heading,2 if re.match(r"\d\.\d",heading) else 1)
        textlog.append(heading)
        for text in paragraphs:
            if text.startswith("@@EQ"):
                equation(d,int(text[-1]));continue
            if text=="@@TABLE1":
                rows=[("Native tasks train/calibration/test","24/24/24","24/24/24"),
                    ("Candidate actions across all splits","242","288"),
                    ("Test candidates","85","96"),("Assessable test candidates","77/85","93/96"),
                    ("Whole-task harmful test candidates","6/77","5/93"),
                    ("Acceptable test candidates","12/85","31/96"),
                    ("Unrealized test holds","45/85","5/96"),
                    ("Cross-solver harm label differences","0/242","0/288"),
                    ("Cross-solver acceptable differences","6/242","0/288"),
                    ("60 s sensitivity harm label differences","0/12","0/12")]
                table(d,"Table 1. Experimental opportunities and numerical checks",["Measure","C-Town","Net3"],rows,[3.6,1.6,1.6]);continue
            if text=="@@TABLE2":
                rows=[]
                for net in ["C-Town","Net3"]:
                    for gate in ["Hold RF","Whole RF","Nominal task","Robust task","Residual task"]:
                        r=CANDIDATES[(CANDIDATES.network==net)&(CANDIDATES.gate==gate)&(CANDIDATES.stratum=="all")].iloc[0]
                        rows.append((net,gate,f"{r.harmful_accepted}/{r.harmful}",
                            f"{r.acceptable_retained}/{r.acceptable}",f"{r.indeterminate_accepted}/{r.indeterminate}"))
                table(d,"Table 2. Test candidate screening with all endpoint classes retained",
                    ["Network","Screen","Harmful accepted","Acceptable retained","Indeterminate accepted"],rows,[.8,1.65,1.4,1.5,1.45]);continue
            if text=="@@FIG1":
                image(d,"Figure_1","Fig. 1. Taskwise positive severity residuals in calibration and test. Dashed lines show the calibration margin. Only assessable tasks are plotted; four C-Town and three Net3 test tasks are indeterminate. The residual axis is linear near zero and logarithmic above 0.05. A finite margin does not establish test coverage under this chronological shifted design. Programmatic plot from executed outputs using AI-assisted code; no generative image model was used.");continue
            if text=="@@FIG2":
                image(d,"Figure_2","Fig. 2. Acceptable completions for both software controllers under selected screens. Every point has 24 scheduled tasks; denied, unrealized and indeterminate cases do not count as acceptable. The same task pool is reused across screens. Scenario task denotes the three-scenario task screen. Programmatic plot from executed outputs using AI-assisted code; no generative image model was used.");continue
            text=resolve(text)
            p=d.add_paragraph()
            for part in re.split(r"(V_h|δe_h)",text):
                if part in ("V_h","δe_h"):
                    base,index=part.split("_");p.add_run(base);p.add_run(index).font.subscript=True
                else:p.add_run(part)
            textlog.append(text)
    d.add_heading("References",1)
    assert len(ORDER)==len(REFERENCES)==29,(len(ORDER),set(REFERENCES)-set(ORDER))
    for i,key in enumerate(ORDER,1):
        p=d.add_paragraph(f"[{i}] "+reference(key));p.paragraph_format.line_spacing=1.2
        p.paragraph_format.space_after=Pt(4)
        for r in p.runs:r.font.size=Pt(10.5)
    d.save(destination)
    (ROOT/"citation_order.json").write_text(json.dumps(ORDER,indent=2))
    (ROOT/"manuscript_text.md").write_text("\n\n".join(textlog))
    print(json.dumps(dict(manuscript=str(destination),abstract_words=len(abstract.split()),
        body_words=len(" ".join(textlog).split()),references=len(ORDER),figures=len(d.inline_shapes),tables=len(d.tables))))


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--out",type=Path,required=True)
    manuscript(parser.parse_args().out)
