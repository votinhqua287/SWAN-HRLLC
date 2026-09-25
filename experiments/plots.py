"""Figure generation for the paper (IEEE single-column style).

Colour: validated categorical palette (fixed slot order); every series also
carries a distinct marker and line style so identity never relies on colour.
"""
import os, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from experiments.run_campaign import load, RESULTS, EXPERIMENTS

FIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "paper", "figures")
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
STYLE = {  # scheme -> (label, colour slot, marker, linestyle)
    "TLA-SWAN":      ("TLA-SWAN (proposed)", 0, "o", "-"),
    "SWAN-MLWDF":    ("SWAN, M-LWDF", 1, "s", "--"),
    "SWAN-MW":       ("SWAN, max-weight", 2, "^", "-."),
    "SWAN-EDF":      ("SWAN, EDF", 3, "v", ":"),
    "SWAN-SR":       ("SWAN, sum-rate + MW", 4, "D", "--"),
    "SWAN-fixed":    ("SWAN, fixed PAs", 5, "x", "-."),
    "SWAN-reactive": ("SWAN, reactive repositioning", 6, "+", ":"),
    "PASS-1WG":      ("Single-waveguide PASS", 7, "*", "--"),
    "Fixed-array":   ("Fixed antenna array", 6, "p", ":"),
    "SWAN-RATEMAX":  ("SWAN, rate-max", 4, "D", "--"),
    "SWAN-SS":       ("SWAN, fixed SS", 5, "x", "-."),
    "SWAN-SA":       ("SWAN, fixed SA (all segments)", 6, "+", ":"),
    "SWAN-FULL":     ("SWAN, full activation", 7, "*", "--"),
    "TLA-SWAN-cfg":  ("TLA-SWAN (energy-aware)", 0, "o", "-"),
    "TLA-SWAN-cfg-warm": ("TLA-SWAN, keep-warm", 1, "s", "--"),
    "SWAN-FULL-cfg": ("SWAN, full activation", 7, "*", ":"),
    "SWAN-FIXJ-onoff":   ("ON--OFF arrivals", 0, "o", "-"),
    "SWAN-FIXJ-poisson": ("Poisson arrivals (same mean)", 1, "s", "--"),
    "SINGLE-SA":     ("fixed SA, simulation", 0, "o", "-"),
    "SINGLE-TLA":    ("TLA-SWAN, simulation", 1, "s", "--"),
}
plt.rcParams.update({
    "font.size": 8, "font.family": "serif", "mathtext.fontset": "cm",
    "axes.labelsize": 8, "legend.fontsize": 6.5, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "lines.linewidth": 1.1, "lines.markersize": 4, "axes.grid": True, "grid.alpha": 0.3,
    "grid.linewidth": 0.4, "axes.linewidth": 0.6, "legend.framealpha": 0.9, "legend.edgecolor": "0.8",
    "figure.dpi": 150, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
})
W, H = 3.45, 2.5


def _save(fig, name):
    os.makedirs(FIG, exist_ok=True)
    fig.savefig(os.path.join(FIG, name + ".pdf"))
    fig.savefig(os.path.join(FIG, name + ".png"), dpi=200)
    plt.close(fig)


def _series(ax, x, y, scheme, **kw):
    lab, c, m, ls = STYLE[scheme]
    ax.plot(x, y, marker=m, linestyle=ls, color=PALETTE[c], label=lab, markerfacecolor="white",
            markeredgewidth=1.0, **kw)


def _floor(y, viol, arr):
    """Report zero-violation points at 1/arrivals (open marker) rather than 0."""
    y = np.array(y, float)
    return np.where(y > 0, y, 1.0 / np.maximum(np.array(arr), 1))


def fig_ccdf(Ts=1e-4):
    R = load("ccdf")
    fig, ax = plt.subplots(figsize=(W, H))
    for s in [k for k in STYLE if k in R]:
        st = R[s][None]
        d = np.arange(st["ccdf"].size) * Ts * 1e3
        y = st["ccdf"]
        ax.semilogy(d[1:], np.maximum(y[1:], 0.5 / st["arr"]), STYLE[s][3], color=PALETTE[STYLE[s][1]],
                    marker=STYLE[s][2], markevery=4, markerfacecolor="white", label=STYLE[s][0])
    ax.axvline(1.0, color="0.4", lw=0.7, ls="--")
    ax.text(1.03, 0.6, r"$D_{\max}$", fontsize=7, color="0.3")
    ax.set_xlabel("Delay threshold $d$ (ms)")
    ax.set_ylabel(r"$\Pr\{D > d\}$")
    ax.set_xlim(0, d[-1])
    ax.legend(ncol=1, loc="lower left")
    _save(fig, "fig_ccdf")


