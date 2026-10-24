"""Build the IEEE-style conference paper (.docx) from results.json.
    python make_figures.py ../results/results.json && python build_paper.py ../results/results.json
Every number in the text/tables is read from the JSON, so re-running on the real Cleveland data updates the paper."""
import json, sys, os, re
import numpy as np
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

HERE = os.path.dirname(os.path.abspath(__file__)); FIG = os.path.join(HERE, "figs")
R = json.load(open(sys.argv[1])); OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "TrustFed_Health_IEEE_Paper.docx")
S, SET, REAL = R["summary"], R["setup"], R["dataset"] == "cleveland"
FED, FEDS, SMPC, EXT = "FedAvg (non-IID)", "FedAvg (IID)", "FedAvg + SMPC", "FedAvg (extended training)"
TE = lambda s: f"TEFL (sigma={s:g})"
MID = TE(2.0)
A = R["audits"]; HEB = R["he_benchmark_seconds"]; rec = R["records"]

# ───────────── derived numbers ─────────────
f1 = lambda x: f"{x:.1f}"; f3 = lambda x: f"{x:.3f}"; pc = lambda x: f"{100*x:.1f}"
def ms(m, k, pct=True):
    v = S[m][k]; return f"{100*v['mean']:.1f} ± {100*v['std']:.1f}" if pct else f"{v['mean']:.3f} ± {v['std']:.3f}"
def pair(m1, m2, key):
    a = {(r["rep"], r["fold"]): r[key] for r in rec if r["method"] == m1}
    b = {(r["rep"], r["fold"]): r[key] for r in rec if r["method"] == m2}
    d = np.array([a[k] - b[k] for k in a]); bs = [np.random.default_rng(i).choice(d, len(d)).mean() for i in range(2000)]
    return d.mean(), np.percentile(bs, [2.5, 97.5])
smpc_gap = max(abs(a["acc"] - b["acc"]) for a in rec for b in rec if a["method"] == FED and b["method"] == SMPC and a["rep"] == b["rep"] and a["fold"] == b["fold"])
d_mia = {s: pair(FED, TE(s), "mia_auc") for s in SET["sigmas"]}
d_acc = {s: pair(FED, TE(s), "acc") for s in SET["sigmas"]}
d_loc = pair(FED, "Local-only (mean of sites)", "acc")
d_iid = pair(FEDS, FED, "acc")
eps = {s: S[TE(s)]["epsilon"]["mean"] for s in SET["sigmas"]}
n_runs = SET["folds"] * SET["reps"]
hs = SET["hospital_sizes_mean"]

