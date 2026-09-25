"""Slot-level simulator of a downlink SWAN serving K HRLLC users with bursty
traffic, finite-blocklength transmissions, deadline-constrained queues, segment
activation with circuit power and configuration delay.

Per-slot order of events (slot t):
  1. new packets arrive (age 0);
  2. the controller picks an action (users S, active segments A, packets b, power);
  3. each scheduled user decodes its codeword with probability 1-eps_k;
     on success the b_k oldest packets leave (delay = age+1 slots);
  4. energy, mode statistics and virtual credits are updated;
  5. packets age by one slot; packets reaching the drop horizon are discarded.
A packet violates the latency target if it is delivered after Dmax slots or
discarded.  Results are pooled counts, so runs can be merged exactly.
"""
from dataclasses import dataclass, asdict
import numpy as np

from .swan_channel import SWAN
from .arrivals import OnOffSource, PoissonSource, PeriodicJitterSource, required_rate_onoff
from .placement import (place_tapp, place_sumrate, place_center, place_nearest, place_maxmin_rate, place_load)
from .service import ActionTable
from .controller import Controller, cum_values, user_weight_values


@dataclass
class SimConfig:
    # --- SWAN geometry / PHY
    M: int = 4
    Ls: float = 10.0
    d: float = 3.0
    Dy: float = 10.0
    fc: float = 28e9
    n_eff: float = 1.4
    Pmax_dBm: float = -10.0
    sigma2_dBm: float = -101.0   # -174 dBm/Hz + 10log10(2 MHz) + 10 dB noise figure
    alpha_g_dBpm: float = 0.08   # in-waveguide attenuation kappa (dB/m), Ouyang et al.
    rician_K: float = np.inf
    coh_slots: int = 100
    margin: float = 0.1
    # --- users / slots / packets
    K: int = 8
    Ts: float = 1e-4
    n: int = 200          # channel uses per slot (B = 2 MHz, Ts = 0.1 ms)
    L: int = 256          # bits per packet (32 bytes)
    bmax: int = 12
    shannon: bool = False  # ablation: Shannon capacity instead of FBL
    # --- traffic
    traffic: str = "onoff"  # onoff | poisson | periodic
    h: float = 3.0          # peak packets/slot in ON state
    alpha: float = 1000.0   # ON->OFF rate (1/s)  -> mean ON 1 ms
    beta: float = 111.11    # OFF->ON rate (1/s)  -> mean OFF 9 ms
    period_slots: int = 20
    batch: int = 4
    jitter_slots: int = 2
    n_crit: int = 0         # users 0..n_crit-1 are critical
    h_crit: float = 4.0
    alpha_crit: float = 1000.0
    delta_crit: float = 1e-6
    # --- latency targets
    Dmax_slots: int = 10
    Ddrop_slots: int = 10   # drop horizon (>= Dmax_slots)
    delta: float = 1e-5
    eps0: float = 1e-5      # nominal FBL reliability used by the placement
    # --- architecture / placement
    arch: str = "swan"       # swan | pass | colocated
    placement: str = "tapp"  # tapp | sumrate | center | nearest | maxmin
    tapp_j: int = 2          # aggregation depth j0 used in the TAPP/load margin (0 = all segments)
    maxmin_j: int = 0        # depth for the tail-agnostic max-min placement (0 = all)
    reactive: bool = False
    tau_r_slots: int = 1
    creq_scale: float = 1.0
    # --- controller
    scheduler: str = "tas"   # tas | mw | mlwdf | edf | pf | ratemax
    mode: str = "adaptive"   # adaptive (SS..SA and SM) | full (SA j=M and SM) | ss | sa | sa_j
    fixed_j: int = 0         # for mode = sa_j
    V: float = 0.0           # energy weight (value units per W)
    Pc_W: float = 0.0        # circuit power per active segment (W)
    V_cfg: float = 0.0       # cost per segment activation
    tau_cfg: float = 0.0     # activation delay (slots, may be fractional)
    la: float = 0.0          # one-step lookahead weight
    keep_warm: bool = False  # keep the last active set powered when idle
    rho_levels: tuple = (1.0,)
    kappa: float = 0.75      # tail sharpness of the packet values
    zeta: float = 0.0        # optional credit weight
    zcap_factor: float = 1.0
    pkt_floor: float = 0.0
    # legacy aliases kept for the first campaign's job files
    tas_variant: str = "pkt"
    pkt_scale: float = 0.75
    pkt_pf: bool = False
    # --- run control
    T: int = 200_000
    warmup: int = 2_000
    seed: int = 0
    mode_qbins: int = 41

    def to_dict(self):
        d = asdict(self)
        d["rician_K"] = float(self.rician_K) if np.isfinite(self.rician_K) else "inf"
        return d


