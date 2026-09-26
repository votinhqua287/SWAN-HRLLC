"""Figures of the manuscript (paper/main.tex), built with the ``ieee-figures`` plugin.

The plugin lives in ``claude-ieee-figures/plugins/ieee-figures`` (vendored copy of the
``ieee-paper-tools`` marketplace); its ``ieeefig`` module sets the house style once and
re-checks it (rule 7b) before anything is written:
  * one markered line per scheme, straight segments, no error bars or bands;
  * ``xlim`` is exactly the first and last swept value and ``xticks`` are exactly the swept
    values (log-spaced sweeps get their labels through ``tick_labels``; a sweep that contains
    0 and spans decades is drawn at equally spaced positions, again labelled with the values);
  * IEEE column geometry, Okabe-Ito colours plus a distinct marker and line style per scheme,
    a hatch channel on bars, vector PDF with Type-42 fonts.
On top of the plugin, this script applies the manuscript rules of
.claude/skills/ieee-paper-writing/SKILL.md section 5: Times New Roman (passed through
``FigureStyle``, math in the same face), one PDF per figure with only "(a)", "(b)", ... under
the x-labels, box on and grid on, legends inside the axes and checked for overlap, and the
printed size decided here (LaTeX includes the PDFs without ``width=``).

Usage:  python -m experiments.paper_figs              (all figures)
        python -m experiments.paper_figs key phy      (selected figures)
"""
import os, sys, json, glob
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.ticker import FixedLocator, NullFormatter, NullLocator

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PLUGIN = os.path.join(ROOT, "claude-ieee-figures", "plugins", "ieee-figures")
sys.path.insert(0, os.path.join(PLUGIN, "ieeefig"))
import ieeefig as ief  # noqa: E402

from experiments.run_campaign import load, RESULTS  # noqa: E402
from src.tail_analysis import single_user_fixed_sa  # noqa: E402

FIG = os.path.join(ROOT, "paper", "figures")
TS_MS = 0.1  # slot duration in ms

STYLE = ief.FigureStyle(font_size=8, font_family=("Times New Roman", "Times", "DejaVu Serif", "serif"), grid=True)


def apply_style():
    """Plugin style plus the manuscript rules: Times New Roman (math included), box on, grid on."""
    ief.apply_publication_style(STYLE)
    mpl.rcParams.update({
        # box on: all four spines, ticks mirrored on the top and right sides; grid on: light major grid
        "axes.spines.top": True, "axes.spines.right": True, "xtick.top": True, "ytick.right": True,
        "grid.linewidth": 0.3, "grid.alpha": 0.5, "grid.color": "0.65",
        "font.family": "serif", "font.serif": list(STYLE.font_family),
        "mathtext.fontset": "custom", "mathtext.rm": "Times New Roman",
        "mathtext.it": "Times New Roman:italic", "mathtext.bf": "Times New Roman:bold",
        "mathtext.sf": "Times New Roman", "mathtext.tt": "Times New Roman",
        "mathtext.cal": "Times New Roman:italic", "mathtext.fallback": "stix",
        "legend.handlelength": 2.0, "legend.handletextpad": 0.5, "legend.labelspacing": 0.25,
        "legend.borderaxespad": 0.3, "legend.columnspacing": 0.9,
    })


