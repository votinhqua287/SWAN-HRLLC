"""Experiment definitions and a resumable multiprocessing runner.

Usage:  python -m sim.experiments --exp peak burst --procs 4 [--T-scale 0.5] [--seeds 4]
Results are stored as one JSON per (experiment, scheme, sweep value, seed) in
results/<exp>/ so that partial runs can be resumed and pooled exactly.
"""
import argparse, json, os, time, glob
from multiprocessing import Pool
import numpy as np

from .simulator import SimConfig, run_config
from .placement import place_tapp
from .swan import SWAN

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RESULTS = os.path.join(ROOT, "results")

SCHEMES = {
    "TLA-SWAN":      dict(arch="swan", placement="tapp", scheduler="tas"),
    "SWAN-MLWDF":    dict(arch="swan", placement="tapp", scheduler="mlwdf"),
    "SWAN-MW":       dict(arch="swan", placement="tapp", scheduler="mw"),
    "SWAN-EDF":      dict(arch="swan", placement="tapp", scheduler="edf"),
    "SWAN-SR":       dict(arch="swan", placement="sumrate", scheduler="mw"),
    "SWAN-fixed":    dict(arch="swan", placement="center", scheduler="tas"),
    "SWAN-reactive": dict(arch="swan", placement="nearest", scheduler="tas", reactive=True),
    "PASS-1WG":      dict(arch="pass", placement="tapp", scheduler="tas"),
    "Fixed-array":   dict(arch="colocated", placement="center", scheduler="tas"),
}
MAIN5 = ["TLA-SWAN", "SWAN-MLWDF", "SWAN-MW", "SWAN-EDF", "SWAN-SR"]
MAIN7 = MAIN5 + ["SWAN-fixed", "PASS-1WG"]
ALL8 = MAIN7 + ["Fixed-array"]

EXPERIMENTS = {
    "ccdf":     dict(param=None, values=[None], schemes=ALL8, base=dict(Ddrop_slots=40), T=800_000, seeds=4),
    "peak":     dict(param="h", values=[2.0, 2.5, 3.0, 3.5, 4.0], schemes=MAIN7, T=250_000, seeds=4),
    "burst":    dict(param="alpha", values=[4000.0, 2000.0, 1000.0, 500.0, 250.0], schemes=MAIN5, T=250_000, seeds=4,
                     derive=lambda v: dict(beta=v / 9.0)),
    "power":    dict(param="Pmax_dBm", values=[-20.0, -15.0, -10.0, -5.0, 0.0], schemes=MAIN5 + ["Fixed-array"], T=250_000, seeds=4),
    "segments": dict(param="M", values=[2, 4, 5, 8, 10], schemes=MAIN5 + ["PASS-1WG"], T=250_000, seeds=4,
                     derive=lambda v: dict(Ls=40.0 / v)),
    "dmax":     dict(param="Dmax_slots", values=[3, 5, 10, 20, 30], schemes=MAIN5, T=250_000, seeds=4,
                     derive=lambda v: dict(Ddrop_slots=v)),
    "users":    dict(param="K", values=[4, 6, 8, 10, 12], schemes=MAIN5, T=250_000, seeds=4),
    "tau":      dict(param="tau_r_slots", values=[0, 1, 2, 5, 10], schemes=["TLA-SWAN", "SWAN-reactive", "SWAN-fixed"],
                     T=150_000, seeds=4),
    "V":        dict(param="V", values=[0.0, 1e3, 3e3, 1e4, 3e4, 1e5], schemes=["TLA-SWAN"], T=250_000, seeds=4,
                     base=dict(rho_levels=(0.1, 0.2, 0.4, 0.7, 1.0))),
    "hetero":   dict(param="placement", values=["tapp", "sumrate", "maxmin", "center"], schemes=["TLA-SWAN"],
                     T=250_000, seeds=4, base=dict(n_crit=2, h_crit=4.0, delta_crit=1e-6)),
    "rician":   dict(param="rician_K", values=[np.inf, 100.0, 10.0, 3.0], schemes=["TLA-SWAN", "SWAN-MLWDF", "SWAN-MW"],
                     T=250_000, seeds=4),
    "mismatch": dict(param="creq_scale", values=[0.5, 0.75, 1.0, 1.5, 2.0], schemes=["TLA-SWAN"], T=250_000, seeds=4),
    "traffic":  dict(param="traffic", values=["onoff", "poisson", "periodic"], schemes=MAIN5, T=250_000, seeds=4,
                     base=dict(period_slots=20, batch=2, jitter_slots=2)),
}


def _fmt(v):
    if v is None:
        return "na"
    if isinstance(v, float):
        return "inf" if np.isinf(v) else f"{v:g}"
    return str(v)


def make_jobs(exp, T_scale=1.0, seeds=None, procs_hint=4):
    spec = EXPERIMENTS[exp]
    nseeds = spec["seeds"] if seeds is None else seeds
    jobs = []
    for scheme in spec["schemes"]:
        for v in spec["values"]:
            for seed in range(nseeds):
                kw = dict(SCHEMES[scheme])
                kw.update(spec.get("base", {}))
                if spec["param"] is not None:
                    kw[spec["param"]] = v
                    if "derive" in spec:
                        kw.update(spec["derive"](v))
                kw["T"] = int(spec["T"] * T_scale)
                kw["seed"] = 100 + seed
                out = os.path.join(RESULTS, exp, f"{scheme}__{_fmt(v)}__s{seed}.json")
                jobs.append((exp, scheme, v, seed, kw, out))
    return jobs


