"""Finite-blocklength (FBL) utilities.

Normal approximation of the maximal coding rate (Polyanskiy-Poor-Verdu 2010):
    R(n, eps, gamma) = C(gamma) - sqrt(V(gamma)/n) Q^{-1}(eps) + log2(n)/(2n)
with C = log2(1+gamma), V = (1 - (1+gamma)^-2) (log2 e)^2.
The decoding error probability of a codeword of n channel uses carrying
R bits/cu is eps(n, R, gamma) = Q( sqrt(n/V) * (C - R + log2(n)/(2n)) ).
"""
import numpy as np
from scipy.special import erfc, erfcinv

LOG2E = np.log2(np.e)


def qfunc(x):
    return 0.5 * erfc(np.asarray(x, dtype=float) / np.sqrt(2.0))


def qfunc_inv(p):
    return np.sqrt(2.0) * erfcinv(2.0 * np.asarray(p, dtype=float))


def capacity(gamma):
    return np.log2(1.0 + gamma)


def dispersion(gamma):
    return (1.0 - (1.0 + gamma) ** (-2.0)) * LOG2E ** 2


def fbl_error(n, R, gamma):
    """Decoding error probability for rate R (bits/cu), blocklength n, SNR gamma.

    All arguments broadcast. Returns values in [0,1]."""
    gamma = np.asarray(gamma, dtype=float)
    R = np.asarray(R, dtype=float)
    n = np.asarray(n, dtype=float)
    C = capacity(gamma)
    V = dispersion(gamma)
    with np.errstate(divide="ignore", invalid="ignore"):
        arg = np.sqrt(n / np.maximum(V, 1e-300)) * (C - R + np.log2(n) / (2.0 * n))
    eps = qfunc(arg)
    # gamma -> 0: V -> 0; error is 1 if R > 0
    eps = np.where(V <= 1e-300, np.where(R > 0, 1.0, 0.0), eps)
    return np.clip(eps, 0.0, 1.0)


def fbl_rate(n, eps, gamma):
    """Maximal rate (bits/cu) at blocklength n and target error eps."""
    gamma = np.asarray(gamma, dtype=float)
    C = capacity(gamma)
    V = dispersion(gamma)
    R = C - np.sqrt(V / n) * qfunc_inv(eps) + np.log2(n) / (2.0 * n)
    return np.maximum(R, 0.0)


def best_packets(n, gamma, L, qmax, weight=None):
    """Number of L-bit packets b in {0..qmax} maximising expected goodput
    b*L*(1-eps(n, bL/n, gamma)).  Vectorised over gamma (1-D array).

    Returns (b_opt, goodput_opt, eps_opt) arrays of the same shape as gamma.
    qmax may be an int or an array (packets in the queue)."""
    gamma = np.atleast_1d(np.asarray(gamma, dtype=float))
    qmax = np.broadcast_to(np.asarray(qmax, dtype=int), gamma.shape)
    bmax = int(qmax.max()) if qmax.size else 0
    if bmax == 0:
        z = np.zeros_like(gamma)
        return z.astype(int), z, z
    b = np.arange(1, bmax + 1)[None, :]  # (1,B)
    R = b * L / float(n)
    eps = fbl_error(n, R, gamma[:, None])
    good = b * L * (1.0 - eps)
    good = np.where(b <= qmax[:, None], good, -np.inf)
    idx = np.argmax(good, axis=1)
    b_opt = b[0, idx]
    g_opt = good[np.arange(gamma.size), idx]
    e_opt = eps[np.arange(gamma.size), idx]
    b_opt = np.where(g_opt > 0, b_opt, 0)
    g_opt = np.where(g_opt > 0, g_opt, 0.0)
    return b_opt, g_opt, e_opt
