"""Slot-level simulator of a downlink SWAN serving K HRLLC users with bursty
traffic, finite-blocklength transmissions and deadline-constrained queues.

Per-slot order of events (slot t):
  1. new packets arrive (age 0);
  2. the scheduler picks a user subset S, packets b_k and a power level;
  3. each scheduled user decodes its codeword with probability 1-eps_k;
     on success the b_k oldest packets leave (delay = age+1 slots);
  4. virtual queues are updated;
  5. packets age by one slot; packets reaching the drop horizon are discarded.
A packet violates the latency target if it is delivered after Dmax slots or
discarded.  Results are pooled counts, so runs can be merged exactly.
"""
from dataclasses import dataclass, field, asdict
import numpy as np

from .swan import SWAN
from .traffic import OnOffSource, PoissonSource, PeriodicJitterSource, required_rate_onoff
from .placement import (place_tapp, place_sumrate, place_center, place_nearest,
                        place_maxmin_rate, agg_rate_packets)
from .scheduler import (build_tables, WeightedScheduler, EDFScheduler, RoundRobinScheduler,
                        PacketValueScheduler)


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
    # --- traffic
    traffic: str = "onoff"  # onoff | poisson | periodic
    h: float = 3.0          # peak packets/slot in ON state
    alpha: float = 1000.0   # ON->OFF rate (1/s)  -> mean ON 1 ms
    beta: float = 111.11    # OFF->ON rate (1/s)  -> mean OFF 9 ms
    period_slots: int = 20
    batch: int = 4
    jitter_slots: int = 2
    # --- latency targets
    Dmax_slots: int = 10
    Ddrop_slots: int = 10   # drop horizon (>= Dmax_slots)
    delta: float = 1e-5
    eps0: float = 1e-5      # nominal FBL reliability used by the placement
    # --- scheme
    arch: str = "swan"       # swan | pass (single long waveguide, one RF chain) | colocated (fixed array)
    placement: str = "tapp"  # tapp | sumrate | center | nearest | maxmin
    scheduler: str = "tas"   # tas | mw | edf | rr | pf | mlwdf
    V: float = 0.0
    zeta: float = 0.0          # weight of the (optional) service-deficit credit in the packet values
    tas_variant: str = "pkt"  # pkt (proposed) | qz | holz | holz_pf | exp
    pkt_floor: float = 0.0     # throughput floor added to every packet value
    pkt_scale: float = 0.75    # tail-sharpness kappa multiplying the exponent a_k
    pkt_pf: bool = False       # divide packet values by the EWMA service rate (PF-type normalisation)
    rho_levels: tuple = (1.0,)
    reactive: bool = False
    tau_r_slots: int = 1
    creq_scale: float = 1.0  # mismatch factor on c_req (robustness tests)
    zcap_factor: float = 1.0  # Z_k capped at zcap_factor * c_req_k * Dmax_slots (0 = no cap)
    # --- heterogeneous traffic: users 0..n_crit-1 are "critical" with peak h_crit,
    #     ON->OFF rate alpha_crit and target delta_crit (others use h, alpha, delta)
    n_crit: int = 0
    h_crit: float = 3.0
    alpha_crit: float = 1000.0
    delta_crit: float = 1e-5
    # --- run control
    T: int = 200_000
    warmup: int = 2_000
    seed: int = 0

    def to_dict(self):
        d = asdict(self)
        d["rician_K"] = float(self.rician_K) if np.isfinite(self.rician_K) else "inf"
        return d


def user_params(cfg):
    """Per-user (h, alpha, beta, delta) arrays."""
    h = np.full(cfg.K, float(cfg.h))
    al = np.full(cfg.K, float(cfg.alpha))
    be = np.full(cfg.K, float(cfg.beta))
    de = np.full(cfg.K, float(cfg.delta))
    if cfg.n_crit > 0:
        h[:cfg.n_crit] = cfg.h_crit
        al[:cfg.n_crit] = cfg.alpha_crit
        de[:cfg.n_crit] = cfg.delta_crit
    return h, al, be, de


def make_source(cfg, rng):
    h, al, be, de = user_params(cfg)
    if cfg.traffic == "onoff":
        return OnOffSource(cfg.K, cfg.Ts, h, al, be, rng)
    if cfg.traffic == "poisson":
        mean = h * be / (al + be)
        return PoissonSource(cfg.K, cfg.Ts, mean, rng)
    if cfg.traffic == "periodic":
        return PeriodicJitterSource(cfg.K, cfg.Ts, cfg.period_slots, cfg.batch,
                                    cfg.jitter_slots, rng, h_ev=cfg.h,
                                    alpha_ev=cfg.alpha, beta_ev=cfg.beta)
    raise ValueError(cfg.traffic)


