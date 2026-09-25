"""SWAN service model: the set of actions available to the controller in a slot.

An action is a pair (user subset S, active-segment set A) with a power level rho:
  * SA(k, j): user k alone, the j segments with the largest |h_{k,m}| aggregated
    (equal-gain transmission, phase aligned).  j = 1 is segment selection (SS),
    j = M is full-segment aggregation.
  * SM(S):    users in S (|S| >= 2) multiplexed by equal-SNR zero-forcing over all
    M segments (the full array is needed for the spatial degrees of freedom).
Every action has a transmit power P_tx (W, at rho = 1), a number of active
segments n_act (each consuming the circuit power P_c of its RF chain) and, for
SA actions, the ordered segment list so that the SNR can be recomputed when
some of the segments are not yet ready after (re)activation.
"""
from itertools import combinations
import numpy as np
from .fbl import fbl_error


class ActionTable:
    def __init__(self, sw, H, n, L, bmax, rho_levels=(1.0,), n_eff=None, sa_only=False,
                 fixed_j=None, shannon=False):
        self.sw, self.n, self.L, self.bmax = sw, n, L, bmax
        self.n_eff = n if n_eff is None else n_eff
        self.rho = np.asarray(rho_levels, float)
        self.shannon = shannon
        K, M = H.shape
        self.K, self.M = K, M
        absH = np.abs(H)
        # ---- SA actions ------------------------------------------------
        order = np.argsort(-absH, axis=1)           # (K, M) segments by gain
        js = [fixed_j] if fixed_j is not None else list(range(1, M + 1))
        acts = []
        for k in range(K):
            for j in js:
                segs = order[k, :j]
                amp = absH[k, segs].sum()
                acts.append(dict(kind="SA", users=(k,), segs=tuple(int(m) for m in segs), j=j,
                                 snr=sw.Pmax * amp ** 2 / sw.sigma2, ptx=j * sw.Pmax, n_act=j))
        # ---- SM actions ------------------------------------------------
        if not sa_only:
            for s in range(2, M + 1):
                for comb in combinations(range(K), s):
                    g, p = sw.zf_snr(H[list(comb), :])
                    if g <= 0:
                        continue
                    acts.append(dict(kind="SM", users=comb, segs=tuple(range(M)), j=M,
                                     snr=g, ptx=p, n_act=M))
        self.acts = acts
        A = len(acts)
        self.mask = np.zeros((A, K), bool)
        self.segmask = np.zeros((A, M), bool)
        for i, a in enumerate(acts):
            self.mask[i, list(a["users"])] = True
            self.segmask[i, list(a["segs"])] = True
        self.snr = np.array([a["snr"] for a in acts])
        self.ptx = np.array([a["ptx"] for a in acts])
        self.n_act = np.array([a["n_act"] for a in acts])
        self.is_sa = np.array([a["kind"] == "SA" for a in acts])
        self.j = np.array([a["j"] for a in acts])
        self.sa_user = np.array([a["users"][0] if a["kind"] == "SA" else -1 for a in acts])
        self.absH = absH
        self.order = order
        self.E = self.error_table(self.snr, self.n_eff)   # (A, rho, bmax)

    def error_table(self, snr, n_cu):
        b = np.arange(1, self.bmax + 1)
        R = b * self.L / float(n_cu)
        g = snr[:, None, None] * self.rho[None, :, None]
        if self.shannon:
            return np.where(R[None, None, :] <= np.log2(1.0 + g), 0.0, 1.0)
        return fbl_error(n_cu, R[None, None, :], g)

    def sa_snr_usable(self, ready):
        """SNR of every SA action when only the segments in `ready` (bool (M,)) are
        usable; SM actions require all segments and get snr 0 otherwise."""
        usable = self.segmask & ready[None, :]
        amp = (self.absH[np.maximum(self.sa_user, 0)] * usable).sum(axis=1)
        snr = np.where(self.is_sa, self.sw.Pmax * amp ** 2 / self.sw.sigma2,
                       np.where(ready.all(), self.snr, 0.0))
        return snr, usable