z = lambda v: f"{(0.0 if abs(v) < 0.05 else v):+.1f}"
sub_n = min(r['n'] for r in A[FED]['subgroups']); sub_r = next(r for r in A[FED]['subgroups'] if r['n'] == sub_n)
half = 100 * 1.96 * (sub_r['accuracy'] * (1 - sub_r['accuracy']) / sub_n) ** 0.5
del_ = [100 * (b_['accuracy'] - a_['accuracy']) for a_, b_ in zip(sorted(A[FED]['subgroups'], key=lambda r: (r['attribute'], r['subgroup'])), sorted(A[MID]['subgroups'], key=lambda r: (r['attribute'], r['subgroup'])))]
# ───────────── references (numbered in order of first citation) ─────────────
REFS = {
 "rieke": 'N. Rieke et al., "The future of digital health with federated learning," npj Digit. Med., vol. 3, art. 119, 2020.',
 "mcmahan": 'B. McMahan, E. Moore, D. Ramage, S. Hampson, and B. A. y Arcas, "Communication-efficient learning of deep networks from decentralized data," in Proc. AISTATS, 2017, pp. 1273–1282.',
 "singh": 'J. P. Singh et al., "Privacy-aware hierarchical federated learning in healthcare: Integrating DP and SMPC," Future Internet, 2025.',
 "jain": 'A. Jain and S. Bhullar, "AI-driven wearable health devices with health-aware control and secure prognostics," Array, 2025.',
 "abu": 'O. AbuAlghanam et al., "A novel key distribution for mobile patient authentication inspired by federated learning," Sensors, 2025.',
 "tightiz": 'L. Tightiz et al., "XG-FedAIT: XGBoost-based federated adaptive interpolation transfer learning for post-TAVR outcome prediction," Blockchain: Res. Appl., 2025.',
 "ikegwu": 'A. Ikegwu et al., "Advancing federated learning frameworks for privacy-preserving cyber threat detection in healthcare systems," Int. J. Comput. Intell. Syst., 2026.',
 "murala": 'D. K. Murala et al., "MedLedgerFL: A hybrid blockchain–federated learning framework for secure remote healthcare services," Sci. Rep., 2026.',
 "abadi": 'M. Abadi et al., "Deep learning with differential privacy," in Proc. ACM CCS, 2016, pp. 308–318.',
 "mironov": 'I. Mironov, K. Talwar, and L. Zhang, "Rényi differential privacy of the sampled Gaussian mechanism," arXiv:1908.10530, 2019.',
 "balle": 'B. Balle, G. Barthe, M. Gaboardi, J. Hsu, and T. Sato, "Hypothesis testing interpretations and Rényi differential privacy," in Proc. AISTATS, 2020, pp. 2496–2506.',
 "bonawitz": 'K. Bonawitz et al., "Practical secure aggregation for privacy-preserving machine learning," in Proc. ACM CCS, 2017, pp. 1175–1191.',
 "paillier": 'P. Paillier, "Public-key cryptosystems based on composite degree residuosity classes," in Proc. EUROCRYPT, 1999, pp. 223–238.',
 "shapley": 'L. S. Shapley, "A value for n-person games," in Contributions to the Theory of Games II, Princeton Univ. Press, 1953, pp. 307–317.',
 "lundberg": 'S. M. Lundberg and S.-I. Lee, "A unified approach to interpreting model predictions," in Proc. NeurIPS, 2017, pp. 4765–4774.',
 "shokri": 'R. Shokri, M. Stronati, C. Song, and V. Shmatikov, "Membership inference attacks against machine learning models," in Proc. IEEE S&P, 2017, pp. 3–18.',
 "yeom": 'S. Yeom, I. Giacomelli, M. Fredrikson, and S. Jha, "Privacy risk in machine learning: Analyzing the connection to overfitting," in Proc. IEEE CSF, 2018, pp. 268–282.',
 "hardt": 'M. Hardt, E. Price, and N. Srebro, "Equality of opportunity in supervised learning," in Proc. NeurIPS, 2016, pp. 3315–3323.',
 "lin": 'J. Lin, "Divergence measures based on the Shannon entropy," IEEE Trans. Inf. Theory, vol. 37, no. 1, pp. 145–151, 1991.',
 "hsu": 'T.-M. H. Hsu, H. Qi, and M. Brown, "Measuring the effects of non-identical data distribution for federated visual classification," arXiv:1909.06335, 2019.',
 "detrano": 'R. Detrano et al., "International application of a new probability algorithm for the diagnosis of coronary artery disease," Am. J. Cardiol., vol. 64, no. 5, pp. 304–310, 1989.',
 "uci": 'D. Dua and C. Graff, "UCI Machine Learning Repository," Univ. California, Irvine, 2019. [Online]. Available: https://archive.ics.uci.edu',
 "kairouz": 'P. Kairouz et al., "Advances and open problems in federated learning," Found. Trends Mach. Learn., vol. 14, no. 1–2, pp. 1–210, 2021.',
 "carlini": 'N. Carlini, S. Chien, M. Nasr, S. Song, A. Terzis, and F. Tramèr, "Membership inference attacks from first principles," in Proc. IEEE S&P, 2022, pp. 1897–1914.',
}
ORDER_CITED = []
def c(*keys):
    nums = []
    for k in keys:
        if k not in ORDER_CITED: ORDER_CITED.append(k)
        nums.append(ORDER_CITED.index(k) + 1)
    return "[" + "], [".join(str(n) for n in nums) + "]" if len(nums) > 1 else f"[{nums[0]}]"

# ───────────── docx helpers ─────────────
doc = Document()
st = doc.styles["Normal"]; st.font.name = "Times New Roman"; st.font.size = Pt(10)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
st.paragraph_format.space_after = Pt(0); st.paragraph_format.space_before = Pt(0)
for name, size, italic, align, before, after, caps in [("Heading 1", 10, False, WD_ALIGN_PARAGRAPH.CENTER, 9, 3, True), ("Heading 2", 10, True, WD_ALIGN_PARAGRAPH.LEFT, 5, 2, False)]:
    h = doc.styles[name]; h.font.name = "Times New Roman"; h.font.size = Pt(size); h.font.italic = italic; h.font.bold = False
    h.font.color.rgb = RGBColor(0, 0, 0); h.font.small_caps = caps
    h.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman"); h.element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman"); h.element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    h.paragraph_format.alignment = align; h.paragraph_format.space_before = Pt(before); h.paragraph_format.space_after = Pt(after); h.paragraph_format.keep_with_next = True

sec0 = doc.sections[0]
sec0.page_width, sec0.page_height = Inches(8.5), Inches(11)
sec0.left_margin = sec0.right_margin = Inches(0.625); sec0.top_margin = Inches(0.75); sec0.bottom_margin = Inches(0.9)

def runs(p, text, size=None, base_italic=False, base_bold=False):
    for tok in re.split(r"(\*\*.+?\*\*|\*.+?\*)", text):
        if not tok: continue
        b, i = base_bold, base_italic
        if tok.startswith("**"): tok, b = tok[2:-2], True
        elif tok.startswith("*") and len(tok) > 2: tok, i = tok[1:-1], True
        r = p.add_run(tok); r.bold, r.italic = b, i
        if size: r.font.size = Pt(size)
    return p

def para(text, size=10, align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=0.17, italic=False, bold=False, after=0, before=0, keep=False):
    p = doc.add_paragraph(); runs(p, text, size, italic, bold)
    pf = p.paragraph_format; pf.alignment = align; pf.first_line_indent = Inches(indent) if indent else None
    pf.space_after = Pt(after); pf.space_before = Pt(before); pf.keep_with_next = keep
    return p

def H1(t): return doc.add_heading(t, level=1)
def H2(t): return doc.add_heading(t, level=2)

