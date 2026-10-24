"""Figures + equation images for the paper. All data figures read results.json."""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figs")
plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"],
                     "font.size": 7, "axes.linewidth": 0.6, "savefig.dpi": 300, "mathtext.fontset": "stix"})
COL = {"FedAvg": "#222222", 1: "#7f7f7f", 2: "#1f5fa8", 4: "#d9822b", 8: "#b22222"}
NICE = {"age": "age", "sex": "sex", "cp": "chest pain", "trestbps": "rest. BP", "chol": "cholesterol", "fbs": "fasting sugar",
        "restecg": "rest. ECG", "thalach": "max HR", "exang": "exer. angina", "oldpeak": "ST depression",
        "slope": "ST slope", "ca": "vessels (ca)", "thal": "thalassemia"}


def box(ax, x, y, w, h, text, fc="#eef3fb", ec="#1f3a68", fs=6.2, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.01,rounding_size=0.015", fc=fc, ec=ec, lw=0.7))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else "normal")


def arrow(ax, p, q, text=None, dy=0.0, dx=0.0, color="#1f3a68"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=7, lw=0.7, color=color))
    if text:
        ax.text((p[0] + q[0]) / 2 + dx, (p[1] + q[1]) / 2 + dy, text, fontsize=5.3, ha="left", va="center", color=color)


def architecture():
    fig, ax = plt.subplots(figsize=(3.45, 3.55)); ax.set_xlim(0, 1); ax.set_ylim(-0.03, 1); ax.axis("off")
    box(ax, .30, .875, .40, .105, "Global server\n(FedAvg on ciphertext sums)", "#dfe9f8", bold=True)
    box(ax, .77, .875, .22, .105, "Key authority\n(Paillier sk)", "#fbeede", "#8a5a14")
    box(ax, .06, .625, .38, .125, "Regional hub East\n(additive-share SMPC)", "#e6f3ea", "#245c36")
    box(ax, .56, .625, .38, .125, "Regional hub West\n(additive-share SMPC)", "#e6f3ea", "#245c36")
    xs = [.015, .215, .415, .615, .815]
    for i, x in enumerate(xs):
        box(ax, x, .36, .17, .15, f"Hospital\n{i+1}\nDP-SGD", "#f6f6f6", "#444444", fs=5.8)
    for i in range(3): arrow(ax, (xs[i] + .085, .51), (.25, .625))
    for i in range(3, 5): arrow(ax, (xs[i] + .085, .51), (.75, .625))
    arrow(ax, (.25, .75), (.42, .875), "Enc(hub sum)", dx=-.2, dy=-.0)
    arrow(ax, (.75, .75), (.58, .875))
    arrow(ax, (.70, .93), (.77, .93)); arrow(ax, (.77, .90), (.70, .90))
    ax.text(.5, .325, "raw patient data never leaves a hospital; only noised updates are shared",
            ha="center", fontsize=5.3, style="italic")
    ax.text(.5, .265, "audits run on the final global model", ha="center", fontsize=5.3, color="#666666")
    box(ax, .02, .12, .30, .12, "Exact SHAP\n(2¹³ coalitions)", "#fff8dc", "#8a7a14")
    box(ax, .35, .12, .30, .12, "Fairness audit\n(subgroup + JS test)", "#fff8dc", "#8a7a14")
    box(ax, .68, .12, .30, .12, "Membership-\ninference audit", "#fff8dc", "#8a7a14")
    box(ax, .02, .005, .96, .08, "FastAPI + JWT roles  ·  hash-chained audit log  ·  React dashboard", "#eeeeee", "#444444", fs=5.8)
    fig.savefig(f"{FIG}/architecture.png", bbox_inches="tight", pad_inches=0.02); plt.close(fig)


