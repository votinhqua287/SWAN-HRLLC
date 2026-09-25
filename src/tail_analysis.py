"""Numerical tail analysis (Route A of the research guide): effective bandwidth
of the bursty source, effective capacity of the FBL service, QoS exponent and
the resulting exponential approximation of the delay-violation probability.
All quantities are per slot; delays are in slots.

The derivations that justify these formulas in the paper's notation are the
co-author's task (Lemma 1, Theorem 2); this module provides the numbers.
"""
import numpy as np
from scipy.optimize import brentq
from .fbl import fbl_error


def eb_onoff_discrete(theta, h, p_on_off, p_off_on):
    """Effective bandwidth (packets/slot) of a discrete-time ON-OFF source with
    Poisson(h) packets per ON slot: (1/theta) log sp(P diag(1, e^{h(e^theta-1)}))."""
    P = np.array([[1 - p_off_on, p_off_on], [p_on_off, 1 - p_on_off]])  # states OFF, ON
    c = h * (np.exp(theta) - 1.0)          # log of the ON-state arrival MGF
    if c > 500.0:                          # asymptotic regime: sp ~ (1-p_on_off) e^c
        return (c + np.log(1 - p_on_off)) / theta
    D = np.diag([1.0, np.exp(c)])
    sp = np.max(np.abs(np.linalg.eigvals(P @ D)))
    return np.log(sp) / theta


def eb_onoff_fluid(theta, h, alpha, beta):
    """Kelly's closed form for the two-state Markov fluid source (same units as h)."""
    x = h * theta - alpha - beta
    return (x + np.sqrt(x * x + 4 * beta * h * theta)) / (2 * theta)


def ec_iid_service(theta, b, eps):
    """Effective capacity of an i.i.d. service delivering b packets w.p. 1-eps."""
    return -np.log(eps + (1 - eps) * np.exp(-theta * b)) / theta


def qos_exponent(eb, ec, theta_max=8.0):
    """Largest theta>0 with eb(theta) <= ec(theta); returns 0 if none (unstable)."""
    f = lambda th: ec(th) - eb(th)
    grid = np.logspace(-4, np.log10(theta_max), 400)
    vals = np.array([f(g) for g in grid])
    if vals[0] <= 0:
        return 0.0
    idx = np.where(vals <= 0)[0]
    if idx.size == 0:
        return grid[-1]
    i = idx[0]
    return brentq(f, grid[i - 1], grid[i])


def tail_approx(Dmax_slots, eb, ec, prefactor=1.0):
    """P(D > Dmax) ~ prefactor * exp(-theta* EB(theta*) Dmax)."""
    th = qos_exponent(eb, ec)
    if th <= 0:
        return 1.0
    return prefactor * np.exp(-th * eb(th) * Dmax_slots)


def single_user_fixed_sa(h, alpha, beta, Ts, snr, n, L, bmax, Dmax_slots, delta=None):
    """Tail approximation for one ON-OFF device served every slot in full SA mode
    with the goodput-maximising bundle at SNR `snr` (Route A, i.i.d. FBL service).
    Returns dict(theta, b, eps, pv_approx, pv_creq_bound)."""
    p_on_off = 1 - np.exp(-alpha * Ts); p_off_on = 1 - np.exp(-beta * Ts)
    b = np.arange(1, bmax + 1)
    eps = fbl_error(n, b * L / n, snr)
    good = b * (1 - eps)
    i = int(np.argmax(good)); b_star, eps_star = int(b[i]), float(eps[i])
    eb = lambda th: eb_onoff_discrete(th, h, p_on_off, p_off_on)
    ec = lambda th: ec_iid_service(th, b_star, eps_star)
    th = qos_exponent(eb, ec)
    pv = tail_approx(Dmax_slots, eb, ec)
    return dict(theta=th, b=b_star, eps=eps_star, pv_approx=pv)


def percentiles_from_hist(hist, dropped, Ddrop, probs=(0.99, 0.999, 0.9999, 0.99999)):
    """Delay percentiles (slots) from a delivered-delay histogram (index=delay) and
    a count of discarded packets (delay treated as Ddrop+1)."""
    h = np.asarray(hist, float).copy()
    h = np.append(h, dropped)
    cdf = np.cumsum(h) / h.sum()
    out = {}
    for p in probs:
        idx = int(np.searchsorted(cdf, p))
        out[p] = idx
    return out


def cvar_from_hist(hist, dropped, alpha=0.999):
    h = np.append(np.asarray(hist, float), dropped)
    d = np.arange(h.size)
    cdf = np.cumsum(h) / h.sum()
    var = int(np.searchsorted(cdf, alpha))
    tail = h[var:]
    return float((tail * d[var:]).sum() / max(tail.sum(), 1e-12))