def _run(job):
    exp, scheme, v, seed, kw, out = job
    if os.path.exists(out):
        return out, 0.0
    t0 = time.time()
    res = run_config(SimConfig(**kw))
    res.update(scheme=scheme, exp=exp, value=None if v is None else (float(v) if isinstance(v, (int, float, np.floating)) else v), seed=seed)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out + ".tmp", "w") as f:
        json.dump(res, f)
    os.replace(out + ".tmp", out)
    return out, time.time() - t0


def run_experiments(exps, procs=4, T_scale=1.0, seeds=None):
    jobs = []
    for e in exps:
        jobs += make_jobs(e, T_scale, seeds)
    # heavy jobs first for better load balance
    jobs.sort(key=lambda j: -j[4]["T"] * (1 + 3 * j[4].get("reactive", False)) * (j[4].get("K", 8) / 8) ** 2)
    print(f"{len(jobs)} jobs", flush=True)
    t0 = time.time()
    with Pool(procs) as p:
        for i, (out, dt) in enumerate(p.imap_unordered(_run, jobs)):
            if dt > 0:
                print(f"[{i+1}/{len(jobs)}] {os.path.relpath(out, RESULTS)} {dt:.0f}s (elapsed {time.time()-t0:.0f}s)", flush=True)


def run_bcd(seeds=(0, 1, 2, 3, 4), grid=200):
    """Convergence histories of the TAPP block-coordinate descent."""
    cfg = SimConfig()
    from .simulator import required_rate
    out = {}
    for s in seeds:
        rng = np.random.default_rng(1000 + s)
        sw = SWAN(M=cfg.M, Ls=cfg.Ls, d=cfg.d, Dy=cfg.Dy, fc=cfg.fc, n_eff=cfg.n_eff, alpha_g_dBpm=cfg.alpha_g_dBpm,
                  margin=cfg.margin, sigma2_dBm=cfg.sigma2_dBm, Pmax_dBm=cfg.Pmax_dBm, rng=rng)
        users = sw.drop_users(cfg.K, rng)
        c2 = SimConfig(n_crit=2, h_crit=4.0, delta_crit=1e-6)
        creq = required_rate(c2)
        x, best, hist = place_tapp(sw, users, creq, cfg.n, cfg.eps0, cfg.L, grid=grid, return_hist=True)
        out[str(s)] = dict(hist=hist.tolist(), x=x.tolist(), users=users.tolist(), creq=creq.tolist())
    os.makedirs(os.path.join(RESULTS, "bcd"), exist_ok=True)
    with open(os.path.join(RESULTS, "bcd", "bcd.json"), "w") as f:
        json.dump(out, f)
    return out


# ------------------------------------------------------------------ pooling
def load(exp):
    """Pool all seeds of an experiment: returns {scheme: {value: stats}}."""
    files = glob.glob(os.path.join(RESULTS, exp, "*.json"))
    agg = {}
    for fn in files:
        with open(fn) as f:
            r = json.load(f)
        key = (r["scheme"], r["value"])
        a = agg.setdefault(key, dict(viol=None, arr=None, hist=None, dropped=None, power=[], reconf=[], n=0,
                                     viol_users=[], arr_users=[], cfg=r["cfg"]))
        viol, arr = np.array(r["viol"]), np.array(r["arrivals"])
        hist, dropped = np.array(r["hist"]), np.array(r["dropped"])
        a["viol"] = viol if a["viol"] is None else a["viol"] + viol
        a["arr"] = arr if a["arr"] is None else a["arr"] + arr
        a["hist"] = hist if a["hist"] is None else a["hist"] + hist
        a["dropped"] = dropped if a["dropped"] is None else a["dropped"] + dropped
        a["power"].append(r["avg_power_W"])
        a["reconf"].append(r["reconf"])
        a["viol_users"].append(viol)
        a["arr_users"].append(arr)
        a["n"] += 1
    out = {}
    for (scheme, v), a in agg.items():
        tot_v, tot_a = a["viol"].sum(), a["arr"].sum()
        # tail CCDF of the delay in slots: P(D > d) for d = 0..Ddrop
        h = a["hist"].sum(axis=0)
        H = h.size - 1
        served_ge = np.cumsum(h[::-1])[::-1]  # served with delay >= d
        drop = a["dropped"].sum()
        ccdf = np.array([(served_ge[d + 1] if d + 1 <= H else 0.0) + drop for d in range(H + 1)]) / max(tot_a, 1)
        per_user_pv = np.concatenate([vu / np.maximum(au, 1) for vu, au in zip(a["viol_users"], a["arr_users"])])
        ncrit = a["cfg"].get("n_crit", 0)
        pv_crit = pv_reg = None
        if ncrit:
            vc = sum(vu[:ncrit].sum() for vu in a["viol_users"]); ac = sum(au[:ncrit].sum() for au in a["arr_users"])
            vr = sum(vu[ncrit:].sum() for vu in a["viol_users"]); ar = sum(au[ncrit:].sum() for au in a["arr_users"])
            pv_crit, pv_reg = vc / max(ac, 1), vr / max(ar, 1)
        out.setdefault(scheme, {})[v] = dict(pv=tot_v / max(tot_a, 1), viol=float(tot_v), arr=float(tot_a),
                                             pv_worst=float(per_user_pv.max()), ccdf=ccdf,
                                             power_mW=1e3 * float(np.mean(a["power"])), reconf=float(np.mean(a["reconf"])),
                                             n=a["n"], pv_crit=pv_crit, pv_reg=pv_reg)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", nargs="+", default=list(EXPERIMENTS))
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--T-scale", type=float, default=1.0)
    ap.add_argument("--seeds", type=int, default=None)
    args = ap.parse_args()
    exps = [e for e in args.exp if e != "bcd"]
    if "bcd" in args.exp:
        run_bcd()
    if exps:
        run_experiments(exps, args.procs, args.T_scale, args.seeds)