P = ief.PALETTE
LS = ief.DEFAULT_LINESTYLES
# scheme -> (legend label, colour, marker, line style); fixed per scheme, distinct within every figure
SERIES = {
    "TLA-SWAN":          ("TLA-SWAN", P["blue_main"], "o", LS[0]),
    "SWAN-MLWDF":        ("M-LWDF", P["vermillion"], "s", LS[1]),
    "SWAN-MW":           ("Max-weight", P["green"], "^", LS[2]),
    "SWAN-EDF":          ("EDF", P["orange"], "v", LS[3]),
    "SWAN-SR":           ("Sum-rate + MW", P["purple"], "D", LS[4]),
    "SWAN-fixed":        ("Fixed PAs", P["blue_secondary"], "x", LS[5]),
    "PASS-1WG":          ("Conventional PASS", P["black"], "P", LS[6]),
    "Fixed-array":       ("Fixed array", P["neutral"], "*", LS[7]),
    "SWAN-RATEMAX":      ("Rate-max", P["purple"], "D", LS[4]),
    "SWAN-SA":           ("Fixed SA (TDMA)", P["black"], "P", LS[6]),
    "SWAN-reactive":     ("Reactive repositioning", P["green"], "^", LS[2]),
    "TLA-SWAN-cfg":      ("TLA-SWAN", P["blue_main"], "o", LS[0]),
    "TLA-SWAN-cfg-warm": ("Keep-warm", P["vermillion"], "s", LS[1]),
    "SWAN-FULL-cfg":     ("Full activation", P["black"], "P", LS[6]),
    "SWAN-FIXJ-onoff":   ("ON–OFF arrivals", P["blue_main"], "o", LS[0]),
    "SWAN-FIXJ-poisson": ("Poisson arrivals", P["vermillion"], "s", LS[1]),
    "SINGLE-SA":         ("Simulation", P["blue_main"], "o", LS[0]),
}
PR = r"$\Pr\{D>D_{\max}\}$"
H_LABEL = "Peak arrival rate $h$ (packets/slot)"
KEY6 = ["TLA-SWAN", "SWAN-MLWDF", "SWAN-MW", "SWAN-RATEMAX", "SWAN-EDF", "SWAN-SA"]
MAIN5 = ["TLA-SWAN", "SWAN-MLWDF", "SWAN-MW", "SWAN-EDF", "SWAN-SR"]


# ------------------------------------------------------------------ data helpers
def _floor(y, arr):
    """Zero-violation points are drawn at the resolution floor 1/(packets observed)."""
    y = np.asarray(y, float)
    return np.where(y > 0, y, 1.0 / np.maximum(np.asarray(arr, float), 1))


def _merge(a, b):
    out = {k: dict(v) for k, v in a.items()}
    for k, v in b.items():
        out.setdefault(k, {}).update(v)
    return out


def _load2(exp, exp2):
    return _merge(load(exp), load(exp2)) if os.path.isdir(os.path.join(RESULTS, exp2)) else load(exp)


def sweep_xy(R, schemes, metric="pv", xfun=None, scale=1.0):
    """Swept values (sorted, common to all schemes) and one y array per scheme."""
    x, ys = None, []
    for s in schemes:
        vals = sorted(R[s].keys())
        xv = np.array([xfun(v) if xfun else v for v in vals], float)
        order = np.argsort(xv)
        xv = xv[order]
        y = np.array([R[s][vals[i]][metric] for i in order], float) * scale
        if metric == "pv":
            y = _floor(y, [R[s][vals[i]]["arr"] for i in order])
        if x is None:
            x = xv
        elif not np.allclose(x, xv):
            raise ValueError(f"{s}: swept values {xv} differ from {x}")
        ys.append(y)
    return x, ys


def _styles(schemes, labels=None):
    labels = labels or {}
    labs, cols, mks, lss = [], [], [], []
    for s in schemes:
        lab, c, m, ls = SERIES[s]
        labs.append(labels.get(s, lab)); cols.append(c); mks.append(m); lss.append(ls)
    return labs, cols, mks, lss


def trend(ax, R, schemes, metric="pv", xfun=None, scale=1.0, labels=None, logx=False, ordinal=False,
          fmt="{:g}", **kw):
    """Sweep panel through ``ief.make_trend`` with the per-scheme styles.

    ``logx``: log-spaced sweep, ticks stay at the swept values and are labelled with ``fmt``.
    ``ordinal``: swept values drawn at equally spaced positions (used when the sweep contains 0
    and spans decades, so the values cannot be labelled at their metric positions).
    """
    x, ys = sweep_xy(R, schemes, metric, xfun, scale)
    labs, cols, mks, lss = _styles(schemes, labels)
    tick_labels = None
    xp = x
    if ordinal:
        xp = np.arange(x.size, dtype=float)
        tick_labels = [fmt.format(v) for v in x]
    elif logx:
        ax.set_xscale("log")
        tick_labels = [fmt.format(v) for v in x]
    ief.make_trend(ax, xp, ys, labs, colors=cols, markers=mks, linestyles=lss, tick_labels=tick_labels,
                   legend=False, **kw)
    if logx:
        ax.xaxis.set_minor_locator(NullLocator())
    return x