def fig_sweep(exp, xlabel, name, schemes=None, xscale="linear", xfun=None, ylabel=r"Delay-violation probability $\Pr\{D>D_{\max}\}$",
              metric="pv", legend_loc="best", target=None):
    R = load(exp)
    fig, ax = plt.subplots(figsize=(W, H))
    schemes = schemes or [k for k in STYLE if k in R]
    for s in schemes:
        if s not in R:
            continue
        vals = sorted(R[s].keys(), key=lambda v: (v is None, v))
        x = np.array([xfun(v) if xfun else v for v in vals], float)
        y = np.array([R[s][v][metric] for v in vals], float)
        if metric == "pv":
            y = _floor(y, None, [R[s][v]["arr"] for v in vals])
        _series(ax, x, y, s)
    if metric == "pv":
        ax.set_yscale("log")
    if target is not None:
        ax.axhline(target, color="0.4", lw=0.7, ls="--")
        ax.text(ax.get_xlim()[0], target * 1.3, r"target $\delta$", fontsize=7, color="0.3")
    ax.set_xscale(xscale)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend(loc=legend_loc)
    _save(fig, name)


def fig_V():
    R = load("V")["TLA-SWAN"]
    vals = sorted(R.keys())
    pv = _floor([R[v]["pv"] for v in vals], None, [R[v]["arr"] for v in vals])
    pw = [R[v]["power_mW"] for v in vals]
    fig, ax = plt.subplots(figsize=(W, H))
    ax.plot(pw, pv, "o-", color=PALETTE[0], markerfacecolor="white")
    for v, x, y in zip(vals, pw, pv):
        ax.annotate(f"$V={v:g}$", (x, y), textcoords="offset points", xytext=(4, 3), fontsize=6)
    ax.set_yscale("log")
    ax.set_xlabel("Average transmit power (mW)")
    ax.set_ylabel(r"$\Pr\{D>D_{\max}\}$")
    _save(fig, "fig_V")


def fig_hetero():
    R = load("hetero")["TLA-SWAN"]
    order = ["tapp", "tapp1", "tappM", "tappmm", "sumrate", "maxmin", "center"]
    labels = ["TAPP\n($j_0=2$)", "TAPP\n($j_0=1$)", "TAPP\n($j_0=M$)", "weighted\nmax-min", "Sum-rate", "Max-min\nrate", "Segment\ncentres"]
    keep = [i for i, p in enumerate(order) if p in R]
    order = [order[i] for i in keep]; labels = [labels[i] for i in keep]
    crit = [R[p]["pv_crit"] for p in order]
    reg = [R[p]["pv_reg"] for p in order]
    arr = [R[p]["arr"] for p in order]
    crit = _floor(crit, None, arr); reg = _floor(reg, None, arr)
    x = np.arange(len(order)); w = 0.36
    fig, ax = plt.subplots(figsize=(W + 0.6, H))
    ax.bar(x - w / 2, crit, w, color=PALETTE[0], label=r"critical users ($\delta=10^{-6}$)")
    ax.bar(x + w / 2, reg, w, color=PALETTE[1], label=r"regular users ($\delta=10^{-5}$)", hatch="///", edgecolor="white")
    ax.set_yscale("log")
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_ylabel(r"$\Pr\{D>D_{\max}\}$")
    ax.set_xlabel("PA placement rule")
    ax.legend()
    _save(fig, "fig_hetero")


def fig_bcd():
    with open(os.path.join(RESULTS, "bcd", "bcd.json")) as f:
        D = json.load(f)
    fig, ax = plt.subplots(figsize=(W, H))
    for i, (s, d) in enumerate(sorted(D.items())):
        h = np.array(d["hist"])
        ax.plot(np.arange(h.size), h, marker="o", markerfacecolor="white", color=PALETTE[i % 8], label=f"drop {int(s)+1}")
    ax.set_xlabel("BCD iteration")
    ax.set_ylabel(r"Tail load $\sum_k c_{{\rm req},k}/R_k^{(j_0)}$")
    ax.legend(ncol=2)
    _save(fig, "fig_bcd")


def fig_placement_example():
    with open(os.path.join(RESULTS, "bcd", "bcd.json")) as f:
        D = json.load(f)
    d = D["0"]
    users = np.array(d["users"]); x = np.array(d["x"]); creq = np.array(d["creq"])
    fig, ax = plt.subplots(figsize=(W, 1.6))
    M = x.size; Ls = 40.0 / M
    for m in range(M):
        ax.plot([m * Ls, (m + 1) * Ls], [0, 0], color="0.3", lw=2.5, solid_capstyle="butt")
        ax.plot([m * Ls], [0], marker="|", color="0.1", markersize=9)
    crit = creq > np.median(creq)
    ax.scatter(users[~crit, 0], users[~crit, 1], marker="o", s=22, color=PALETTE[1], label="regular user", zorder=3)
    ax.scatter(users[crit, 0], users[crit, 1], marker="D", s=22, color=PALETTE[7], label="critical user", zorder=3)
    ax.scatter(x, np.zeros(M), marker="v", s=40, color=PALETTE[0], label="activated PA (TAPP)", zorder=4)
    ax.set_xlabel("$x$ (m)"); ax.set_ylabel("$y$ (m)")
    ax.set_ylim(-6, 6); ax.set_xlim(-1, 41)
    ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.32), frameon=False)
    _save(fig, "fig_placement")


