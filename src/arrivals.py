"""Bursty packet-arrival models (slot-level).

1. ON-OFF (interrupted Poisson / Markov-modulated) source:
   two-state Markov chain with ON->OFF rate alpha and OFF->ON rate beta (1/s).
   In the ON state packets arrive as Poisson with h packets per slot
   (peak rate h/Ts packets/s); no arrivals in OFF. Mean rate = h*beta/(alpha+beta).
2. Poisson: memoryless arrivals with the same mean rate (non-bursty baseline).
3. Periodic-with-jitter (industrial control): one batch of B packets every
   period T_p with random jitter, plus event-triggered ON-OFF bursts.

All generators return an integer array (K,) of packets arriving in a slot.
"""
import numpy as np


class OnOffSource:
    def __init__(self, K, Ts, h, alpha, beta, rng, deterministic_on=False):
        self.K, self.Ts = K, Ts
        self.h = np.broadcast_to(np.asarray(h, float), (K,)).copy()
        self.alpha = np.broadcast_to(np.asarray(alpha, float), (K,)).copy()
        self.beta = np.broadcast_to(np.asarray(beta, float), (K,)).copy()
        self.p_on_off = 1 - np.exp(-self.alpha * Ts)
        self.p_off_on = 1 - np.exp(-self.beta * Ts)
        self.rng = rng
        self.det = deterministic_on
        # start in stationary distribution
        p_on = self.beta / (self.alpha + self.beta)
        self.on = rng.random(K) < p_on

    @property
    def mean_rate(self):  # packets per slot
        return self.h * self.beta / (self.alpha + self.beta)

    def step(self):
        u = self.rng.random(self.K)
        new_on = np.where(self.on, u >= self.p_on_off, u < self.p_off_on)
        if self.det:
            a = np.where(self.on, np.round(self.h).astype(int), 0)
        else:
            a = np.where(self.on, self.rng.poisson(self.h), 0)
        self.on = new_on
        return a.astype(int)


class PoissonSource:
    def __init__(self, K, Ts, rate_per_slot, rng):
        self.K = K
        self.lam = np.broadcast_to(np.asarray(rate_per_slot, float), (K,)).copy()
        self.rng = rng

    @property
    def mean_rate(self):
        return self.lam

    def step(self):
        return self.rng.poisson(self.lam).astype(int)


class PeriodicJitterSource:
    """Periodic batches (B packets every T_p slots, jitter +-J slots) plus an
    additive ON-OFF event stream (h_ev, alpha_ev, beta_ev)."""

    def __init__(self, K, Ts, period_slots, batch, jitter_slots, rng,
                 h_ev=0.0, alpha_ev=1.0, beta_ev=1.0):
        self.K = K
        self.T = int(period_slots)
        self.B = int(batch)
        self.J = int(jitter_slots)
        self.rng = rng
        self.next = rng.integers(0, self.T, K)
        self.t = 0
        self.ev = OnOffSource(K, Ts, h_ev, alpha_ev, beta_ev, rng) if h_ev > 0 else None

    @property
    def mean_rate(self):
        m = np.full(self.K, self.B / self.T)
        if self.ev is not None:
            m = m + self.ev.mean_rate
        return m

    def step(self):
        a = np.zeros(self.K, int)
        due = self.next <= self.t
        a[due] = self.B
        self.next[due] += self.T + self.rng.integers(-self.J, self.J + 1, due.sum())
        self.t += 1
        if self.ev is not None:
            a += self.ev.step()
        return a


def beta_for_activity(alpha, activity, Ts):
    """OFF->ON rate giving stationary ON probability `activity` for the slotted chain
    with per-slot transition probabilities 1-exp(-alpha Ts), 1-exp(-beta Ts)."""
    p_on_off = 1 - np.exp(-alpha * Ts)
    p_off_on = p_on_off * activity / (1 - activity)
    return -np.log(1 - p_off_on) / Ts


def required_rate_onoff(h, alpha, beta, Dmax, delta):
    """Tail-latency-aware required service rate for an ON-OFF fluid source
    (peak rate h, ON->OFF alpha, OFF->ON beta; all rates in consistent units):
        c_req = h (beta + Lambda) / (alpha + beta + Lambda),  Lambda = ln(1/delta)/Dmax.
    Obtained from the effective-bandwidth / large-buffer asymptotics
    P(D > Dmax) ~ exp(-theta*(c) c Dmax) with theta*(c) = ((alpha+beta)c - beta h)/(c(h-c)).
    [Derivation to be formalised by the co-author.]"""
    Lam = np.log(1.0 / delta) / Dmax
    return h * (beta + Lam) / (alpha + beta + Lam)