def img(name, width=3.4, cap=None, kind="Fig."):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_before = Pt(4); p.add_run().add_picture(os.path.join(FIG, name), width=Inches(width))
    if cap: para(cap, size=8, align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=0, after=5)

def equation(name, num, width=2.7):
    p = doc.add_paragraph(); pf = p.paragraph_format
    pf.tab_stops.add_tab_stop(Inches(1.6), WD_TAB_ALIGNMENT.CENTER); pf.tab_stops.add_tab_stop(Inches(3.5), WD_TAB_ALIGNMENT.RIGHT)
    pf.space_before = Pt(2); pf.space_after = Pt(2)
    p.add_run("\t"); p.add_run().add_picture(os.path.join(FIG, name), width=Inches(width)); p.add_run(f"\t({num})")

def set_cell_border(cell, **kw):
    tcPr = cell._tc.get_or_add_tcPr(); b = tcPr.find(qn("w:tcBorders"))
    if b is None: b = OxmlElement("w:tcBorders"); tcPr.append(b)
    for edge, val in kw.items():
        e = OxmlElement(f"w:{edge}"); e.set(qn("w:val"), val[0]); e.set(qn("w:sz"), str(val[1])); e.set(qn("w:color"), "000000"); b.append(e)

def table(title, header, rows, widths, num, bold_rows=(), size=7.5, note=None):
    cap = doc.add_paragraph(); cap.alignment = WD_ALIGN_PARAGRAPH.CENTER; cap.paragraph_format.keep_with_next = True
    cap.paragraph_format.space_before = Pt(5)
    r = cap.add_run(f"TABLE {num}\n"); r.font.size = Pt(8); r.font.small_caps = True
    r = cap.add_run(title.upper()); r.font.size = Pt(8); r.font.small_caps = False
    t = doc.add_table(rows=1 + len(rows), cols=len(header)); t.alignment = 1; t.autofit = False
    tbl = t._tbl; tblPr = tbl.tblPr
    for tag in ("w:tblW", "w:tblLayout", "w:tblInd"):
        for e in tblPr.findall(qn(tag)): tblPr.remove(e)
    w_ = OxmlElement("w:tblW"); w_.set(qn("w:w"), str(int(sum(widths) * 1440))); w_.set(qn("w:type"), "dxa"); tblPr.append(w_)
    lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
    for gc, wd in zip(tbl.tblGrid.findall(qn("w:gridCol")), widths): gc.set(qn("w:w"), str(int(wd * 1440)))
    for ri in range(len(rows) + 1):
        for ci in range(len(header)):
            cell = t.cell(ri, ci); cell.width = Inches(widths[ci])
            txt = header[ci] if ri == 0 else rows[ri - 1][ci]
            p = cell.paragraphs[0]; p.paragraph_format.keep_with_next = ri < len(rows)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if ci == 0 else WD_ALIGN_PARAGRAPH.CENTER
            rr = p.add_run(str(txt)); rr.font.size = Pt(size); rr.bold = (ri == 0) or ((ri - 1) in bold_rows)
            tcPr = cell._tc.get_or_add_tcPr(); mar = OxmlElement("w:tcMar")
            for side in ("top", "bottom"):
                m = OxmlElement(f"w:{side}"); m.set(qn("w:w"), "15"); m.set(qn("w:type"), "dxa"); mar.append(m)
            tcPr.append(mar)
            if ri == 0: set_cell_border(cell, top=("single", 8), bottom=("single", 4))
            if ri == len(rows): set_cell_border(cell, bottom=("single", 8))
    if note: para(note, size=7.5, indent=0, after=4, before=2, italic=True)
    else: para("", size=3, indent=0, after=3)

def set_cols(section, n=2, space=360):
    sp = section._sectPr; cols = sp.find(qn("w:cols"))
    if cols is None: cols = OxmlElement("w:cols"); sp.append(cols)
    cols.set(qn("w:num"), str(n)); cols.set(qn("w:space"), str(space))

# ───────────── title block (single column) ─────────────
p = para("TrustFed-Health: A Privacy-Preserving, Explainable and Fairness-Audited Hierarchical Federated Learning Framework for Multi-Hospital Heart-Disease Risk Prediction", size=22, align=WD_ALIGN_PARAGRAPH.CENTER, indent=0, after=8)
for r_ in p.runs: r_.font.name = "Times New Roman"
authors = [("Vikram R", "Department of CSE,\nIFET College of Engineering,\nVillupuram, India.\nrmvikram05@gmail.com"),
           ("[Co-author 2 name]", "Department of CSE,\n[Institution],\n[City, Country].\n[email]"),
           ("[Guide name, Dr.]", "Department of CSE,\n[Institution],\n[City, Country].\n[email]")]
t = doc.add_table(rows=1, cols=3); t.autofit = False
for i, (n, a_) in enumerate(authors):
    cell = t.cell(0, i); cell.width = Inches(2.42); p_ = cell.paragraphs[0]; p_.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rr = p_.add_run(n + "\n"); rr.font.size = Pt(10); rr.bold = True
    rr = p_.add_run(a_); rr.font.size = Pt(9)
para("", size=4, indent=0)