def curve(ax, x, y, scheme=None, label=None, color=None, marker=None, ls=None, markevery=None):
    """A non-sweep curve (CCDF, mode probability) drawn with the same encoding as make_trend."""
    if scheme is not None:
        lab, c, m, l = SERIES[scheme]
        label, color, marker, ls = (label or lab), c, m, l
    ax.plot(x, y, label=label, color=color, marker=marker, linestyle=ls, markevery=markevery,
            markerfacecolor="none", markeredgewidth=0.9, zorder=3)


# ------------------------------------------------------------------ legend placement
def _points_in_box(ax, box, pad=1.0):
    """Number of data samples (line segments, markers, bars) inside a display-space box."""
    n = 0
    x0, y0, x1, y1 = box.x0 - pad, box.y0 - pad, box.x1 + pad, box.y1 + pad
    for ln in ax.lines:
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
        if p.get_window_extent().overlaps(box):
            n += 1
    return n


def legend(ax, locs=("best",), ncols=(1,), **kw):
    """Legend inside the axes: first candidate (location, columns) that covers no data and stays
    inside the axes box, otherwise the least bad one (reported as a WARNING)."""
    fig = ax.figure
    kw = dict({"frameon": True, "facecolor": "white", "edgecolor": "none", "framealpha": 1.0}, **kw)
    best = None
    for ncol in ncols:
        for loc in locs:
            leg = ax.legend(loc=loc, ncol=ncol, **kw)
            fig.canvas.draw()
            r = fig.canvas.get_renderer()
            lb, ab = leg.get_window_extent(r), ax.get_window_extent(r)
            outside = max(ab.x0 - lb.x0, lb.x1 - ab.x1, ab.y0 - lb.y0, lb.y1 - ab.y1, 0.0)
            hits = _points_in_box(ax, lb)
            score = hits + 1000 * (outside > 2.0)
            if best is None or score < best[0]:
                best = (score, loc, ncol, hits, outside)
            if score == 0:
                ax._legend_report = f"legend {loc} ncol={ncol}"
                return leg
    _, loc, ncol, hits, outside = best
    ax.legend(loc=loc, ncol=ncol, **kw)
    ax._legend_report = f"WARNING legend {loc} ncol={ncol} overlap={hits} outside={outside:.1f}px"


def shared_legend(fig, schemes, labels=None, ncol=None):
    """One legend row above the panels (used only when a legend cannot fit inside the panels)."""
    from matplotlib.lines import Line2D
    handles = []
    for s in schemes:
        lab, c, m, ls = SERIES[s]
        handles.append(Line2D([], [], color=c, marker=m, linestyle=ls, markerfacecolor="none",
                              markeredgewidth=0.9, label=(labels or {}).get(s, lab)))
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=ncol or len(handles),
               frameon=False, borderaxespad=0.0, handlelength=2.0, columnspacing=1.2)


# ------------------------------------------------------------------ figure assembly
def finish(fig, axes, panel_labels=True):
    """Common margins for the row, then "(a)", "(b)", ... centred right under each x-label."""
    fig.tight_layout(pad=0.3, w_pad=1.0)
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    if panel_labels and len(axes) > 1:
        y = min((ax.xaxis.label.get_window_extent(r).y0 - ax.get_window_extent(r).y0) / ax.get_window_extent(r).height
                for ax in axes)
        ief.add_panel_labels(fig, axes, y=y - 0.015)
    # make_trend draws unclipped markers: every plotted point must lie inside the y-limits
    for i, ax in enumerate(axes):
        lo, hi = ax.get_ylim()
        for ln in ax.lines:
            if ln.get_clip_on():
                continue
            yd = np.asarray(ln.get_ydata(), float)
            yd = yd[np.isfinite(yd)]
            if yd.size and (yd.min() < min(lo, hi) or yd.max() > max(lo, hi)):
                print(f"WARNING axes[{i}]: data ({yd.min():.3g}, {yd.max():.3g}) outside ylim ({lo:.3g}, {hi:.3g})")
    return fig