def user_params(cfg):
    h = np.full(cfg.K, float(cfg.h)); al = np.full(cfg.K, float(cfg.alpha))
    be = np.full(cfg.K, float(cfg.beta)); de = np.full(cfg.K, float(cfg.delta))
    if cfg.n_crit > 0:
        h[:cfg.n_crit] = cfg.h_crit; al[:cfg.n_crit] = cfg.alpha_crit; de[:cfg.n_crit] = cfg.delta_crit
    return h, al, be, de


def make_source(cfg, rng):
    h, al, be, de = user_params(cfg)
    if cfg.traffic == "onoff":
        return OnOffSource(cfg.K, cfg.Ts, h, al, be, rng)
    if cfg.traffic == "poisson":
        return PoissonSource(cfg.K, cfg.Ts, h * be / (al + be), rng)
    if cfg.traffic == "periodic":
        return PeriodicJitterSource(cfg.K, cfg.Ts, cfg.period_slots, cfg.batch, cfg.jitter_slots, rng,
                                    h_ev=cfg.h, alpha_ev=cfg.alpha, beta_ev=cfg.beta)
    raise ValueError(cfg.traffic)


def _creq_poisson(lam, Dmax_slots, delta):
    from scipy.optimize import brentq
    Lam = np.log(1 / delta) / Dmax_slots
    def g(c):
        th = brentq(lambda th: lam * (np.exp(th) - 1) - c * th, 1e-9, 50.0)
        return th * c - Lam
    return brentq(g, lam * (1 + 1e-6), 50 * lam + 50)


def required_rate(cfg):
    h, al, be, de = user_params(cfg)
    Dmax = cfg.Dmax_slots * cfg.Ts
    if cfg.traffic == "onoff":
        c = required_rate_onoff(h, al, be, Dmax, de)
    elif cfg.traffic == "poisson":
        lam = h * be / (al + be)
        c = np.array([_creq_poisson(l, cfg.Dmax_slots, d) for l, d in zip(lam, de)])
    else:
        c = required_rate_onoff(h, al, be, Dmax, de) + cfg.batch / cfg.period_slots
    return c * cfg.creq_scale


from .queue import fifo_remove as _fifo_remove


WEIGHTS = {"tas": "value", "mw": "mw", "mlwdf": "mlwdf", "edf": "edf", "pf": "pf", "ratemax": "goodput"}
KINDS = ["idle", "SS", "SA-partial", "SA-full", "SM"]