# ───────────── body (two columns) ─────────────
body = doc.add_section(WD_SECTION.CONTINUOUS); set_cols(body, 2, 360)
body.left_margin = body.right_margin = Inches(0.625)

base, tef = S[FED], S[MID]
dm2, dmci = d_mia[2.0][0], d_mia[2.0][1]
abstract = (f"**Abstract—**Hospitals cannot pool patient records, yet single-site models generalise poorly. We present TrustFed-Health, a hierarchical federated "
 f"learning (FL) framework for heart-disease risk prediction that combines record-level differential privacy (local DP-SGD with a Rényi accountant), "
 f"additive-secret-sharing secure aggregation inside regional hubs, an optional Paillier tier between hubs and the global server, exact Shapley "
 f"explanations, and a fairness audit that compares subgroup accuracy and SHAP-importance profiles. All components run in a tested, dependency-light "
 f"Python engine behind a role-based FastAPI service and React dashboard. We evaluate on {'the UCI Cleveland cohort' if REAL else 'a synthetic Cleveland-schema cohort (the real data could not be downloaded in the build environment)'} "
 f"({R['n']} patients) split over {SET['K']} non-IID hospitals using {SET['reps']}×{SET['folds']}-fold cross-validation. Secure aggregation is numerically exact "
 f"(max accuracy difference {smpc_gap:.3f}). Local DP at σ=2 (worst-case ε={eps[2.0]:.1f}, δ=10⁻⁵) lowers accuracy from {ms(FED,'acc')}% to {ms(MID,'acc')}% and reduces a "
 f"loss-threshold membership-inference attack from AUC {S[FED]['mia_auc']['mean']:.3f} to {S[MID]['mia_auc']['mean']:.3f} (paired Δ={dm2:.3f}, 95% CI [{dmci[0]:.3f}, {dmci[1]:.3f}]). "
 f"Federation beats isolated hospitals by {100*d_loc[0]:.1f} accuracy points. We report overheads, limitations and a reproducible protocol.")
para(abstract, size=9, bold=False, italic=False, indent=0, after=4)
para("**Keywords—**federated learning, differential privacy, secure aggregation, SHAP, algorithmic fairness, membership inference, healthcare AI", size=9, indent=0, after=4, italic=True)

# I. INTRODUCTION
H1("I. Introduction")
para(f"Machine-learning models for cardiovascular risk are only as good as the data behind them, but patient records are protected by law and institutional policy and cannot be centralised {c('rieke')}. "
     f"Federated learning (FL) trains a shared model by exchanging model updates instead of records {c('mcmahan')}, {c('kairouz')}. FL alone is not a privacy guarantee: updates can leak membership and attributes, "
     f"clinical users need to know *why* a model flags a patient, and a model that is accurate on average may still underperform for particular sexes, age bands or hospitals.")
para(f"Recent healthcare-FL work addresses pieces of this problem—hierarchical aggregation with DP and secure multi-party computation {c('singh')}, wearable prognostics {c('jain')}, key distribution for patient authentication {c('abu')}, "
     f"XGBoost-based federated transfer {c('tightiz')}, cyber-threat detection {c('ikegwu')} and blockchain-backed services {c('murala')}—but among the works we reviewed none jointly (i) *measures* privacy empirically with a membership-inference attack, "
     f"(ii) explains each prediction with exact attributions and (iii) audits subgroup fairness inside the federation. TrustFed-Health targets that gap.")
para("The contributions of this paper are:", indent=0.17, after=1)
for t_ in [f"a two-tier federation (hospital → regional hub → global server) with local record-level DP-SGD, exact additive-share secure aggregation and an optional packed-Paillier tier;",
           f"an auditable privacy pipeline: a Rényi-DP accountant for the Poisson-sampled Gaussian mechanism (checked against a published benchmark) plus an empirical membership-inference test;",
           f"exact Shapley explanations (all 2¹³ coalitions) and a fairness audit combining subgroup accuracy with a permutation test on SHAP-importance divergence;",
           f"an open, tested implementation (unit tests for gradients, accountant, secure sums, Paillier, SHAP efficiency and fairness detection) and a one-command reproduction of every number in this paper."]:
    para("• " + t_, indent=0, after=1).paragraph_format.left_indent = Inches(0.15)

# II. RELATED WORK
H1("II. Related Work")
para(f"**Federated learning in healthcare.** FedAvg {c('mcmahan')} remains the baseline; surveys emphasise statistical heterogeneity and privacy as open problems {c('kairouz')}, {c('rieke')}. Hierarchical designs reduce cross-silo communication and "
     f"allow regional trust domains; Singh *et al.* {c('singh')} combine them with DP and SMPC. We adopt that structure but add exact accounting and empirical attack testing.")
para(f"**Differential privacy.** DP-SGD clips per-example gradients and adds Gaussian noise {c('abadi')}. Privacy loss is tracked with Rényi DP; for Poisson-sampled Gaussian steps there is a closed form at integer orders {c('mironov')}, "
     f"converted to (ε, δ) with the tight rule of Balle *et al.* {c('balle')}. We implement this accountant directly.")