def fig_key():
    """H1: mean delay (left) and delay-violation probability (right) versus the peak rate."""
    R = load("key")
    fig, axs = plt.subplots(1, 2, figsize=(2 * W, H))
    for s in [k for k in ["TLA-SWAN", "SWAN-MLWDF", "SWAN-MW", "SWAN-RATEMAX", "SWAN-EDF", "SWAN-SA"] if k in R]:
        vals = sorted(R[s].keys())
        x = np.array(vals, float)
        _series(axs[0], x, [R[s][v]["mean_delay"] * 0.1 for v in vals], s)
        _series(axs[1], x, _floor([R[s][v]["pv"] for v in vals], None, [R[s][v]["arr"] for v in vals]), s)
    axs[0].set_ylabel("Mean delay (ms)"); axs[1].set_ylabel(r"$\Pr\{D>D_{\max}\}$"); axs[1].set_yscale("log")
    for ax in axs:
        ax.set_xlabel("Peak arrival rate $h$ (packets/slot)")
    axs[1].axhline(1e-5, color="0.4", lw=0.7, ls="--")
    axs[0].legend(loc="upper left")
    _save(fig, "fig_key")


def fig_energy():
    """H2: energy per slot versus achieved delay-violation probability (V sweep)."""
    R = load("energy")
    fig, ax = plt.subplots(figsize=(W, H))
    for s in [k for k in ["TLA-SWAN", "SWAN-MW", "SWAN-RATEMAX"] if k in R]:
        vals = sorted(R[s].keys())
        pw = np.array([R[s][v]["power_mW"] for v in vals]); pv = _floor([R[s][v]["pv"] for v in vals], None, [R[s][v]["arr"] for v in vals])
        _series(ax, pw, pv, s)
        if s == "TLA-SWAN":
            for v, x, y in zip(vals, pw, pv):
                ax.annotate(f"$V={v:g}$", (x, y), textcoords="offset points", xytext=(3, 3), fontsize=5.5)
    ax.set_yscale("log"); ax.set_xlabel("Average power consumption (mW, incl. circuit power)"); ax.set_ylabel(r"$\Pr\{D>D_{\max}\}$")
    ax.legend(loc="upper right")
    _save(fig, "fig_energy")


def fig_target():
    R = load("target")["TLA-SWAN"]
    vals = sorted(R.keys(), reverse=True)
    fig, ax = plt.subplots(figsize=(W, H))
    x = [-np.log10(v) for v in vals]
    ax.plot(x, [R[v]["power_mW"] for v in vals], "o-", color=PALETTE[0], markerfacecolor="white", label="power (mW)")
    ax.set_xlabel(r"Reliability target $-\log_{10}\delta$"); ax.set_ylabel("Average power (mW)")
    ax2 = ax.twinx()
    ax2.plot(x, _floor([R[v]["pv"] for v in vals], None, [R[v]["arr"] for v in vals]), "s--", color=PALETTE[1], markerfacecolor="white", label="achieved $\\Pr\\{D>D_{\\max}\\}$")
    ax2.set_yscale("log"); ax2.set_ylabel(r"achieved $\Pr\{D>D_{\max}\}$")
    ax2.plot(x, vals, ":", color="0.4", lw=0.8)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left")
    _save(fig, "fig_target")