class Simulator:
    def __init__(self, cfg: SimConfig):
        self.cfg = cfg
        self.rng = np.random.default_rng(cfg.seed)
        self.sw = SWAN(M=cfg.M, Ls=cfg.Ls, d=cfg.d, Dy=cfg.Dy, fc=cfg.fc, n_eff=cfg.n_eff,
                       alpha_g_dBpm=cfg.alpha_g_dBpm, margin=cfg.margin, sigma2_dBm=cfg.sigma2_dBm,
                       Pmax_dBm=cfg.Pmax_dBm, rician_K=cfg.rician_K, rng=self.rng)
        self.users = self.sw.drop_users(cfg.K, self.rng)
        self.src = make_source(cfg, self.rng)
        self.creq = required_rate(cfg)
        self.zcap = (cfg.zcap_factor * self.creq * cfg.Dmax_slots) if cfg.zcap_factor > 0 else np.full(cfg.K, np.inf)
        self.pa_x = self._place()
        self.kappa = cfg.kappa if cfg.tas_variant == "pkt" else cfg.pkt_scale

    def _place(self):
        cfg, sw, U = self.cfg, self.sw, self.users
        if cfg.arch == "colocated" or cfg.placement == "center":
            return place_center(sw)
        if cfg.placement == "tapp":
            return place_tapp(sw, U, self.creq, cfg.n, cfg.eps0, cfg.L, j=(cfg.tapp_j or None))
        if cfg.placement == "sumrate":
            return place_sumrate(sw, U, cfg.n, cfg.eps0, cfg.L)
        if cfg.placement == "maxmin":
            return place_maxmin_rate(sw, U, cfg.n, cfg.eps0, cfg.L, j=(cfg.maxmin_j or None))
        if cfg.placement == "load":
            return place_load(sw, U, self.creq, cfg.n, cfg.eps0, cfg.L, j=(cfg.tapp_j or None))
        if cfg.placement == "nearest":
            return place_nearest(sw, U)
        raise ValueError(cfg.placement)

    def _channel(self, pa_x, silent=None):
        cfg = self.cfg
        if cfg.arch == "colocated":
            xc = self.sw.Dx / 2 + (np.arange(cfg.M) - (cfg.M - 1) / 2) * self.sw.lam / 2
            H = self.sw.los_channel(self.users, xc)
            H = H * np.exp(1j * 2 * np.pi * (xc - self.sw.x0) / self.sw.lam_g)[None, :]
        else:
            H = self.sw.channel(self.users, pa_x, self.rng)
            if cfg.arch == "pass":
                # single long waveguide fed at x=0: attenuation over the full feed-to-PA length
                extra = np.exp(-0.5 * self.sw.alpha_g * (pa_x - 0.0)) / np.exp(-0.5 * self.sw.alpha_g * (pa_x - self.sw.x0))
                H = H * extra[None, :]
        if silent is not None and silent.any():
            H = H.copy(); H[:, silent] = 0.0
        return H

    def _table(self, H):
        cfg = self.cfg
        mode = cfg.mode
        if cfg.arch == "pass":
            return ActionTable(self.sw, H, cfg.n, cfg.L, cfg.bmax, cfg.rho_levels, sa_only=True,
                               fixed_j=cfg.M, shannon=cfg.shannon)
        if mode == "adaptive":
            return ActionTable(self.sw, H, cfg.n, cfg.L, cfg.bmax, cfg.rho_levels, shannon=cfg.shannon)
        if mode == "full":
            return ActionTable(self.sw, H, cfg.n, cfg.L, cfg.bmax, cfg.rho_levels, fixed_j=cfg.M, shannon=cfg.shannon)
        if mode == "ss":
            return ActionTable(self.sw, H, cfg.n, cfg.L, cfg.bmax, cfg.rho_levels, sa_only=True, fixed_j=1, shannon=cfg.shannon)
        if mode == "sa":
            return ActionTable(self.sw, H, cfg.n, cfg.L, cfg.bmax, cfg.rho_levels, sa_only=True, fixed_j=cfg.M, shannon=cfg.shannon)
        if mode == "sa_j":
            return ActionTable(self.sw, H, cfg.n, cfg.L, cfg.bmax, cfg.rho_levels, sa_only=True, fixed_j=cfg.fixed_j, shannon=cfg.shannon)
        raise ValueError(mode)

    def run(self):
        cfg = self.cfg
        K, M, H_ = cfg.K, cfg.M, cfg.Ddrop_slots
        rng = self.rng
        weights = WEIGHTS[cfg.scheduler]
        h_, al_, be_, de_ = user_params(cfg)
        a_k = np.log(1.0 / de_) / cfg.Dmax_slots
        ages_row = np.arange(H_)[None, :]

        q = np.zeros((K, H_), int)
        Z = np.zeros(K)
        Rbar = np.full(K, 1e-3)
        hist = np.zeros((K, H_ + 1)); dropped = np.zeros(K); arrivals = np.zeros(K)
        decode_fail = np.zeros(K); n_sched = np.zeros(K)
        energy = 0.0; energy_tx = 0.0; Zsum = np.zeros(K); Qsum = np.zeros(K)
        reconf = 0; activations = 0
        mode_hist = np.zeros((len(KINDS), cfg.mode_qbins))
        nact_sum = 0.0

        silent_until = np.zeros(M, int)
        ready_time = np.zeros(M, int)      # slot from which a segment is usable
        active_prev = np.zeros(M, bool)
        pa_x = self.pa_x.copy()
        H = self._channel(pa_x)
        tab = self._table(H)
        ctrl = Controller(tab, weights=weights, V=cfg.V, Pc=cfg.Pc_W, V_cfg=cfg.V_cfg, la=cfg.la,
                          tau_cfg=cfg.tau_cfg, edf=(cfg.scheduler == "edf"))
        fading = np.isfinite(cfg.rician_K)
        # packet values are static when they depend on the age only
        v_const = None
        if weights in ("value", "mw", "goodput", "edf") and not (weights == "value" and (cfg.zeta > 0 or cfg.pkt_pf)):
            v_const = user_weight_values(weights, q, ages_row, cfg.Dmax_slots, a_k, self.kappa, Rbar,
                                         Z=Z, zeta=0.0, creq=self.creq, pkt_floor=cfg.pkt_floor)
        v_next_const = None
        if v_const is not None and cfg.la > 0:
            v_next_const = user_weight_values(weights, q, ages_row + 1.0, cfg.Dmax_slots, a_k, self.kappa, Rbar,
                                              Z=Z, zeta=0.0, creq=self.creq, pkt_floor=cfg.pkt_floor)

        for t in range(cfg.T):
            A = self.src.step()
            q[:, 0] += A
            if t >= cfg.warmup:
                arrivals += A
            qpk = q.sum(axis=1)

            rebuild = fading and t % cfg.coh_slots == 0 and t > 0
            if cfg.reactive:
                Wt = qpk + cfg.zeta * Z
                new_x = pa_x.copy()
                for m in range(M):
                    inseg = (self.users[:, 0] >= self.sw.x0[m]) & (self.users[:, 0] < self.sw.x0[m] + cfg.Ls)
                    cand = np.where(inseg & (qpk > 0))[0]
                    if cand.size:
                        k = cand[np.argmax(Wt[cand])]
                        new_x[m] = np.clip(self.users[k, 0], self.sw.xlo[m], self.sw.xhi[m])
                moved = np.abs(new_x - pa_x) > 1e-9
                if moved.any():
                    reconf += int(moved.sum()); silent_until[moved] = t + cfg.tau_r_slots
                    pa_x = new_x; rebuild = True
                if rebuild or (silent_until == t).any():
                    H = self._channel(pa_x, silent=silent_until > t)
                    tab = self._table(H)
                    ctrl = Controller(tab, weights=weights, V=cfg.V, Pc=cfg.Pc_W, V_cfg=cfg.V_cfg, la=cfg.la,
                                      tau_cfg=cfg.tau_cfg, edf=(cfg.scheduler == "edf"))
            elif rebuild:
                H = self._channel(pa_x); tab = self._table(H)
                ctrl = Controller(tab, weights=weights, V=cfg.V, Pc=cfg.Pc_W, V_cfg=cfg.V_cfg, la=cfg.la,
                                  tau_cfg=cfg.tau_cfg, edf=(cfg.scheduler == "edf"))

            # ---- values and decision
            dec = None
            if qpk.any():
                if v_const is not None:
                    v = v_const
                else:
                    v = user_weight_values(weights, q, ages_row, cfg.Dmax_slots, a_k, self.kappa, Rbar,
                                           Z=Z, zeta=cfg.zeta, creq=self.creq, pkt_floor=cfg.pkt_floor)
                    if cfg.pkt_pf and weights == "value":
                        v = v / np.maximum(Rbar, 1e-3)[:, None]
                bl = qpk > 0
                U_now = np.full((K, cfg.bmax + 1), np.nan); U_now[:, 0] = 0.0
                U_now[bl] = cum_values(q[bl], v[bl], cfg.bmax)
                if cfg.la > 0:
                    v_next = v_next_const if v_next_const is not None else user_weight_values(
                        weights, q, ages_row + 1.0, cfg.Dmax_slots, a_k, self.kappa, Rbar,
                        Z=Z, zeta=cfg.zeta, creq=self.creq, pkt_floor=cfg.pkt_floor)
                    U_next = np.full((K, cfg.bmax + 1), np.nan); U_next[:, 0] = 0.0
                    U_next[bl] = cum_values(q[bl], v_next[bl], cfg.bmax)
                else:
                    U_next = U_now
                ctrl._hol = np.max(np.where(q > 0, ages_row, -1), axis=1)
                ready = active_prev & (ready_time <= t)
                dec = ctrl.decide(U_now, U_next, qpk, ready, active_prev, t)

            # ---- transmission and activation bookkeeping
            s = np.zeros(K)
            if dec is not None:
                segs = dec["segs"]
                newly = segs & ~active_prev
                if newly.any():
                    activations += int(newly.sum())
                    if cfg.tau_cfg >= 1.0:
                        ready_time[newly] = t + int(np.ceil(cfg.tau_cfg))
                    else:
                        ready_time[newly] = t
                usable = segs & (ready_time <= t)
                b = dec["b"]
                if usable.any():
                    ok = rng.random(K) < (1.0 - dec["eps"])
                else:
                    ok = np.zeros(K, bool)   # all segments still configuring
                b_ok = np.where(ok, b, 0)
                served = _fifo_remove(q, b_ok)
                q -= served
                s = served.sum(axis=1).astype(float)
                active_now = segs.copy()
                kind = dec["kind"]
                if kind == "SA":
                    kind_i = 1 if dec["j"] == 1 else (3 if dec["j"] == M else 2)
                else:
                    kind_i = 4
                e_slot = dec["energy"]
                if t >= cfg.warmup:
                    hist[:, 1:] += served
                    decode_fail += (b > 0) & (~ok) & usable.any()
                    n_sched += (b > 0)
                    energy_tx += tab.rho[dec["rho_idx"]] * tab.ptx[dec["act"]]
            else:
                active_now = active_prev.copy() if cfg.keep_warm else np.zeros(M, bool)
                kind_i = 0
                e_slot = active_now.sum() * cfg.Pc_W
            if t >= cfg.warmup:
                energy += e_slot
                nact_sum += active_now.sum()
                mode_hist[kind_i, min(int(qpk.sum()), cfg.mode_qbins - 1)] += 1
            active_prev = active_now
            Rbar = 0.999 * Rbar + 0.001 * s

            Z = np.minimum(np.maximum(Z + self.creq * (qpk > 0) - s, 0.0), self.zcap)
            if t >= cfg.warmup:
                Zsum += Z; Qsum += q.sum(axis=1)
                dropped += q[:, H_ - 1]
            q[:, 1:] = q[:, :-1]; q[:, 0] = 0

        Teff = cfg.T - cfg.warmup
        late = hist[:, cfg.Dmax_slots + 1:].sum(axis=1)
        viol = dropped + late
        delivered = hist.sum(axis=1)
        mean_delay = float((hist * np.arange(H_ + 1)[None, :]).sum() / max(delivered.sum(), 1))
        return dict(
            cfg=cfg.to_dict(), users=self.users.tolist(), pa_x=pa_x.tolist(), creq=self.creq.tolist(),
            arrivals=arrivals.tolist(), viol=viol.tolist(), dropped=dropped.tolist(), late=late.tolist(),
            hist=hist.tolist(), decode_fail=decode_fail.tolist(), n_sched=n_sched.tolist(),
            avg_power_W=energy / Teff, avg_tx_power_W=energy_tx / Teff, avg_nact=nact_sum / Teff,
            activations=activations, mode_hist=mode_hist.tolist(), mean_delay_slots=mean_delay,
            avg_Z=(Zsum / Teff).tolist(), avg_Q=(Qsum / Teff).tolist(), reconf=reconf, Teff=Teff,
            pv=float(viol.sum() / max(arrivals.sum(), 1)),
            pv_max=float(np.max(viol / np.maximum(arrivals, 1))),
            snr_agg_dB=(10 * np.log10(self.sw.agg_snr(self.sw.los_channel(self.users, pa_x)))).tolist(),
        )


def run_config(cfg: SimConfig):
    return Simulator(cfg).run()
