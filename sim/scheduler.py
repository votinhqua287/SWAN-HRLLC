"""Slot-level schedulers operating on precomputed subset tables.

A 'table' (from build_tables) holds, for every user subset S (|S|<=M) and
power level rho_i:  G[S, i, q] = max_{b<=q} b (1 - eps(b L / n, rho_i gamma(S)))
i.e. the best expected goodput (in packets) a user with q packets can get in
the subset.  All schedulers return (chosen subset mask, b per user, rho index).
"""
import numpy as np
from .fbl import fbl_error


def build_tables(sw, H, n, L, bmax=8, rho_levels=(1.0,), n_eff=None):
    tab = sw.subset_tables(H)
    n_eff = n if n_eff is None else n_eff
    rho = np.asarray(rho_levels, float)
    b = np.arange(1, bmax + 1)
    R = b * L / float(n_eff)  # bits per channel use
    snr = tab["snr"][:, None, None] * rho[None, :, None]  # (S,rho,1)
    eps = fbl_error(n_eff, R[None, None, :], snr)  # (S,rho,B)
    good = b[None, None, :] * (1.0 - eps)
    # best goodput with at most q packets available, q=0..bmax
    G = np.zeros(good.shape[:2] + (bmax + 1,))
    B = np.zeros(good.shape[:2] + (bmax + 1,), int)
    E = np.zeros(good.shape[:2] + (bmax + 1,))
    for q in range(1, bmax + 1):
        j = np.argmax(good[:, :, :q], axis=2)
        G[:, :, q] = np.take_along_axis(good[:, :, :q], j[:, :, None], axis=2)[:, :, 0]
        B[:, :, q] = j + 1
        E[:, :, q] = np.take_along_axis(eps[:, :, :q], j[:, :, None], axis=2)[:, :, 0]
    tab.update(G=G, B=B, E=E, E_raw=eps, rho=rho, bmax=bmax)
    return tab


class WeightedScheduler:
    """Maximises sum_{k in S} W_k G_k(S,rho) - V rho P_tot(S) over all subsets.
    Weights are supplied per slot by the caller (Q, Q+Z, 1/Rbar, ...)."""

    def __init__(self, V=0.0):
        self.V = V

    def decide(self, tab, W, qpk):
        K = W.size
        qcap = np.minimum(qpk, tab["bmax"])
        active = qpk > 0
        mask = tab["mask"]
        # subsets containing an empty user are invalid
        valid = ~(mask & ~active[None, :]).any(axis=1)
        if not valid.any():
            return None
        Gk = tab["G"][:, :, qcap]  # (S, rho, K)
        J = (Gk * (mask[:, None, :] * W[None, None, :])).sum(axis=2)  # (S, rho)
        J = J - self.V * tab["rho"][None, :] * tab["ptot"][:, None]
        J[~valid, :] = -np.inf
        i = int(np.argmax(J))
        s, r = np.unravel_index(i, J.shape)
        if J[s, r] <= 0:
            return None
        b = np.where(mask[s], tab["B"][s, r, qcap], 0)
        eps = np.where(mask[s], tab["E"][s, r, qcap], 0.0)
        return dict(sub=s, rho_idx=r, b=b, eps=eps, ptot=tab["rho"][r] * tab["ptot"][s])


class EDFScheduler:
    """Earliest-deadline-first: serve the M users with the oldest HoL packet
    (channel-agnostic), full power, best FBL packet count."""

    def decide(self, tab, hol_age, qpk, M):
        qcap = np.minimum(qpk, tab["bmax"])
        active = qpk > 0
        if not active.any():
            return None
        order = np.argsort(-(hol_age + 1e-3 * qpk) * active)
        chosen = [k for k in order[:M] if active[k]]
        mask = tab["mask"]
        target = np.zeros(mask.shape[1], bool)
        target[chosen] = True
        s = int(np.where((mask == target[None, :]).all(axis=1))[0][0])
        r = len(tab["rho"]) - 1  # full power (rho levels sorted ascending)
        b = np.where(mask[s], tab["B"][s, r, qcap], 0)
        eps = np.where(mask[s], tab["E"][s, r, qcap], 0.0)
        return dict(sub=s, rho_idx=r, b=b, eps=eps, ptot=tab["rho"][r] * tab["ptot"][s])