# ------------------------------------------------------------------ figures
def build_key():
    """Fig. 2: mean delay and delay-violation probability versus the peak arrival rate."""
    fig, axes = ief.create_subplots(1, 2, column="double", height=1.85)
    R = load("key")
    x = trend(axes[0], R, KEY6, metric="mean_delay", scale=TS_MS, xlabel=H_LABEL, ylabel="Mean delay (ms)")
    trend(axes[1], R, KEY6, xlabel=H_LABEL, ylabel=PR, yscale="log")
    axes[1].set_ylim(5e-7, 0.6)
    axes[1].hlines(1e-5, x[0], x[-1], colors="0.35", lw=0.6, ls="--", zorder=1)  # target delta
    legend(axes[0], ["upper left", "center left"])
    legend(axes[1], ["lower right", "center right"])
    return finish(fig, axes)


def build_ccdf():
    """Fig. 3: complementary CDF of the packet delay (delay axis continuous by design)."""
    order = ["TLA-SWAN", "SWAN-MLWDF", "SWAN-MW", "SWAN-EDF", "SWAN-SR", "SWAN-fixed", "PASS-1WG", "Fixed-array"]
    fig, axes = ief.create_subplots(1, 1, column="single", height=2.1)
    ax = axes[0]
    R = load("ccdf")
    d = None
    for s in order:
        st = R[s][None]
        d = np.arange(st["ccdf"].size) * TS_MS
        curve(ax, d, np.maximum(st["ccdf"], 0.5 / st["arr"]), scheme=s, markevery=4)
    ax.set_yscale("log")
    ax.set_xlim(d[0], d[-1]); ax.set_ylim(1e-8, 1.5)
    ax.set_xticks([0, 1, 2, 3, 4])
    ax.vlines(1.0, 1e-8, 1.5, colors="0.35", lw=0.6, ls="--", zorder=1)
    ax.text(1.06, 0.93, r"$D_{\max}$", transform=ax.get_xaxis_transform(), fontsize=7, color="0.25", va="center")
    ax.set_xlabel("Delay threshold $d$ (ms)"); ax.set_ylabel(r"$\Pr\{D>d\}$")
    legend(ax, ["lower left", "lower center", "center left", "upper right"], ncols=(1, 2))
    return finish(fig, axes)


def build_traffic():
    """Fig. 4: delay-violation probability versus h, the mean burst duration, and D_max."""
    fig, axes = ief.create_subplots(1, 3, column="double", height=1.7)
    trend(axes[0], load("peak"), MAIN5 + ["SWAN-fixed", "PASS-1WG"], xlabel=H_LABEL, ylabel=PR, yscale="log")
    trend(axes[1], load("burst"), MAIN5, xfun=lambda al: 1e3 / al, logx=True,
          xlabel=r"Mean burst duration $1/\alpha$ (ms)", ylabel=PR, yscale="log")
    trend(axes[2], load("dmax"), MAIN5, xfun=lambda v: TS_MS * v, logx=True,
          xlabel=r"Latency budget $D_{\max}$ (ms)", ylabel=PR, yscale="log")
    for ax in axes:
        ax.set_ylim(3e-7, 0.4)
    shared_legend(fig, MAIN5 + ["SWAN-fixed", "PASS-1WG"])
    return finish(fig, axes)


def build_phy():
    """Fig. 5: delay-violation probability versus P_max, M and the repositioning delay."""
    fig, axes = ief.create_subplots(1, 3, column="double", height=1.7)
    trend(axes[0], load("power"), MAIN5 + ["Fixed-array"], xlabel=r"Per-segment power $P_{\max}$ (dBm)",
          ylabel=PR, yscale="log")
    trend(axes[1], load("segments"), MAIN5 + ["PASS-1WG"], xlabel="Number of segments $M$", ylabel=PR, yscale="log")
    trend(axes[2], load("tau"), ["TLA-SWAN", "SWAN-fixed", "SWAN-reactive"],
          xlabel=r"PA repositioning delay $\tau_r$ (slots)", ylabel=PR, yscale="log")
    axes[0].set_ylim(1e-8, 1.0); axes[1].set_ylim(1e-8, 1.0); axes[2].set_ylim(7e-4, 0.2)
    shared_legend(fig, MAIN5 + ["Fixed-array", "PASS-1WG"])
    legend(axes[2], ["upper left", "center left", "lower right"])
    return finish(fig, axes)