para(f"**Secure aggregation.** Additive secret sharing hides individual updates from the aggregator {c('bonawitz')}; additively homomorphic Paillier encryption {c('paillier')} lets an untrusted server add ciphertexts. We use both, at different tiers.")
para(f"**Explainability and fairness.** Shapley values {c('shapley')} underlie SHAP {c('lundberg')}; with 13 features we compute them exactly. Group-fairness criteria such as equalised odds {c('hardt')} compare error rates across subgroups; "
     f"we additionally compare *how* the model uses features per subgroup using Jensen–Shannon divergence {c('lin')}.")
para(f"**Privacy auditing.** Membership-inference attacks {c('shokri')}, {c('yeom')} estimate leakage empirically; stronger likelihood-ratio attacks exist {c('carlini')} and are left for future work.")

# III. PROBLEM
H1("III. Problem Statement and Objectives")
para(f"Given K hospitals, each holding a private, differently distributed tabular cohort, train a global risk model such that (O1) no site's raw data or individual update is revealed, "
     f"(O2) the privacy cost is quantified formally (ε, δ) and tested empirically, (O3) every prediction carries a faithful explanation, and (O4) performance and feature-use disparities across sex, age band and hospital are detected and reported. "
     f"The system should run end-to-end in a web application with role-based access and a tamper-evident audit trail.")

# IV. SYSTEM DESIGN
H1("IV. System Design")
H2("A. Architecture")
para(f"Fig. 1 shows the architecture. Hospitals train locally; the {SET['K']} sites are grouped into {len(SET['hubs'])} regional hubs (sizes {', '.join(str(len(h_)) for h_ in SET['hubs'])}). Inside a hub, updates are combined by secure summation; "
     f"hub totals are optionally encrypted under a key held by a separate authority and summed by the global server, which never sees an individual hub total in the clear. "
     f"After training, the explanation, fairness and privacy audits run on the global model and are exposed through a FastAPI service with JWT roles (hospital staff, regional admin, global admin) and a hash-chained audit log.")
img("architecture.png", 3.4, "Fig. 1. TrustFed-Health architecture: two-tier federation with local DP-SGD, SMPC in hubs, optional Paillier tier and post-hoc audits.")
H2("B. Model and Federated Optimisation")
para(f"The predictor is a 13–32–16–2 ReLU network ({SET['n_params']} parameters) over the 13 Cleveland attributes, standardised with public normalisation constants. Each round every hospital runs local SGD from the global weights and the server forms the sample-weighted average")
equation("eq_fedavg.png", 1, 1.35)
para("where nₖ is hospital k's training-set size and N=Σnₖ. Weights nₖθₖ and the count nₖ are aggregated together so the weighting itself is computed securely.", indent=0)
H2("C. Local Differential Privacy")
para(f"Each local step samples a Poisson mini-batch (rate q=B/nₖ), clips every per-example gradient to L2 norm C and adds Gaussian noise:")
equation("eq_dpsgd.png", 2, 3.05)
para(f"We implement per-example gradients analytically (verified against finite differences). The guarantee is *record-level* for each hospital over all T=rounds×steps local steps. "
     f"The accountant evaluates, for integer orders α∈[2, 256],")
equation("eq_rdp.png", 3, 3.05)
para("composes T steps linearly, and converts to (ε, δ)-DP:", indent=0)
equation("eq_conv.png", 4, 2.9)
para(f"As a correctness check our code reproduces ε≈2.6 for the standard MNIST benchmark (N=60 000, B=256, σ=1.1, 60 epochs, δ=10⁻⁵), and the older, looser conversion gives ≈3.0, the value commonly quoted for this benchmark. We report the *maximum* ε over hospitals, which is governed by the smallest site.")
H2("D. Secure Aggregation")
para(f"**Tier 1 (SMPC).** A hospital encodes its vector in fixed point (2⁻²⁴ resolution) and splits it into one random share per member of its hub:")
equation("eq_share.png", 5, 2.9)
para(f"Member j adds the shares it receives and the hub adds the partial sums, so only the *total* is ever formed; any single share or partial sum is uniform on ℤ₂⁶⁴. "
     f"Exactness is tested: the aggregate equals the plain sum to 10⁻⁶. **Tier 2 (HE).** Hub totals are encrypted with Paillier {c('paillier')} (g=n+1) using slot packing—19 values of 52 bits per 1024-bit plaintext—so a {SET['n_params']+1}-element vector needs 54 ciphertexts; the global server multiplies ciphertexts and a key authority decrypts only the sum. "
     f"A hub of two sites cannot hide a member's update from the other member once the hub total is known; this inherent limit is discussed in Section VII.")
H2("E. Explainability")
para(f"For a standardised patient x and reference b (the population mean after standardisation), the Shapley value of feature j for the logit margin f=z₁−z₀ is")
equation("eq_shap.png", 6, 3.05)
para(f"Because d=13 we enumerate all 8 192 coalitions, so values are exact and satisfy efficiency, Σφⱼ=f(x)−f(b) (unit-tested). An LLM can optionally verbalise the top attributions, constrained to those numbers; a deterministic template is used when no key is configured.")
H2("F. Fairness Audit")
para(f"On held-out predictions we report, per subgroup (sex, age <55/55–64/≥65, hospital site), accuracy, TPR and FPR. To test whether the model *uses features differently* for a group g we compute normalised mean-|SHAP| profiles and")
equation("eq_js.png", 7, 2.3)
para(f"with p-values from {500} label-permutation draws. A subgroup with n≥15 is flagged if its accuracy deviates from overall by >10 points or p<0.05. The fairness score is 1−max accuracy gap. "
     f"A SHAP flag signals a *different feature profile*—often reflecting covariate differences—and is a prompt for clinical review, not proof of bias.")