def _creq_poisson(lam, Dmax_slots, delta):
    """Discrete-time Poisson batches: EB(theta) = lam (e^theta - 1)/theta per slot;
    smallest c with theta*(c) c >= Lambda where lam (e^theta - 1) = c theta."""
    from scipy.optimize import brentq
    Lam = np.log(1 / delta) / Dmax_slots
    def g(c):
        th = brentq(lambda th: lam * (np.exp(th) - 1) - c * th, 1e-9, 50.0)
        return th * c - Lam
    return brentq(g, lam * (1 + 1e-6), 50 * lam + 50)


def required_rate(cfg):
    """Tail-latency-aware required service rate of every user (packets/slot)."""
    h, al, be, de = user_params(cfg)
    Dmax = cfg.Dmax_slots * cfg.Ts
    if cfg.traffic == "onoff":
        c = required_rate_onoff(h, al, be, Dmax, de)
    elif cfg.traffic == "poisson":
        lam = h * be / (al + be)
        c = np.array([_creq_poisson(l, cfg.Dmax_slots, d) for l, d in zip(lam, de)])
    else:  # periodic + events: ON-OFF part plus the periodic mean
        c = required_rate_onoff(h, al, be, Dmax, de) + cfg.batch / cfg.period_slots
    return c * cfg.creq_scale


def _fifo_remove(q, b):
    """Remove b[k] oldest packets from ring q (K, H); returns served (K,H)."""
    rev = q[:, ::-1]
    cs = np.cumsum(rev, axis=1)
    before = cs - rev
    served_rev = np.clip(b[:, None] - before, 0, rev)
    return served_rev[:, ::-1]