def build_energy():
    """Fig. 6: energy-aware operation (trade-off, mode probabilities, target cost, activation delay)."""
    fig, axes = ief.create_subplots(1, 4, column="double", height=1.62)
    # (a) operating points of the energy weight sweep: x is measured power, not a swept value, so the
    # points are markers (make_scatter encoding) joined by thin segments in the order of V
    ax = axes[0]
    R = _load2("energy", "energy2")
    ax.set_yscale("log")
    for s in ["TLA-SWAN", "SWAN-MW", "SWAN-RATEMAX"]:
        vals = sorted(R[s].keys())
        x = np.array([R[s][v]["power_mW"] for v in vals])
        y = _floor([R[s][v]["pv"] for v in vals], [R[s][v]["arr"] for v in vals])
        lab, c, m, ls = SERIES[s]
        ax.add_collection(LineCollection([np.column_stack([x, y])], colors=[c], linewidths=0.8, linestyles=[ls], zorder=2))
        ax.scatter(x, y, s=16, marker=m, facecolors="none", edgecolors=c, linewidths=0.9, label=lab, zorder=3)
    ax.autoscale_view()
    ax.set_xlabel("Average power (mW)"); ax.set_ylabel(PR)
    # (b) mode probability versus the backlog level (continuous by design)
    ax = axes[1]
    mh = load("energy")["TLA-SWAN"][0.3]["mode_hist"]
    tot = mh.sum(axis=0)
    mask = (tot > 200) & (np.arange(mh.shape[1]) >= 1)
    q = np.arange(mh.shape[1])[mask]
    names = {1: "SS ($j{=}1$)", 2: "SA ($1{<}j{<}M$)", 3: "SA ($j{=}M$)", 4: "SM"}
    for k, (i, c, m, ls) in enumerate([(1, P["vermillion"], "s", LS[1]), (2, P["green"], "^", LS[2]),
                                        (3, P["orange"], "v", LS[3]), (4, P["purple"], "D", LS[4])]):
        curve(ax, q, mh[i][mask] / tot[mask], label=names[i], color=c, marker=m, ls=ls, markevery=4)
    ax.set_xlim(q[0], q[-1]); ax.set_ylim(-0.02, 1.36)  # head-room for the two-row legend
    ax.set_xticks([q[0], 10, 20, 30, q[-1]]); ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_xlabel("Total backlog (packets)"); ax.set_ylabel("Mode probability")
    # (c) minimum average power that meets a target delta (evaluated targets are the sweep)
    ax = axes[2]
    R = _load2("cost", "cost2")
    targets = [1e-3, 1e-4, 1e-5, 1e-6]
    schemes = ["TLA-SWAN", "SWAN-MW", "SWAN-RATEMAX"]
    ys = []
    for s in schemes:
        pts = []
        for dlt in targets:
            feas = [v for v in R[s] if R[s][v]["pv"] <= dlt]
            pts.append(min(R[s][v]["power_mW"] for v in feas) if feas else np.nan)
        ys.append(pts)
    labs, cols, mks, lss = _styles(schemes)
    ief.make_trend(ax, [-np.log10(t) for t in targets], ys, labs, colors=cols, markers=mks, linestyles=lss,
                   xlabel=r"Target $-\log_{10}\delta$", ylabel="Minimum power (mW)", legend=False)
    ax.set_ylim(55, 145)  # head-room for the legend
    # (d) activation delay: the sweep {0, 0.25, 0.5, 1, 2, 4} contains 0 and spans decades
    trend(axes[3], load("cfg"), ["TLA-SWAN-cfg", "TLA-SWAN-cfg-warm", "SWAN-FULL-cfg"], ordinal=True,
          xlabel=r"Activation delay $\tau_{\rm cfg}$ (slots)", ylabel=PR, yscale="log")
    axes[3].set_ylim(4e-4, 0.3)
    legend(axes[0], ["upper right", "center right", "lower left"])
    legend(axes[1], ["upper center", "upper right"], ncols=(2,), handlelength=0.9, columnspacing=0.3,
           handletextpad=0.25, borderpad=0.15, borderaxespad=0.0)
    legend(axes[2], ["upper right", "upper center", "upper left"])
    legend(axes[3], ["upper left", "center left", "lower right"])
    return finish(fig, axes)