H2("G. Empirical Privacy Test")
para(f"We run a loss-threshold membership-inference attack {c('yeom')} with members = training records and non-members = held-out records:")
equation("eq_mia.png", 8, 2.6)
para("AUC 0.5 means no leakage. This is a weak attack; a low AUC does not prove privacy, which is why the formal ε is reported alongside it.", indent=0)

# V. EXPERIMENTAL SETUP
H1("V. Experimental Setup")
H2("A. Data and Federation")
if REAL:
    para(f"We use the UCI Cleveland heart-disease data {c('detrano')}, {c('uci')}: {R['n']} complete records (6 with missing values removed), 13 attributes, binary target (disease present = diagnosis>0; prevalence {100*R['prevalence']:.1f}%).")
else:
    para(f"**Data disclosure.** The sandbox used to build this version had no internet access, so the UCI Cleveland file {c('detrano')}, {c('uci')} could not be fetched. All reported numbers therefore come from a *synthetic* cohort with the same 13-attribute schema, "
         f"{R['n']} patients and prevalence {100*R['prevalence']:.1f}%, generated from approximate class-conditional marginals. These results validate the pipeline, not clinical performance. "
         f"Running python -m tefl.run_experiments --data cleveland and rebuilding this paper replaces every number with real-data results.")
para(f"Patients are assigned to K={SET['K']} hospitals with label skew (Dirichlet α={SET['alpha']} {c('hsu')}) and age skew, guaranteeing ≥5 patients per class per site; mean training sizes are {', '.join(f'{x:.0f}' for x in hs)}. "
     f"The same mechanism assigns held-out patients to sites so each hospital has a site-specific test slice.")
H2("B. Protocol and Baselines")
para(f"We use {SET['reps']} repetitions of stratified {SET['folds']}-fold cross-validation ({n_runs} runs per method, identical splits across methods). Normalisation constants come from the training fold. Methods: centralised pooled training (upper bound), local-only training, "
     f"FedAvg on IID and non-IID partitions, FedAvg+SMPC, FedAvg with 150 rounds (to expose overfitting leakage), and TEFL (local DP-SGD + SMPC) at σ∈{{{', '.join(f'{s:g}' for s in SET['sigmas'])}}}. Table I lists the shared settings.")
table("Experimental configuration", ["Parameter", "Value"], [
    ["Network / parameters", f"13–32–16–2 ReLU / {SET['n_params']}"], ["Rounds × local epochs", f"{SET['rounds']} × {SET['local_epochs']}"],
    ["Expected batch B / lr (SGD)", f"{SET['batch']} / {SET['lr']}"], ["Clip norm C", f"{SET['clip']}"],
    ["Noise multiplier σ", ", ".join(f"{s:g}" for s in SET["sigmas"])], ["δ / RDP orders", "10⁻⁵ / 2…256"],
    ["Hospitals / hubs", f"{SET['K']} / {len(SET['hubs'])} ({'+'.join(str(len(h_)) for h_ in SET['hubs'])})"],
    ["Partition", f"Dirichlet α={SET['alpha']}, age skew {SET['skew']}"], ["Evaluation", f"{SET['reps']}×{SET['folds']}-fold CV"]], [1.75, 1.7], "I")

# VI. RESULTS
H1("VI. Results and Discussion")
H2("A. Utility and Privacy")
rows = []
order = ["Centralized (pooled)", "Local-only (mean of sites)", FEDS, FED, SMPC, EXT] + [TE(s) for s in SET["sigmas"]]
labels = {"Centralized (pooled)": "Centralised (pooled)", "Local-only (mean of sites)": "Local-only (mean)", FEDS: "FedAvg, IID", FED: "FedAvg, non-IID", SMPC: "FedAvg + SMPC", EXT: "FedAvg, 150 rounds"}
for m in order:
    s_ = S[m]; mia = f"{s_['mia_auc']['mean']:.3f}" if s_.get("mia_auc") else "—"
    e_ = f"{s_['epsilon']['mean']:.1f}" if s_.get("epsilon") else "—"
    rows.append([labels.get(m, m.replace("TEFL (sigma=", "TEFL σ=").replace(")", "")), ms(m, "acc"), f"{s_['auc']['mean']:.3f}", mia, e_])
table(f"Test results, mean ± SD over {n_runs} runs", ["Method", "Acc. (%)", "ROC-AUC", "MIA AUC", "ε"], rows, [1.1, 0.85, 0.55, 0.55, 0.4], "II", bold_rows=(len(order) - 3,),
      note="MIA AUC: loss-threshold attack (0.5 = chance). ε: worst hospital, δ=10⁻⁵.")
