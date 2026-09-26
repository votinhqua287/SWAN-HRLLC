"""Figures of the page-limited manuscript (paper/main.tex).

Implements Section 5 of .claude/skills/ieee-paper-writing/SKILL.md:
  * Times New Roman for all text (math in the same font), TrueType embedding;
  * one PDF per panel, generated at the printed size and included at natural size;
  * all panels of a figure share the same canvas and the same axes box (common margins,
    never bbox_inches="tight");
  * no panel titles and no "(a)" in the images - LaTeX \\subfloat[] prints "(a)" under the x-label;
  * legends inside the axes; overflow and overlap with the data are checked and reported.
Usage:  python -m experiments.paper_figs            (all figures)
        python -m experiments.paper_figs 4 6        (selected figures)
"""
import os, sys, json, glob
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from experiments.run_campaign import load, RESULTS
from src.tail_analysis import single_user_fixed_sa

FIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "paper", "figures")

RC = {
    "font.family": "serif",
    "font.serif": ["Times New Roman"],
    "mathtext.fontset": "custom",
    "mathtext.rm": "Times New Roman",
    "mathtext.it": "Times New Roman:italic",
    "mathtext.bf": "Times New Roman:bold",
    "mathtext.sf": "Times New Roman",
    "mathtext.cal": "Times New Roman:italic",
    "mathtext.fallback": "stix",
    "pdf.fonttype": 42, "ps.fonttype": 42,
    "axes.linewidth": 0.5, "lines.linewidth": 0.9, "lines.markersize": 3.3, "lines.markeredgewidth": 0.8,
    "xtick.major.width": 0.5, "ytick.major.width": 0.5, "xtick.minor.width": 0.4, "ytick.minor.width": 0.4,
    "xtick.major.size": 2.5, "ytick.major.size": 2.5, "xtick.minor.size": 1.4, "ytick.minor.size": 1.4,
    "xtick.direction": "in", "ytick.direction": "in", "xtick.top": True, "ytick.right": True,
    "axes.grid": True, "grid.linewidth": 0.3, "grid.alpha": 0.4, "grid.color": "0.6",
    "legend.frameon": True, "legend.framealpha": 0.95, "legend.edgecolor": "0.55", "legend.fancybox": False,
    "legend.borderpad": 0.3, "legend.labelspacing": 0.22, "legend.handlelength": 2.1,
    "legend.handletextpad": 0.4, "legend.borderaxespad": 0.35, "legend.columnspacing": 0.8,
    "axes.labelpad": 1.2, "xtick.major.pad": 1.8, "ytick.major.pad": 1.5,
    "savefig.dpi": 300, "figure.dpi": 100,
}
# canvas (in), font sizes (label, tick, legend) per layout
SIZES = {"w2": (3.40, 2.05), "w3": (2.28, 1.80), "w4": (1.74, 1.68), "col": (3.30, 2.25), "colbar": (3.30, 2.05)}
FONTS = {"w2": (7.5, 7.0, 6.5), "col": (7.5, 7.0, 6.5), "colbar": (7.5, 7.0, 6.5),
         "w3": (7.0, 6.5, 6.0), "w4": (7.0, 6.5, 6.0)}

PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
# scheme -> (legend label, colour slot, marker, line style); colour and marker fixed per scheme
SERIES = {
    "TLA-SWAN":          ("TLA-SWAN (proposed)", 0, "o", "-"),
    "SWAN-MLWDF":        ("M-LWDF", 1, "s", "--"),
    "SWAN-MW":           ("Max-weight", 2, "^", "-."),
    "SWAN-EDF":          ("EDF", 3, "v", ":"),
    "SWAN-SR":           ("Sum-rate + MW", 4, "D", "--"),
    "SWAN-fixed":        ("Fixed PAs", 5, "x", "-."),
    "PASS-1WG":          ("Conventional PASS", 7, "*", "--"),
    "Fixed-array":       ("Fixed array", 6, "p", ":"),
    "SWAN-RATEMAX":      ("Rate-max", 6, "h", "--"),
    "SWAN-SA":           ("Fixed SA (TDMA)", 7, "P", ":"),
    "SWAN-reactive":     ("Reactive repositioning", 6, "d", ":"),
    "TLA-SWAN-cfg":      ("TLA-SWAN (proposed)", 0, "o", "-"),
    "TLA-SWAN-cfg-warm": ("TLA-SWAN, keep-warm", 1, "s", "--"),
    "SWAN-FULL-cfg":     ("Full activation", 7, "*", ":"),
    "SWAN-FIXJ-onoff":   ("ON–OFF arrivals", 0, "o", "-"),
    "SWAN-FIXJ-poisson": ("Poisson arrivals", 1, "s", "--"),
    "SINGLE-SA":         ("Simulation", 0, "o", "-"),
}
PR = r"$\Pr\{D>D_{\max}\}$"