def _single_points():
    pts, approx = [], {}
    for fn in sorted(glob.glob(os.path.join(RESULTS, "single", "SINGLE-SA__*.json"))):
        r = json.load(open(fn)); cfg = r["cfg"]
        snr = 10 ** (r["snr_agg_dB"][0] / 10)
        ap = single_user_fixed_sa(cfg["h"], cfg["alpha"], cfg["beta"], cfg["Ts"], snr, cfg["n"], cfg["L"],
                                  cfg["bmax"], cfg["Dmax_slots"])
        approx.setdefault(cfg["h"], []).append(ap["pv_approx"])
        arr = max(sum(r["arrivals"]), 1)
        pts.append((ap["pv_approx"], sum(r["viol"]) / arr, 1.0 / arr, cfg["h"]))
    return pts, approx


def build_validation():
    """Fig. 7: fixed aggregation depth, single-device validation of the EB/EC approximation."""
    fig, axes = ief.create_subplots(1, 3, column="double", height=1.7)
    trend(axes[0], load("fixedj"), ["SWAN-FIXJ-onoff", "SWAN-FIXJ-poisson"], xlabel="Aggregation depth $j$ (TDMA)",
          ylabel=PR, yscale="log")
    axes[0].set_ylim(3e-7, 0.6)
    pts, approx = _single_points()
    R = load("single")
    x, ys = sweep_xy(R, ["SINGLE-SA"])
    hs = sorted(approx)
    assert np.allclose(hs, x)
    ys.append([np.mean(approx[h]) for h in hs])
    ief.make_trend(axes[1], x, ys, ["Simulation", "EB/EC approximation"], colors=[P["blue_main"], P["black"]],
                   markers=["o", "None"], linestyles=[LS[0], LS[2]], xlabel=H_LABEL, ylabel=PR, yscale="log", legend=False)
    axes[1].set_ylim(1e-7, 1)
    axes[1].lines[1].set_clip_on(True)  # the approximation falls below 1e-7 at small h (off scale)
    # (c) drop-by-drop comparison: markers only, reference guides as a collection
    ax = axes[2]
    from matplotlib.lines import Line2D
    hs_all = sorted({p[3] for p in pts})
    handles = []
    for i, h in enumerate(hs_all):
        c, m = ief.DEFAULT_COLORS[i % 8], ["o", "s", "^", "v", "D", "P", "*"][i % 7]
        for observed, face in ((True, c), (False, "none")):  # open marker: no violation observed
            sel = [(p[0], max(p[1], p[2])) for p in pts if p[3] == h and (p[1] > 0) == observed]
            if sel:
                xs_, ys_ = zip(*sel)
                ax.scatter(xs_, ys_, s=14, marker=m, facecolors=face, edgecolors=c, linewidths=0.8, zorder=3)
        handles.append(Line2D([], [], ls="none", marker=m, color=c, markersize=3.5, label=f"$h={h:g}$"))
    lim = (1e-7, 1.0)
    ax.add_collection(LineCollection([[(lim[0], lim[0]), (lim[1], lim[1])]], colors="k", linewidths=0.6, linestyles="--"))
    ax.add_collection(LineCollection([[(lim[0], 3 * lim[0]), (lim[1] / 3, lim[1])], [(3 * lim[0], lim[0]), (lim[1], lim[1] / 3)]],
                                     colors="0.6", linewidths=0.5, linestyles=":"))
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(*lim); ax.set_ylim(*lim)
    ax.set_xticks([1e-7, 1e-5, 1e-3, 1e-1]); ax.set_yticks([1e-7, 1e-5, 1e-3, 1e-1])
    ax.set_xlabel("Approximation"); ax.set_ylabel("Simulation")
    legend(axes[0], ["center right", "lower left", "lower right"])
    legend(axes[1], ["lower right", "upper left"])
    legend(axes[2], ["upper left", "lower right"], ncols=(2, 3), handles=handles, handlelength=1.0, columnspacing=0.6)
    return finish(fig, axes)