def convergence(R):
    fig, ax = plt.subplots(figsize=(3.45, 2.1))
    cur = R["curves"]
    for name, key in [("FedAvg (non-IID)", "FedAvg"), ("TEFL (sigma=1)", 1), ("TEFL (sigma=2)", 2), ("TEFL (sigma=4)", 4), ("TEFL (sigma=8)", 8)]:
        m = np.array(cur[name]["mean"]) * 100
        lab = "FedAvg (no DP)" if key == "FedAvg" else f"TEFL σ={key}"
        ax.plot(range(1, len(m) + 1), m, color=COL[key], lw=1.1, ls="-" if key != "FedAvg" else "--", label=lab)
    ax.set_xlabel("Communication round"); ax.set_ylabel("Test accuracy (%)"); ax.grid(alpha=.25, lw=.4)
    ax.legend(fontsize=5.8, ncol=2, frameon=False, loc="lower right"); ax.set_xlim(1, len(m))
    fig.savefig(f"{FIG}/convergence.png", bbox_inches="tight", pad_inches=0.02); plt.close(fig)


def tradeoff(R):
    S = R["summary"]; sig = R["setup"]["sigmas"]
    names = [f"TEFL (sigma={s:g})" for s in sig]
    eps = [S[n]["epsilon"]["mean"] for n in names]
    acc = np.array([S[n]["acc"]["mean"] for n in names]) * 100; accs = np.array([S[n]["acc"]["std"] for n in names]) * 100
    mia = np.array([S[n]["mia_auc"]["mean"] for n in names]); mias = np.array([S[n]["mia_auc"]["std"] for n in names])
    base = S["FedAvg (non-IID)"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(3.45, 1.95))
    a.errorbar(eps, acc, yerr=accs, fmt="o-", color="#1f5fa8", ms=3, lw=1, capsize=2, elinewidth=.6)
    a.axhline(base["acc"]["mean"] * 100, color="#222", ls="--", lw=.8); a.text(eps[-1], base["acc"]["mean"] * 100 + .8, "no DP", fontsize=5.8, ha="left")
    for e, s in zip(eps, sig): a.annotate(f"σ={s:g}", (e, acc[sig.index(s)]), textcoords="offset points", xytext=(2, -8), fontsize=5.4)
    a.set_xscale("log"); a.set_xlabel("ε (δ=1e-5)"); a.set_ylabel("Accuracy (%)"); a.grid(alpha=.25, lw=.4)
    b.errorbar(eps, mia, yerr=mias / np.sqrt(R["setup"]["folds"] * R["setup"]["reps"]), fmt="s-", color="#b22222", ms=3, lw=1, capsize=2, elinewidth=.6)
    b.axhline(base["mia_auc"]["mean"], color="#222", ls="--", lw=.8); b.axhline(.5, color="#888", ls=":", lw=.8)
    b.text(max(eps), .5 + .0015, "chance", fontsize=5.8, color="#666", ha="right")
    b.text(max(eps), base["mia_auc"]["mean"] - .0035, "no DP", fontsize=5.8, ha="right")
    b.set_xscale("log"); b.set_xlabel("ε (δ=1e-5)"); b.set_ylabel("Attack AUC"); b.grid(alpha=.25, lw=.4)
    from matplotlib.ticker import ScalarFormatter, NullFormatter
    for axx in (a, b):
        axx.set_xticks([2, 5, 10, 20]); axx.xaxis.set_major_formatter(ScalarFormatter()); axx.xaxis.set_minor_formatter(NullFormatter())
    fig.tight_layout(w_pad=1.0)
    fig.savefig(f"{FIG}/tradeoff.png", bbox_inches="tight", pad_inches=0.02); plt.close(fig)


def shap_fig(R):
    g = R["shap_global"]; a, b = g["FedAvg (non-IID)"], g["TEFL (sigma=2)"]
    order = sorted(a, key=lambda k: a[k])
    fig, ax = plt.subplots(figsize=(3.45, 2.45)); y = np.arange(len(order))
    ax.barh(y + .2, [a[k] for k in order], .38, color="#555555", label="FedAvg (no DP)")
    ax.barh(y - .2, [b[k] for k in order], .38, color="#1f5fa8", label="TEFL σ=2")
    ax.set_yticks(y); ax.set_yticklabels([NICE[k] for k in order], fontsize=6.3)
    ax.set_xlabel("mean |SHAP| (log-odds)"); ax.legend(fontsize=6, frameon=False, loc="lower right"); ax.grid(axis="x", alpha=.25, lw=.4)
    fig.savefig(f"{FIG}/shap.png", bbox_inches="tight", pad_inches=0.02); plt.close(fig)