# ------------------------------------------------------------------ helpers
def _floor(y, arr):
    y = np.asarray(y, float)
    return np.where(y > 0, y, 1.0 / np.maximum(np.asarray(arr, float), 1))


def _merge(a, b):
    out = {k: dict(v) for k, v in a.items()}
    for k, v in b.items():
        out.setdefault(k, {}).update(v)
    return out


def series(ax, x, y, scheme, label=None, **kw):
    lab, c, m, ls = SERIES[scheme]
    ms = kw.pop("ms", None)
    ax.plot(x, y, linestyle=ls, marker=m, color=PALETTE[c], markerfacecolor="white",
            label=lab if label is None else label, ms=ms if ms else plt.rcParams["lines.markersize"], **kw)


def sweep(ax, exp, schemes, xfun=None, metric="pv", labels=None):
    R = load(exp)
    labels = labels or {}
    for s in schemes:
        if s not in R:
            continue
        vals = sorted(R[s].keys(), key=lambda v: (v is None, v))
        x = [xfun(v) if xfun else v for v in vals]
        y = [R[s][v][metric] for v in vals]
        if metric == "pv":
            y = _floor(y, [R[s][v]["arr"] for v in vals])
        series(ax, x, y, s, label=labels.get(s))
    return R


def _points_in_box(ax, box, pad=1.0):
    """Number of data samples (line segments and markers) inside a display-space box."""
    n = 0
    x0, y0, x1, y1 = box.x0 - pad, box.y0 - pad, box.x1 + pad, box.y1 + pad
    for ln in ax.lines:
        if ln.get_gid() == "ref":
            continue
        xy = ln.get_xydata()
        if len(xy) == 0:
            continue
        good = np.all(np.isfinite(xy), axis=1)
        pts = ax.transData.transform(xy[good])
        samples = [pts]
        if ln.get_linestyle() not in ("None", "", " ") and len(pts) > 1:
            t = np.linspace(0, 1, 30)[:, None]
            for a, b in zip(pts[:-1], pts[1:]):
                samples.append(a + t * (b - a))
        allp = np.vstack(samples)
        n += int(np.sum((allp[:, 0] > x0) & (allp[:, 0] < x1) & (allp[:, 1] > y0) & (allp[:, 1] < y1)))
    for col in ax.collections:
        offs = col.get_offsets()
        if len(offs):
            pts = ax.transData.transform(offs)
            n += int(np.sum((pts[:, 0] > x0) & (pts[:, 0] < x1) & (pts[:, 1] > y0) & (pts[:, 1] < y1)))
    for p in ax.patches:
        bb = p.get_window_extent()
        if bb.overlaps(box):
            n += 1
    return n


def auto_legend(ax, locs, ncols=(1,), **kw):
    """Try the candidate locations/column counts in order; keep the first legend that lies inside the
    axes without covering data, otherwise the least bad one (and warn)."""
    fig = ax.figure
    best = None
    for ncol in ncols:
        for loc in locs:
            leg = ax.legend(loc=loc, ncol=ncol, **kw)
            fig.canvas.draw()
            r = fig.canvas.get_renderer()
            lb, ab = leg.get_window_extent(r), ax.get_window_extent(r)
            outside = max(ab.x0 - lb.x0, lb.x1 - ab.x1, ab.y0 - lb.y0, lb.y1 - ab.y1, 0.0)
            hits = _points_in_box(ax, lb)
            score = hits + 1000 * (outside > 0.5)
            if best is None or score < best[0]:
                best = (score, loc, ncol, hits, outside)
            if score == 0:
                return leg, best
    _, loc, ncol, hits, outside = best
    leg = ax.legend(loc=loc, ncol=ncol, **kw)
    return leg, best