def build_hetero():
    """Fig. 8: per-class delay-violation probability of the placement rules (grouped bars)."""
    order = ["tapp", "tapp1", "tappM", "tappmm", "sumrate", "maxmin", "center"]
    labels = ["TAPP\n($j_0=2$)", "TAPP\n($j_0=1$)", "TAPP\n($j_0=M$)", "Weighted\nmax-min", "Sum-rate", "Max-min\nrate",
              "Segment\ncentres"]
    fig, axes = ief.create_subplots(1, 1, column="single", height=1.95)
    ax = axes[0]
    exp = "hetero16" if os.path.isdir(os.path.join(RESULTS, "hetero16")) else "hetero"
    R = load(exp)["TLA-SWAN"]
    keep = [i for i, p in enumerate(order) if p in R]
    o = [order[i] for i in keep]; lab = [labels[i] for i in keep]
    crit = _floor([R[p]["pv_crit"] for p in o], [R[p]["arr"] for p in o])
    reg = _floor([R[p]["pv_reg"] for p in o], [R[p]["arr"] for p in o])
    ief.make_grouped_bar(ax, lab, [crit, reg], [r"Critical users ($\delta=10^{-6}$)", r"Regular users ($\delta=10^{-5}$)"],
                         ylabel=PR, colors=[P["blue_main"], P["orange"]], hatches=["", "//"])
    ax.set_yscale("log"); ax.set_ylim(1e-3, 3e-2)
    ax.yaxis.set_major_locator(FixedLocator([1e-3, 1e-2])); ax.yaxis.set_minor_formatter(NullFormatter())
    ax.tick_params(axis="x", which="both", length=0, labelsize=6.5)
    ax.grid(axis="x", visible=False)  # categorical axis: no vertical grid lines
    legend(ax, ["upper left", "upper center", "upper right"], ncols=(2, 1))
    return finish(fig, axes)


# name -> (builder, strict tick audit).  strict=False only where an axis is continuous by design
# (delay threshold in ccdf, backlog level in energy(b)); the sweep panels of those figures still get
# their ticks from make_trend, and tests/test_figures.py checks them.
BUILDERS = {
    "key": (build_key, True),
    "ccdf": (build_ccdf, False),
    "traffic": (build_traffic, True),
    "phy": (build_phy, True),
    "energy": (build_energy, False),
    "validation": (build_validation, True),
    "hetero": (build_hetero, True),
}


def audit(fig, name):
    ief.assert_house_style(fig, strict_ticks=BUILDERS[name][1])


def render(name):
    builder, strict = BUILDERS[name]
    fig = builder()
    audit(fig, name)
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    tb = fig.get_tightbbox(r)
    w, h = tb.width + 0.04, tb.height + 0.04  # + 2 * pad of finalize_figure
    cw, ch = fig.get_size_inches()
    sweeps = []
    for ax in fig.axes:
        lines = [ln for ln in ax.get_lines() if ln.get_xdata().size > 1]
        if lines:
            sweeps.append(f"{lines[0].get_xdata().size} pts")
        rep = getattr(ax, "_legend_report", None)
        if rep:
            sweeps.append(rep)
    out = ief.finalize_figure(fig, os.path.join(FIG, name))
    print(f"{name}: canvas {cw:.2f}x{ch:.2f} in -> PDF {w:.2f}x{h:.2f} in; audit clean "
          f"({'strict' if strict else 'strict_ticks=False'}); {'; '.join(sweeps)}; wrote {out[0].name}")


if __name__ == "__main__":
    apply_style()
    for k in (sys.argv[1:] or list(BUILDERS)):
        render(k)