def fairness_fig(R):
    A, B = R["audits"]["FedAvg (non-IID)"], R["audits"]["TEFL (sigma=2)"]
    ORD = ["Female", "Male", "Age <55", "Age 55-64", "Age >=65"] + [f"Hospital {i}" for i in range(1, 6)]
    srt = lambda L: sorted(L, key=lambda r: ORD.index(r["subgroup"]))
    rows = srt(A["subgroups"]); Bs = srt(B["subgroups"])
    lab = [r["subgroup"].replace("Hospital ", "H").replace("Age ", "").replace("-", "–").replace(">=", "≥") for r in rows]
    fig, ax = plt.subplots(figsize=(3.45, 1.9)); x = np.arange(len(rows))
    ax.bar(x - .2, [r["accuracy"] * 100 for r in rows], .38, color="#555555", label="FedAvg")
    ax.bar(x + .2, [r["accuracy"] * 100 for r in Bs], .38, color="#1f5fa8", label="TEFL σ=2")
    ax.axhline(A["overall_accuracy"] * 100, color="#555", ls="--", lw=.7); ax.axhline(B["overall_accuracy"] * 100, color="#1f5fa8", ls="--", lw=.7)
    ax.set_xticks(x); ax.set_xticklabels(lab, rotation=40, ha="right", fontsize=6); ax.set_ylabel("Accuracy (%)")
    ax.set_ylim(60, 100); ax.legend(fontsize=6, frameon=False, ncol=2, loc="upper left"); ax.grid(axis="y", alpha=.25, lw=.4)
    fig.savefig(f"{FIG}/fairness.png", bbox_inches="tight", pad_inches=0.02); plt.close(fig)


EQS = {
 "eq_fedavg": r"$\theta^{t+1}=\sum_{k=1}^{K}\frac{n_k}{N}\,\theta_k^{t+1}$",
 "eq_dpsgd": r"$\tilde g=\frac{1}{qn}\left(\sum_{i\in\mathcal{B}}g_i\min\left(1,\frac{C}{\|g_i\|_2}\right)+\mathcal{N}(0,\sigma^2C^2\mathbf{I})\right)$",
 "eq_rdp": r"$\varepsilon_\alpha(q,\sigma)=\frac{1}{\alpha-1}\log\sum_{j=0}^{\alpha}\binom{\alpha}{j}(1-q)^{\alpha-j}q^{j}e^{(j^2-j)/2\sigma^2}$",
 "eq_conv": r"$\varepsilon=\min_{\alpha}\left[T\varepsilon_\alpha+\log\frac{\alpha-1}{\alpha}-\frac{\log\delta+\log\alpha}{\alpha-1}\right]$",
 "eq_share": r"$\sum_{j=1}^{m}s_i^{(j)}\equiv\mathrm{enc}(v_i)\ (\mathrm{mod}\ 2^{64}),\quad \mathrm{enc}(v)=\mathrm{round}(2^{24}v)$",
 "eq_shap": r"$\phi_j(x)=\sum_{S\subseteq F\setminus\{j\}}\frac{|S|!\,(d-|S|-1)!}{d!}\left[f(x_{S\cup\{j\}},b)-f(x_S,b)\right]$",
 "eq_js": r"$D_g=\mathrm{JS}(I_g\,\|\,I_{\bar g}),\quad I_g=\frac{\overline{|\phi|}_g}{\|\overline{|\phi|}_g\|_1}$",
 "eq_mia": r"$s(x,y)=-\ell(\theta;x,y),\qquad \mathrm{Adv}=\max_{\tau}\,(\mathrm{TPR}_\tau-\mathrm{FPR}_\tau)$",
}


def equations():
    for k, tex in EQS.items():
        fig = plt.figure(figsize=(3.3, 0.5)); fig.text(0.5, 0.5, tex, fontsize=8.6, ha="center", va="center")
        fig.savefig(f"{FIG}/{k}.png", bbox_inches="tight", pad_inches=0.03, transparent=False, facecolor="white"); plt.close(fig)


if __name__ == "__main__":
    R = json.load(open(sys.argv[1]))
    architecture(); convergence(R); tradeoff(R); shap_fig(R); fairness_fig(R); equations(); print("figures ok")