class RoundRobinScheduler:
    def __init__(self, K):
        self.ptr = 0
        self.K = K

    def decide(self, tab, qpk, M):
        qcap = np.minimum(qpk, tab["bmax"])
        active = np.where(qpk > 0)[0]
        if active.size == 0:
            return None
        order = np.roll(np.arange(self.K), -self.ptr)
        chosen = [k for k in order if qpk[k] > 0][:M]
        self.ptr = (chosen[-1] + 1) % self.K
        mask = tab["mask"]
        target = np.zeros(self.K, bool)
        target[chosen] = True
        s = int(np.where((mask == target[None, :]).all(axis=1))[0][0])
        r = len(tab["rho"]) - 1
        b = np.where(mask[s], tab["B"][s, r, qcap], 0)
        eps = np.where(mask[s], tab["E"][s, r, qcap], 0.0)
        return dict(sub=s, rho_idx=r, b=b, eps=eps, ptot=tab["rho"][r] * tab["ptot"][s])


class PacketValueScheduler:
    """Tail-aware packet-value scheduler.  Every queued packet of user k with
    age a (slots) carries a value v_k(a) = floor + exp(a_k (a + 1 + shift_k - Dmax)),
    a_k = ln(1/delta_k)/Dmax.  For a subset S at power level rho the scheduler
    picks for each user the packet count b maximising (1-eps_k(b,S,rho)) U_k(b),
    where U_k(b) is the value of the b oldest packets, and chooses the subset
    maximising the sum of these values minus V rho P_tot(S)."""

    def __init__(self, V=0.0):
        self.V = V

    @staticmethod
    def cum_values(q, v, bmax):
        """q: (K,H) counts by age, v: (K,H) value per packet by age.
        Returns U (K, bmax+1) with U[:,b] = value of the b oldest packets."""
        K, H = q.shape
        cnt = q[:, ::-1]           # oldest first
        val = (q * v)[:, ::-1]
        ccnt = np.cumsum(cnt, axis=1)
        cval = np.cumsum(val, axis=1)
        vrev = v[:, ::-1]
        U = np.zeros((K, bmax + 1))
        b = np.arange(1, bmax + 1)
        # index of the bin containing the b-th oldest packet
        idx = np.stack([np.searchsorted(ccnt[k], b, side="left") for k in range(K)])  # (K,bmax)
        valid = idx < H
        idxc = np.minimum(idx, H - 1)
        prev_cnt = np.where(idxc > 0, np.take_along_axis(ccnt, np.maximum(idxc - 1, 0), axis=1), 0)
        prev_val = np.where(idxc > 0, np.take_along_axis(cval, np.maximum(idxc - 1, 0), axis=1), 0.0)
        Ub = prev_val + (b[None, :] - prev_cnt) * np.take_along_axis(vrev, idxc, axis=1)
        U[:, 1:] = np.where(valid, Ub, np.nan)
        return U

    def decide(self, tab, U, qpk):
        K = qpk.size
        bmax = tab["bmax"]
        mask = tab["mask"]
        active = qpk > 0
        valid = ~(mask & ~active[None, :]).any(axis=1)
        if not valid.any():
            return None
        valid_b = ~np.isnan(U[:, 1:])                        # (K, bmax): b <= queue length
        Uc = np.nan_to_num(U[:, 1:], nan=0.0)
        succ = 1.0 - tab["E_raw"]                            # (S, rho, bmax)
        val = succ[:, :, None, :] * Uc[None, None, :, :]     # (S, rho, K, bmax)
        val = np.where(valid_b[None, None, :, :], val, -1e30)
        best = val.max(axis=3)                               # (S, rho, K)
        barg = val.argmax(axis=3) + 1
        best = np.where(mask[:, None, :] & active[None, None, :], np.maximum(best, 0.0), 0.0)
        J = best.sum(axis=2) - self.V * tab["rho"][None, :] * tab["ptot"][:, None]
        J[~valid, :] = -np.inf
        i = int(np.argmax(J))
        s, r = np.unravel_index(i, J.shape)
        if not np.isfinite(J[s, r]) or J[s, r] <= 0:
            return None
        b = np.where(mask[s], barg[s, r], 0)
        eps = np.where(mask[s], tab["E_raw"][s, r][np.maximum(b, 1) - 1], 0.0)
        return dict(sub=s, rho_idx=r, b=b, eps=eps, ptot=tab["rho"][r] * tab["ptot"][s])