def render_row(panels, layout):
    """panels: list of (name, draw_fn, legend_spec). draw_fn(ax) plots the panel; legend_spec is a
    dict(locs=[...], ncols=(...), kw={...}) or None. All panels share canvas and axes box."""
    W, H = SIZES[layout]
    fl, ft, fg = FONTS[layout]
    rc = dict(RC, **{"font.size": fl, "axes.labelsize": fl, "xtick.labelsize": ft, "ytick.labelsize": ft,
                     "legend.fontsize": fg})
    report = []
    with plt.rc_context(rc):
        pad = np.array([0.03, 0.04, 0.025, 0.035])
        m = np.array([0.40, 0.08, 0.30, 0.05])  # provisional margins (in): left, right, bottom, top
        for _ in range(4):  # fixed point: margins that fit the largest tick/label extents of the row
            need = np.zeros(4)
            for name, fn, _spec in panels:
                fig = plt.figure(figsize=(W, H))
                ax = fig.add_axes([m[0] / W, m[2] / H, 1 - (m[0] + m[1]) / W, 1 - (m[2] + m[3]) / H])
                fn(ax)
                fig.canvas.draw()
                r = fig.canvas.get_renderer()
                ab, tb = ax.get_window_extent(r), ax.get_tightbbox(r)
                d = fig.dpi
                need = np.maximum(need, [(ab.x0 - tb.x0) / d, (tb.x1 - ab.x1) / d, (ab.y0 - tb.y0) / d, (tb.y1 - ab.y1) / d])
                plt.close(fig)
            new_m = np.maximum(need, 0) + pad
            if np.max(np.abs(new_m - m)) < 0.004:
                m = new_m
                break
            m = new_m
        for name, fn, spec in panels:
            fig = plt.figure(figsize=(W, H))
            ax = fig.add_axes([m[0] / W, m[2] / H, 1 - (m[0] + m[1]) / W, 1 - (m[2] + m[3]) / H])
            fn(ax)
            info = ""
            if spec is not None:
                leg, best = auto_legend(ax, spec.get("locs", ["best"]), spec.get("ncols", (1,)), **spec.get("kw", {}))
                info = f"legend {best[1]} ncol={best[2]} overlap={best[3]} outside={best[4]:.1f}px"
                if best[3] > 0 or best[4] > 0.5:
                    info = "WARNING " + info
            fig.canvas.draw()
            r = fig.canvas.get_renderer()
            tb = fig.get_tightbbox(r)
            if tb.x0 < -0.01 or tb.y0 < -0.01 or tb.x1 > W + 0.01 or tb.y1 > H + 0.01:
                info += f" WARNING content outside canvas {tb}"
            os.makedirs(FIG, exist_ok=True)
            fig.savefig(os.path.join(FIG, name + ".pdf"))
            fig.savefig(os.path.join(FIG, name + ".png"), dpi=300)
            plt.close(fig)
            report.append(f"{name}: {W:.2f}x{H:.2f} in, axes margins L{m[0]:.2f} R{m[1]:.2f} B{m[2]:.2f} T{m[3]:.2f}; {info}")
    for line in report:
        print(line)


def legend_only(name, schemes, width, ncol, fontsize=6.5):
    """Shared legend row (used only when a legend cannot fit inside the panels)."""
    with plt.rc_context(dict(RC, **{"legend.fontsize": fontsize})):
        fig = plt.figure(figsize=(width, 0.22))
        handles = []
        for s in schemes:
            lab, c, mk, ls = SERIES[s]
            h, = plt.plot([], [], linestyle=ls, marker=mk, color=PALETTE[c], markerfacecolor="white", label=lab)
            handles.append(h)
        fig.legend(handles=handles, loc="center", ncol=ncol, frameon=False, handlelength=2.2, columnspacing=1.0)
        fig.savefig(os.path.join(FIG, name + ".pdf")); fig.savefig(os.path.join(FIG, name + ".png"), dpi=300)
        plt.close(fig)