def fig_modes():
    """Probability of each SWAN mode versus the total queue length (energy-aware TLA-SWAN, V=0.3)."""
    R = load("energy")["TLA-SWAN"]
    v = 0.3 if 0.3 in R else sorted(R.keys())[len(R) // 2]
    mh = R[v]["mode_hist"]
    tot = mh.sum(axis=0); mask = tot > 200
    q = np.arange(mh.shape[1])[mask]
    fig, ax = plt.subplots(figsize=(W, H))
    names = ["idle", "SS ($j=1$)", "SA ($1<j<M$)", "SA ($j=M$)", "SM"]
    for i, nm in enumerate(names):
        if i == 0:
            continue
        ax.plot(q, mh[i][mask] / tot[mask], marker="osv^D"[i], markerfacecolor="white", color=PALETTE[i], label=nm)
    ax.set_xlabel("Total queue length (packets)"); ax.set_ylabel("Mode probability")
    ax.set_ylim(0, 1); ax.legend()
    _save(fig, "fig_modes")


def fig_fixedj():
    R = load("fixedj")
    fig, ax = plt.subplots(figsize=(W, H))
    for s in ["SWAN-FIXJ-onoff", "SWAN-FIXJ-poisson"]:
        if s not in R:
            continue
        vals = sorted(R[s].keys())
        _series(ax, vals, _floor([R[s][v]["pv"] for v in vals], None, [R[s][v]["arr"] for v in vals]), s)
    ax.set_yscale("log"); ax.set_xlabel("Fixed number of aggregated segments $j$"); ax.set_ylabel(r"$\Pr\{D>D_{\max}\}$")
    ax.set_xticks([1, 2, 3, 4]); ax.legend()
    _save(fig, "fig_fixedj")


def fig_cfg():
    R = load("cfg")
    fig, ax = plt.subplots(figsize=(W, H))
    for s in ["TLA-SWAN-cfg", "TLA-SWAN-cfg-warm", "SWAN-FULL-cfg"]:
        if s not in R:
            continue
        vals = sorted(R[s].keys())
        _series(ax, vals, _floor([R[s][v]["pv"] for v in vals], None, [R[s][v]["arr"] for v in vals]), s)
    ax.set_yscale("log"); ax.set_xlabel(r"Segment activation delay $\tau_{\rm cfg}$ (slots)"); ax.set_ylabel(r"$\Pr\{D>D_{\max}\}$")
    ax.legend()
    _save(fig, "fig_cfg")


def fig_single(Ts=1e-4):
    """Route A: analytical tail approximation versus simulation for one device in fixed SA mode."""
    from src.tail_analysis import single_user_fixed_sa
    from experiments.run_campaign import EXPERIMENTS
    import json, glob
    R = load("single")
    fig, ax = plt.subplots(figsize=(W, H))
    for s in ["SINGLE-SA", "SINGLE-TLA"]:
        if s not in R:
            continue
        vals = sorted(R[s].keys())
        _series(ax, vals, _floor([R[s][v]["pv"] for v in vals], None, [R[s][v]["arr"] for v in vals]), s)
    # analytical curve: average over the drops of the fixed-SA runs (SNR from each run)
    files = glob.glob(os.path.join(RESULTS, "single", "SINGLE-SA__*.json"))
    approx = {}
    for fn in files:
        r = json.load(open(fn)); c = r["cfg"]
        snr = 10 ** (r["snr_agg_dB"][0] / 10)
        a = single_user_fixed_sa(c["h"], c["alpha"], c["beta"], c["Ts"], snr, c["n"], c["L"], c["bmax"], c["Dmax_slots"])
        approx.setdefault(c["h"], []).append(a["pv_approx"])
    hs = sorted(approx)
    ax.plot(hs, [np.mean(approx[h]) for h in hs], "k-.", lw=1.0, label="Route-A approximation (fixed SA)")
    ax.set_yscale("log"); ax.set_xlabel("Peak arrival rate $h$ (packets/slot)"); ax.set_ylabel(r"$\Pr\{D>D_{\max}\}$")
    ax.legend()
    _save(fig, "fig_single")


def all_figures():
    done = []
    def safe(f, *a, **k):
        try:
            f(*a, **k); done.append(f.__name__ + str(a[:1]))
        except Exception as e:
            print("skip", f.__name__, a[:1], "->", e)
    safe(fig_ccdf)
    safe(fig_sweep, "peak", "Peak arrival rate $h$ (packets/slot)", "fig_peak")
    safe(fig_sweep, "burst", r"Mean burst duration $1/\alpha$ (ms)", "fig_burst", xfun=lambda a: 1e3 / a, xscale="log")
    safe(fig_sweep, "power", r"Per-segment transmit power $P_{\max}$ (dBm)", "fig_power")
    safe(fig_sweep, "segments", "Number of segments $M$ ($D_x = 40$ m)", "fig_segments")
    safe(fig_sweep, "dmax", r"Latency budget $D_{\max}$ (ms)", "fig_dmax", xfun=lambda v: v * 0.1)
    safe(fig_sweep, "users", "Number of users $K$", "fig_users")
    safe(fig_sweep, "tau", r"Reconfiguration delay $\tau_r$ (slots)", "fig_tau")
    safe(fig_sweep, "rician", "Rician factor (dB)", "fig_rician", xfun=lambda v: 60 if np.isinf(v) else 10 * np.log10(v))
    safe(fig_sweep, "mismatch", r"Mismatch factor on $c_{\rm req}$", "fig_mismatch")
    safe(fig_V)
    safe(fig_hetero)
    safe(fig_bcd)
    safe(fig_placement_example)
    safe(fig_key); safe(fig_energy); safe(fig_target); safe(fig_modes); safe(fig_fixedj); safe(fig_cfg); safe(fig_single)
    print("figures:", done)


if __name__ == "__main__":
    all_figures()