sig_txt = lambda a: "lower" if a < 0 else "higher"
para(f"Table II and Fig. 2 summarise utility. Federation is clearly worthwhile: non-IID FedAvg exceeds isolated hospitals by {100*d_loc[0]:.1f} accuracy points (paired 95% CI [{100*d_loc[1][0]:.1f}, {100*d_loc[1][1]:.1f}]) and is within "
     f"{100*abs(S['Centralized (pooled)']['acc']['mean']-base['acc']['mean']):.1f} points of centralised training. Non-IID skew changes accuracy by {z(100*d_iid[0])} points relative to IID (CI [{z(100*d_iid[1][0])}, {z(100*d_iid[1][1])}]). "
     f"Secure aggregation is exact: FedAvg and FedAvg+SMPC differ by at most {smpc_gap:.3f} accuracy in any run, because the ring arithmetic is lossless up to 2⁻²⁴ quantisation.")
img("convergence.png", 3.4, "Fig. 2. Test accuracy per round (mean of the five folds of repetition 1). Higher noise slows convergence.")
para(f"Local DP trades accuracy for privacy smoothly: σ=1 / 2 / 4 / 8 give worst-case ε≈{eps[1.0]:.1f} / {eps[2.0]:.1f} / {eps[4.0]:.1f} / {eps[8.0]:.1f} and accuracy {ms(TE(1.0),'acc')} / {ms(MID,'acc')} / {ms(TE(4.0),'acc')} / {ms(TE(8.0),'acc')}%. "
     f"The paired accuracy cost relative to non-private FedAvg is {100*d_acc[2.0][0]:.1f} points at σ=2 (CI [{100*d_acc[2.0][1][0]:.1f}, {100*d_acc[2.0][1][1]:.1f}]). "
     f"These ε values are large by deployment standards: they are set by the smallest hospital ({min(hs):.0f} training records on average), where each record is sampled in a large fraction of the steps. More data per site, fewer rounds or larger σ shrink ε, at the utility cost in Fig. 3.")
img("tradeoff.png", 3.4, "Fig. 3. Privacy–utility trade-off. Left: accuracy (±SD). Right: membership-inference AUC (±SE); dashed = non-private FedAvg, dotted = chance.")
para(f"**Empirical leakage.** Even without DP the attack is weak here (AUC {base['mia_auc']['mean']:.3f} at {SET['rounds']} rounds; {S[EXT]['mia_auc']['mean']:.3f} after 150 rounds; {S['Centralized (pooled)']['mia_auc']['mean']:.3f} for the pooled model), "
     f"because a 1 010-parameter network trained briefly on ~240 records barely overfits. DP still reduces the AUC monotonically towards 0.5 (σ=8: {S[TE(8.0)]['mia_auc']['mean']:.3f}); the paired reduction at σ=2 is {dm2:.3f} (95% CI [{dmci[0]:.3f}, {dmci[1]:.3f}]). "
     f"This effect is statistically detectable but small in absolute terms, and the CI treats repeated-CV runs as independent, so it is optimistic. We therefore do not claim that DP 'eliminates' leakage; the formal ε is the guarantee, the attack is a sanity check.")
H2("B. Explainability")
g1, g2 = R["shap_global"][FED], R["shap_global"][MID]
top = sorted(g1, key=lambda k: -g1[k])[:3]; topd = sorted(g2, key=lambda k: -g2[k])[:3]
nice = {"age": "age", "sex": "sex", "cp": "chest-pain type", "trestbps": "resting BP", "chol": "cholesterol", "fbs": "fasting sugar", "restecg": "resting ECG", "thalach": "max heart rate", "exang": "exercise angina", "oldpeak": "ST depression", "slope": "ST slope", "ca": "vessels (ca)", "thal": "thalassemia"}
rk = lambda d: {k: i for i, k in enumerate(sorted(d, key=lambda k: -d[k]))}
from scipy.stats import spearmanr
rho = spearmanr([g1[k] for k in g1], [g2[k] for k in g1])[0]
para(f"Fig. 4 shows global importance (mean |SHAP|, pooled out-of-fold predictions of repetition 1). The three most influential features are {', '.join(nice[k] for k in top)} for non-private FedAvg and {', '.join(nice[k] for k in topd)} with DP; "
     f"the Spearman rank correlation of the two importance vectors is {rho:.2f}, i.e. DP noise {'largely preserves' if rho > 0.7 else 'noticeably reshuffles'} which features drive predictions. "
     f"{'These rankings agree with established clinical risk markers.' if REAL else 'Rankings on synthetic data reflect the generator, not clinical knowledge.'}")
img("shap.png", 3.4, "Fig. 4. Global feature importance for non-private FedAvg and TEFL σ=2.")
H2("C. Fairness Audit")
ORD = ["Female", "Male", "Age <55", "Age 55-64", "Age >=65"] + [f"Hospital {i}" for i in range(1, 6)]
getr = lambda a, g: next(r for r in A[a]["subgroups"] if r["subgroup"] == g)
frows = []
for g in ORD:
    ra, rb = getr(FED, g), getr(MID, g)
    frows.append([g.replace("Age >=65", "Age ≥65").replace("Hospital ", "Hosp. "), ra["n"], f"{100*ra['accuracy']:.1f}", f"{100*rb['accuracy']:.1f}", f"{rb['shap_divergence']:.3f}", f"{rb['shap_p']:.3f}" + ("*" if rb["shap_p"] < .05 and rb["n"] >= 15 else "")])