# ------------------------------------------------------------------ figures
KEY6 = ["TLA-SWAN", "SWAN-MLWDF", "SWAN-MW", "SWAN-RATEMAX", "SWAN-EDF", "SWAN-SA"]
MAIN5 = ["TLA-SWAN", "SWAN-MLWDF", "SWAN-MW", "SWAN-EDF", "SWAN-SR"]


def fig2():
    def a(ax):
        sweep(ax, "key", KEY6, metric="mean_delay")
        for ln in ax.lines:  # slots -> ms
            ln.set_ydata(np.asarray(ln.get_ydata()) * 0.1)
        ax.relim(); ax.autoscale()
        ax.set_xlabel("Peak arrival rate $h$ (packets/slot)"); ax.set_ylabel("Mean delay (ms)")
        ax.set_xticks([1.5, 2, 2.5, 3, 3.5, 4])
    def b(ax):
        sweep(ax, "key", KEY6)
        ax.axhline(1e-5, color="0.35", lw=0.6, ls="--", gid="ref")
        ax.set_yscale("log"); ax.set_ylim(5e-7, 0.6)
        ax.set_xlabel("Peak arrival rate $h$ (packets/slot)"); ax.set_ylabel(PR)
        ax.set_xticks([1.5, 2, 2.5, 3, 3.5, 4])
    render_row([("p2a", a, dict(locs=["upper left", "center left"])),
                ("p2b", b, dict(locs=["lower right", "center right"]))], "w2")


def fig3(Ts=1e-4):
    order = ["TLA-SWAN", "SWAN-MLWDF", "SWAN-MW", "SWAN-EDF", "SWAN-SR", "SWAN-fixed", "PASS-1WG", "Fixed-array"]
    def a(ax):
        R = load("ccdf")
        for s in order:
            st = R[s][None]
            d = np.arange(st["ccdf"].size) * Ts * 1e3
            lab, c, mk, ls = SERIES[s]
            ax.plot(d[1:], np.maximum(st["ccdf"][1:], 0.5 / st["arr"]), linestyle=ls, marker=mk, markevery=4,
                    color=PALETTE[c], markerfacecolor="white", label=lab)
        ax.axvline(1.0, color="0.35", lw=0.6, ls="--", gid="ref")
        ax.text(1.05, 0.93, r"$D_{\max}$", transform=ax.get_xaxis_transform(), fontsize=7, color="0.25", va="center")
        ax.set_yscale("log"); ax.set_xlim(0, 4.0); ax.set_ylim(1e-8, 1.5)
        ax.set_xlabel("Delay threshold $d$ (ms)"); ax.set_ylabel(r"$\Pr\{D>d\}$")
    render_row([("p3", a, dict(locs=["lower left", "upper right", "lower center"]))], "col")


def fig4():
    def a(ax):
        sweep(ax, "peak", MAIN5 + ["SWAN-fixed", "PASS-1WG"])
        ax.set_yscale("log"); ax.set_ylim(3e-7, 0.4); ax.set_xticks([2, 2.5, 3, 3.5, 4])
        ax.set_xlabel("Peak arrival rate $h$ (packets/slot)"); ax.set_ylabel(PR)
    def b(ax):
        sweep(ax, "burst", MAIN5, xfun=lambda al: 1e3 / al)
        ax.set_xscale("log"); ax.set_yscale("log"); ax.set_ylim(3e-7, 0.4)
        ax.set_xticks([0.25, 0.5, 1, 2, 4]); ax.set_xticklabels(["0.25", "0.5", "1", "2", "4"]); ax.minorticks_off()
        ax.set_xlabel(r"Mean burst duration $1/\alpha$ (ms)"); ax.set_ylabel(PR)
    def c(ax):
        sweep(ax, "dmax", MAIN5, xfun=lambda v: 0.1 * v)
        ax.set_yscale("log"); ax.set_ylim(3e-7, 0.4)
        ax.set_xlabel(r"Latency budget $D_{\max}$ (ms)"); ax.set_ylabel(PR)
    spec = dict(locs=["lower right", "lower left", "center right", "upper left"], ncols=(1, 2))
    render_row([("p4a", a, spec), ("p4b", b, spec), ("p4c", c, spec)], "w3")