class Simulator:
    def __init__(self, cfg: SimConfig):
        self.cfg = cfg
        self.rng = np.random.default_rng(cfg.seed)
        self.sw = SWAN(M=cfg.M, Ls=cfg.Ls, d=cfg.d, Dy=cfg.Dy, fc=cfg.fc, n_eff=cfg.n_eff,
                       alpha_g_dBpm=cfg.alpha_g_dBpm, margin=cfg.margin,
                       sigma2_dBm=cfg.sigma2_dBm, Pmax_dBm=cfg.Pmax_dBm,
                       rician_K=cfg.rician_K, rng=self.rng)
        self.users = self.sw.drop_users(cfg.K, self.rng)
        self.src = make_source(cfg, self.rng)
        self.creq = required_rate(cfg)
        self.zcap = (cfg.zcap_factor * self.creq * cfg.Dmax_slots) if cfg.zcap_factor > 0 else np.full(cfg.K, np.inf)
        self.pa_x = self._place()
        self.n_eff_cu = cfg.n

    # ------------------------------------------------------------ placement
    def _place(self):
        cfg, sw, U = self.cfg, self.sw, self.users
        if cfg.placement == "tapp":
            return place_tapp(sw, U, self.creq, cfg.n, cfg.eps0, cfg.L)
        if cfg.placement == "sumrate":
            return place_sumrate(sw, U, cfg.n, cfg.eps0, cfg.L)
        if cfg.placement == "maxmin":
            return place_maxmin_rate(sw, U, cfg.n, cfg.eps0, cfg.L)
        if cfg.placement == "nearest":
            return place_nearest(sw, U)
        if cfg.placement == "center" or cfg.arch == "colocated":
            return place_center(sw)
        raise ValueError(cfg.placement)

    def _channel(self, pa_x, silent=None):
        cfg = self.cfg
        if cfg.arch == "colocated":
            # M co-located antennas at the centre of the area at height d,
            # lambda/2 spacing along x (conventional fixed-antenna BS)
            xc = self.sw.Dx / 2 + (np.arange(cfg.M) - (cfg.M - 1) / 2) * self.sw.lam / 2
            H = self.sw.los_channel(self.users, xc)
            # remove the (meaningless) in-waveguide phase for a conventional array
            s = (xc - self.sw.x0)
            H = H * np.exp(1j * 2 * np.pi * s / self.sw.lam_g)[None, :]
        else:
            H = self.sw.channel(self.users, pa_x, self.rng)
        if silent is not None and silent.any():
            H = H.copy()
            H[:, silent] = 0.0
        return H

    def _tables(self, H):
        cfg = self.cfg
        if cfg.arch == "pass":
            # conventional single-waveguide PASS: one RF chain -> at most one
            # user per slot (aggregation only) with in-waveguide loss over the
            # long waveguide fed at x=0 (alpha_g applied to the full length)
            s = (self.pa_x - 0.0)
            loss = np.exp(-0.5 * self.sw.alpha_g * s)[None, :]
            loss = loss / np.exp(-0.5 * self.sw.alpha_g * (self.pa_x - self.sw.x0))[None, :]
            Hs = H * loss
            tab = build_tables(self.sw, Hs, cfg.n, cfg.L, cfg.bmax, cfg.rho_levels,
                               n_eff=self.n_eff_cu)
            keep = tab["size"] == 1
            for key in ("mask", "snr", "ptot", "size", "G", "B", "E"):
                tab[key] = tab[key][keep]
            tab["subsets"] = [s for s, k in zip(tab["subsets"], keep) if k]
            return tab
        return build_tables(self.sw, H, cfg.n, cfg.L, cfg.bmax, cfg.rho_levels,
                            n_eff=self.n_eff_cu)

    # ------------------------------------------------------------------ run
    def run(self):
        cfg = self.cfg
        K, H_ = cfg.K, cfg.Ddrop_slots
        rng = self.rng
        q = np.zeros((K, H_), int)
        Z = np.zeros(K)
        Rbar = np.full(K, 1e-3)
        hist = np.zeros((K, H_ + 1))     # delay histogram in slots (index = delay)
        dropped = np.zeros(K)
        arrivals = np.zeros(K)
        decode_fail = np.zeros(K)
        tx_slots = 0
        power = 0.0
        Zsum = np.zeros(K)
        Qsum = np.zeros(K)
        reconf = 0
        n_sched = np.zeros(K)

        a_mlwdf = np.log(1.0 / user_params(cfg)[3]) / cfg.Dmax_slots
        if cfg.scheduler == "tas" and cfg.tas_variant == "pkt":
            sch = PacketValueScheduler(V=cfg.V)
            ages_row = np.arange(H_)[None, :]
        elif cfg.scheduler in ("tas", "mw", "pf", "mlwdf"):
            sch = WeightedScheduler(V=cfg.V if cfg.scheduler in ("tas", "mw") else 0.0)
        elif cfg.scheduler == "edf":
            sch = EDFScheduler()
        elif cfg.scheduler == "rr":
            sch = RoundRobinScheduler(K)
        else:
            raise ValueError(cfg.scheduler)

        silent_until = np.zeros(cfg.M, int)
        pa_x = self.pa_x.copy()
        H = self._channel(pa_x)
        tab = self._tables(H)
        fading = np.isfinite(cfg.rician_K)

        for t in range(cfg.T):
            # 1. arrivals
            A = self.src.step()
            q[:, 0] += A
            if t >= cfg.warmup:
                arrivals += A
            qpk = q.sum(axis=1)

            # (optional) block fading / reactive repositioning -> rebuild tables
            rebuild = False
            if fading and t % cfg.coh_slots == 0 and t > 0:
                rebuild = True
            if cfg.reactive:
                W = qpk + cfg.zeta * Z
                new_x = pa_x.copy()
                for m in range(cfg.M):
                    inseg = (self.users[:, 0] >= self.sw.x0[m]) & (self.users[:, 0] < self.sw.x0[m] + cfg.Ls)
                    cand = np.where(inseg & (qpk > 0))[0]
                    if cand.size:
                        k = cand[np.argmax(W[cand])]
                        new_x[m] = np.clip(self.users[k, 0], self.sw.xlo[m], self.sw.xhi[m])
                moved = np.abs(new_x - pa_x) > 1e-9
                if moved.any():
                    reconf += int(moved.sum())
                    silent_until[moved] = t + cfg.tau_r_slots
                    pa_x = new_x
                    rebuild = True
                silent = silent_until > t
                if rebuild or (silent_until == t).any():
                    H = self._channel(pa_x, silent=silent)
                    tab = self._tables(H)
            elif rebuild:
                H = self._channel(pa_x)
                tab = self._tables(H)

            # 2. scheduling
            if cfg.scheduler == "tas" and cfg.tas_variant == "pkt":
                shift = cfg.zeta * Z / self.creq
                expo = cfg.pkt_scale * a_mlwdf[:, None] * (ages_row + 1.0 + shift[:, None] - cfg.Dmax_slots)
                v = cfg.pkt_floor + np.exp(np.minimum(expo, 50.0))
                if cfg.pkt_pf:
                    v = v / np.maximum(Rbar, 1e-3)[:, None]
                U = PacketValueScheduler.cum_values(q, v, cfg.bmax)
                dec = sch.decide(tab, U, qpk)
            elif cfg.scheduler == "tas":
                if cfg.tas_variant == "qz":
                    Wt = qpk + cfg.zeta * Z
                else:
                    ages = np.arange(H_)
                    hol = np.max(np.where(q > 0, ages[None, :], -1), axis=1) + 1.0
                    eff_age = np.maximum(hol, 0) + cfg.zeta * Z / self.creq
                    if cfg.tas_variant == "holz":
                        Wt = a_mlwdf * eff_age
                    elif cfg.tas_variant == "holz_pf":
                        Wt = a_mlwdf * eff_age / Rbar
                    elif cfg.tas_variant == "exp":
                        x = a_mlwdf * eff_age
                        Wt = np.exp(x / (1.0 + np.sqrt(np.mean(x[qpk > 0]) if (qpk > 0).any() else 0.0))) / Rbar
                    else:
                        raise ValueError(cfg.tas_variant)
                dec = sch.decide(tab, Wt, qpk)
            elif cfg.scheduler == "mw":
                dec = sch.decide(tab, qpk.astype(float), qpk)
            elif cfg.scheduler == "pf":
                dec = sch.decide(tab, 1.0 / Rbar, qpk)
            elif cfg.scheduler == "mlwdf":
                ages = np.arange(H_)
                hol = np.max(np.where(q > 0, ages[None, :], -1), axis=1) + 1.0
                dec = sch.decide(tab, a_mlwdf * np.maximum(hol, 0) / Rbar, qpk)
            elif cfg.scheduler == "edf":
                ages = np.arange(H_)
                hol = np.max(np.where(q > 0, ages[None, :], -1), axis=1)
                dec = sch.decide(tab, hol, qpk, cfg.M)
            else:
                dec = sch.decide(tab, qpk, cfg.M)

            # 3. transmission
            s = np.zeros(K)
            if dec is not None:
                b = dec["b"]
                ok = rng.random(K) < (1.0 - dec["eps"])
                b_ok = np.where(ok, b, 0)
                served = _fifo_remove(q, b_ok)
                q -= served
                s = served.sum(axis=1).astype(float)
                if t >= cfg.warmup:
                    hist[:, 1:] += served  # delay = age + 1
                    decode_fail += (b > 0) & (~ok)
                    power += dec["ptot"]
                    n_sched += (b > 0)
                tx_slots += 1
            Rbar = 0.999 * Rbar + 0.001 * s

            # 4. virtual queues (tail-aware credit)
            Z = np.minimum(np.maximum(Z + self.creq * (qpk > 0) - s, 0.0), self.zcap)
            if t >= cfg.warmup:
                Zsum += Z
                Qsum += q.sum(axis=1)

            # 5. ageing and drop
            if t >= cfg.warmup:
                dropped += q[:, H_ - 1]
            q[:, 1:] = q[:, :-1]
            q[:, 0] = 0

        Teff = cfg.T - cfg.warmup
        late = hist[:, cfg.Dmax_slots + 1:].sum(axis=1)
        viol = dropped + late
        res = dict(
            cfg=cfg.to_dict(),
            users=self.users.tolist(),
            pa_x=pa_x.tolist(),
            creq=self.creq.tolist(),
            arrivals=arrivals.tolist(),
            viol=viol.tolist(),
            dropped=dropped.tolist(),
            late=late.tolist(),
            hist=hist.tolist(),
            decode_fail=decode_fail.tolist(),
            n_sched=n_sched.tolist(),
            avg_power_W=power / Teff,
            avg_Z=(Zsum / Teff).tolist(),
            avg_Q=(Qsum / Teff).tolist(),
            reconf=reconf,
            Teff=Teff,
            pv=float(viol.sum() / max(arrivals.sum(), 1)),
            pv_max=float(np.max(viol / np.maximum(arrivals, 1))),
            snr_agg_dB=(10 * np.log10(self.sw.agg_snr(self.sw.los_channel(self.users, pa_x)))).tolist(),
        )
        return res


def run_config(cfg: SimConfig):
    return Simulator(cfg).run()