table("Subgroup audit (pooled out-of-fold test predictions)", ["Subgroup", "n", "Acc. FedAvg", "Acc. TEFL σ=2", "JS div.", "p"], frows, [0.9, 0.4, 0.7, 0.8, 0.45, 0.45], "III",
      note=f"* p<0.05 (500 permutations). Overall accuracy: FedAvg {100*A[FED]['overall_accuracy']:.1f}%, TEFL {100*A[MID]['overall_accuracy']:.1f}%.")
nf = lambda a: len(A[a]["flags"])
para(f"Fairness scores are {A[FED]['score']:.3f} (FedAvg) and {A[MID]['score']:.3f} (TEFL σ=2), i.e. the largest subgroup accuracy gap is {100*(1-A[FED]['score']):.1f} and {100*(1-A[MID]['score']):.1f} points. The audit raised {nf(FED)} and {nf(MID)} flags respectively. "
     f"Subgroup sizes are small (smallest: {sub_n} patients), so per-group accuracies have wide uncertainty (a binomial 95% interval at that size is roughly ±{half:.0f} points); the flags are best read as review prompts. "
     f"Fig. 5 shows that, relative to non-private FedAvg, DP changes subgroup accuracies by between {min(del_):+.1f} and {max(del_):+.1f} points.")
img("fairness.png", 3.4, "Fig. 5. Subgroup accuracy; dashed lines mark overall accuracy.")
H2("D. Overhead")
table("Aggregation cost per round (5 hospitals, 1 011 values)", ["Protocol", "Time"], [
    ["Plain sum", f"{HEB['plain sum']*1e6:.0f} µs"], ["SMPC (additive shares)", f"{HEB['SMPC (additive shares)']*1e3:.2f} ms"],
    ["SMPC + Paillier-1024 (packed)", f"{HEB['SMPC + Paillier-1024']:.2f} s"], ["SMPC + Paillier-2048 (packed)", f"{HEB['SMPC + Paillier-2048']:.2f} s"]], [2.3, 1.1], "IV",
    note="Single-threaded pure-Python Paillier; key generation is excluded.")
para(f"Additive-share SMPC is negligible; Paillier dominates (about {HEB['SMPC + Paillier-1024']:.1f} s per round at 1 024 bits and {HEB['SMPC + Paillier-2048']:.1f} s at 2 048 bits even with packing), "
     f"which is acceptable for cross-hospital rounds that take minutes but is why HE is optional in the dashboard. Optimised big-integer libraries would reduce this substantially.")

# VII. LIMITATIONS
H1("VII. Limitations and Threats to Validity")
for t_ in [("Data.", " " + ("Cleveland is a single-institution cohort of 297 patients; the 'hospitals' are simulated partitions, not real sites, and results do not establish clinical validity." if REAL else "Results use a synthetic cohort and must be regenerated on real data before any scientific claim; the 'hospitals' are simulated partitions.")),
           ("Privacy.", " DP is record-level per hospital, assumes honest Poisson sampling and ignores privacy spent on hyper-parameter selection and on normalisation constants (treated as public). The attack is weak; stronger attacks may recover more. Secure summation inside a two-site hub reveals the other member's update to a member who learns the hub total, and neither SMPC nor HE defends against malicious or colluding parties."),
           ("Fairness.", " Small subgroups yield noisy estimates; SHAP-profile divergence is partly driven by covariate differences and is a review signal, not a bias test. Multiple comparisons are not corrected."),
           ("Scope.", " The model is a small MLP on 13 tabular attributes; it is decision support, not a diagnostic device. Differences across partitions and seeds are reported as SD, and confidence intervals from repeated CV are optimistic.")]:
    para(f"**{t_[0]}**{t_[1]}", indent=0, after=2)

# VIII. CONCLUSION
H1("VIII. Conclusion and Future Work")
para(f"TrustFed-Health shows that formal DP accounting, exact secure aggregation, exact explanations and subgroup auditing can be combined in one small, fully tested federated pipeline. "
     f"On {'Cleveland' if REAL else 'the synthetic cohort'}, federation outperformed isolated hospitals, secure aggregation cost no accuracy, and DP traded a few accuracy points for a lower—but not zero—empirical leakage. "
     f"Future work includes evaluation on multi-institution clinical data, likelihood-ratio membership attacks {c('carlini')}, secure aggregation with dropout tolerance and malicious-security guarantees, client-level DP, fairness-aware training, and native Flower/Opacus back-ends.")
H1("Reproducibility")
para("Code, tests and the paper builder are in the project archive: python tests/test_tefl.py, python -m tefl.run_experiments --data cleveland, then python paper/make_figures.py results/results.json && python paper/build_paper.py results/results.json.", indent=0)

# REFERENCES
H1("References")
for i, k in enumerate(ORDER_CITED, 1):
    p = para(f"[{i}] {REFS[k]}", size=8, indent=0, after=2); p.paragraph_format.left_indent = Inches(0.28); p.paragraph_format.first_line_indent = Inches(-0.28)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
doc.save(OUT); print("saved", OUT, "| refs:", len(ORDER_CITED), "of", len(REFS), "| unused:", [k for k in REFS if k not in ORDER_CITED])