def fig5():
    short = {"TLA-SWAN": "TLA-SWAN"}
    def a(ax):
        sweep(ax, "power", MAIN5 + ["Fixed-array"], labels=short)
        ax.set_yscale("log"); ax.set_ylim(1e-8, 1.0); ax.set_xticks([-20, -15, -10, -5, 0])
        ax.set_xlabel(r"Per-segment power $P_{\max}$ (dBm)"); ax.set_ylabel(PR)
    def b(ax):
        # conventional PASS is labelled directly on its curve so that the legend fits below the data
        sweep(ax, "segments", MAIN5 + ["PASS-1WG"], labels=dict(short, **{"PASS-1WG": "_nolegend_"}))
        ax.text(7.2, 3.2e-2, "Conventional PASS", fontsize=6.3, ha="center", va="bottom", color="0.1")
        ax.set_yscale("log"); ax.set_ylim(1e-8, 1.0); ax.set_xticks([2, 4, 6, 8, 10])
        ax.set_xlabel("Number of segments $M$"); ax.set_ylabel(PR)
    def c(ax):
        sweep(ax, "tau", ["TLA-SWAN", "SWAN-fixed", "SWAN-reactive"], labels=short)
        ax.set_yscale("log"); ax.set_ylim(7e-4, 0.2); ax.set_xticks([0, 2, 4, 6, 8, 10])
        ax.set_xlabel(r"PA repositioning delay $\tau_r$ (slots)"); ax.set_ylabel(PR)
    spec = dict(locs=["lower left", "lower right", "center left", "upper right"], ncols=(1, 2), kw=dict(handlelength=1.7))
    render_row([("p5a", a, spec), ("p5b", b, spec),
                ("p5c", c, dict(locs=["upper left", "center left", "lower right"], kw=dict(handlelength=1.7)))], "w3")


def fig6():
    def a(ax):
        R = _merge(load("energy"), load("energy2")) if os.path.isdir(os.path.join(RESULTS, "energy2")) else load("energy")
        for s in ["TLA-SWAN", "SWAN-MW", "SWAN-RATEMAX"]:
            vals = sorted(R[s].keys())
            series(ax, [R[s][v]["power_mW"] for v in vals], _floor([R[s][v]["pv"] for v in vals], [R[s][v]["arr"] for v in vals]), s,
                   label=SERIES[s][0].replace(" (proposed)", ""))
        ax.set_yscale("log"); ax.set_xlabel("Average power (mW)"); ax.set_ylabel(PR)
    def b(ax):
        R = load("energy")["TLA-SWAN"]
        mh = R[0.3]["mode_hist"]; tot = mh.sum(axis=0)
        mask = (tot > 200) & (np.arange(mh.shape[1]) >= 1)
        q = np.arange(mh.shape[1])[mask]
        names = [None, "SS ($j=1$)", "SA ($1<j<M$)", "SA ($j=M$)", "SM"]
        styles = [None, (1, "s", "-"), (2, "^", "--"), (3, "v", ":"), (4, "D", "-.")]
        for i in range(1, 5):
            c, mk, ls = styles[i]
            ax.plot(q, mh[i][mask] / tot[mask], linestyle=ls, marker=mk, markevery=4, color=PALETTE[c],
                    markerfacecolor="white", label=names[i])
        ax.set_ylim(-0.02, 1.02); ax.set_xlabel("Total backlog (packets)"); ax.set_ylabel("Mode probability")
    def c(ax):
        R = _merge(load("cost"), load("cost2")) if os.path.isdir(os.path.join(RESULTS, "cost2")) else load("cost")
        targets = [1e-3, 1e-4, 1e-5, 1e-6]
        for s in ["TLA-SWAN", "SWAN-MW", "SWAN-RATEMAX"]:
            pts = []
            for dlt in targets:
                feas = [v for v in R[s] if R[s][v]["pv"] <= dlt]
                pts.append(min(R[s][v]["power_mW"] for v in feas) if feas else np.nan)
            series(ax, [-np.log10(dlt) for dlt in targets], pts, s, label=SERIES[s][0].replace(" (proposed)", ""))
        ax.set_xticks([3, 4, 5, 6]); ax.set_xlim(2.7, 6.3); ax.set_ylim(55, 125)
        ax.set_xlabel(r"Target $-\log_{10}\delta$"); ax.set_ylabel("Minimum power (mW)")
    def d(ax):
        R = load("cfg")
        for s in ["TLA-SWAN-cfg", "TLA-SWAN-cfg-warm", "SWAN-FULL-cfg"]:
            vals = sorted(R[s].keys())
            lab = {"TLA-SWAN-cfg": "TLA-SWAN", "TLA-SWAN-cfg-warm": "Keep-warm", "SWAN-FULL-cfg": "Full activation"}[s]
            series(ax, vals, _floor([R[s][v]["pv"] for v in vals], [R[s][v]["arr"] for v in vals]), s, label=lab)
        ax.set_yscale("log"); ax.set_ylim(4e-4, 0.3); ax.set_xticks([0, 1, 2, 3, 4])
        ax.set_xlabel(r"Activation delay $\tau_{\rm cfg}$ (slots)"); ax.set_ylabel(PR)
    render_row([("p6a", a, dict(locs=["upper right", "center right", "lower left"])),
                ("p6b", b, dict(locs=["center left", "center right", "upper center"])),
                ("p6c", c, dict(locs=["upper right", "center right", "upper left"])),
                ("p6d", d, dict(locs=["upper left", "center left", "lower right"]))], "w4")


def fig7():
    def a(ax):
        R = load("fixedj")
        for s in ["SWAN-FIXJ-onoff", "SWAN-FIXJ-poisson"]:
            vals = sorted(R[s].keys())
            series(ax, vals, _floor([R[s][v]["pv"] for v in vals], [R[s][v]["arr"] for v in vals]), s)
        ax.set_yscale("log"); ax.set_ylim(3e-7, 0.6); ax.set_xticks([1, 2, 3, 4])
        ax.set_xlabel("Aggregation depth $j$ (TDMA)"); ax.set_ylabel(PR)
    pts, approx = [], {}
    for fn in glob.glob(os.path.join(RESULTS, "single", "SINGLE-SA__*.json")):
        r = json.load(open(fn)); cfg = r["cfg"]
        snr = 10 ** (r["snr_agg_dB"][0] / 10)
        ap = single_user_fixed_sa(cfg["h"], cfg["alpha"], cfg["beta"], cfg["Ts"], snr, cfg["n"], cfg["L"], cfg["bmax"], cfg["Dmax_slots"])
        approx.setdefault(cfg["h"], []).append(ap["pv_approx"])
        arr = max(sum(r["arrivals"]), 1)
        pts.append((ap["pv_approx"], sum(r["viol"]) / arr, 1.0 / arr, cfg["h"]))
    def b(ax):
        R = load("single")["SINGLE-SA"]
        vals = sorted(R.keys())
        series(ax, vals, _floor([R[v]["pv"] for v in vals], [R[v]["arr"] for v in vals]), "SINGLE-SA")
        hs = sorted(approx)
        ax.plot(hs, [np.mean(approx[h]) for h in hs], color="k", ls="-.", lw=0.9, label="EB/EC approximation")
        ax.set_yscale("log"); ax.set_ylim(1e-7, 1); ax.set_xticks([3, 3.5, 4, 4.5, 5, 5.5])
        ax.set_xlabel("Peak arrival rate $h$ (packets/slot)"); ax.set_ylabel(PR)
    def c(ax):
        hs_all = sorted({p[3] for p in pts})
        for i, h in enumerate(hs_all):
            xs = [p[0] for p in pts if p[3] == h]; ys = [max(p[1], p[2]) for p in pts if p[3] == h]
            obs = [p[1] > 0 for p in pts if p[3] == h]
            mk = "osv^D*"[i % 6]
            ax.plot([x for x, o in zip(xs, obs) if o], [y for y, o in zip(ys, obs) if o], ls="none", marker=mk, ms=3.6,
                    color=PALETTE[i % 8], label=f"$h={h:g}$")
            ax.plot([x for x, o in zip(xs, obs) if not o], [y for y, o in zip(ys, obs) if not o], ls="none", marker=mk, ms=3.6,
                    color=PALETTE[i % 8], markerfacecolor="white")
        lim = [1e-7, 1]
        ax.plot(lim, lim, "k--", lw=0.6, gid="ref")
        ax.plot(lim, [3 * v for v in lim], color="0.6", lw=0.5, ls=":", gid="ref")
        ax.plot(lim, [v / 3 for v in lim], color="0.6", lw=0.5, ls=":", gid="ref")
        ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(1e-7, 1); ax.set_ylim(1e-7, 1)
        ax.set_xticks([1e-7, 1e-5, 1e-3, 1e-1]); ax.set_yticks([1e-7, 1e-5, 1e-3, 1e-1])
        ax.set_xlabel("Approximation"); ax.set_ylabel("Simulation")
    render_row([("p7a", a, dict(locs=["center right", "lower left", "lower right"])),
                ("p7b", b, dict(locs=["lower right", "upper left"])),
                ("p7c", c, dict(locs=["upper left", "lower right"], ncols=(2, 3), kw=dict(handlelength=1.0, columnspacing=0.6)))], "w3")


def fig8():
    order = ["tapp", "tapp1", "tappM", "tappmm", "sumrate", "maxmin", "center"]
    labels = ["TAPP\n($j_0=2$)", "TAPP\n($j_0=1$)", "TAPP\n($j_0=M$)", "Weighted\nmax-min", "Sum-rate", "Max-min\nrate", "Segment\ncentres"]
    def a(ax):
        exp = "hetero16" if os.path.isdir(os.path.join(RESULTS, "hetero16")) else "hetero"
        R = load(exp)["TLA-SWAN"]
        keep = [i for i, p in enumerate(order) if p in R]
        o = [order[i] for i in keep]; lab = [labels[i] for i in keep]
        crit = _floor([R[p]["pv_crit"] for p in o], [R[p]["arr"] for p in o])
        reg = _floor([R[p]["pv_reg"] for p in o], [R[p]["arr"] for p in o])
        x = np.arange(len(o)); w = 0.38
        ax.bar(x - w / 2, crit, w, color=PALETTE[0], edgecolor="white", lw=0.3, label=r"Critical users ($\delta=10^{-6}$)")
        ax.bar(x + w / 2, reg, w, color=PALETTE[1], edgecolor="white", lw=0.3, hatch="////", label=r"Regular users ($\delta=10^{-5}$)")
        ax.set_yscale("log"); ax.set_ylim(1e-3, 3e-2)
        from matplotlib.ticker import FixedLocator, NullFormatter
        ax.yaxis.set_major_locator(FixedLocator([1e-3, 1e-2])); ax.yaxis.set_minor_formatter(NullFormatter())
        ax.set_xticks(x); ax.set_xticklabels(lab); ax.tick_params(axis="x", which="both", length=0, labelsize=6.3)
        ax.grid(axis="x", visible=False)
        ax.set_ylabel(PR)
    render_row([("p8", a, dict(locs=["upper left", "upper center", "upper right"], ncols=(2, 1)))], "colbar")


ALL = {"2": fig2, "3": fig3, "4": fig4, "5": fig5, "6": fig6, "7": fig7, "8": fig8}

if __name__ == "__main__":
    which = sys.argv[1:] or list(ALL)
    for k in which:
        print(f"--- Fig. {k}")
        ALL[k]()
