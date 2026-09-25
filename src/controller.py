"""Slot-level controllers operating on the SWAN action table.

The proposed tail-aware controller (weights="value") maximises, over the
actions (S, A) of the ActionTable and the power levels rho,
    J(a,rho) = value_now(a,rho) + la * value_next(a,rho)
               - V * [n_act(a) P_c + rho P_tx(a)] - V_cfg * (#segments switched on),
where value_now is the expected tail-risk-potential reduction obtainable in the
current slot with the segments that are already usable, and value_next the one
obtainable in the next slot once all segments of the action are ready
(one-step lookahead that lets the controller pay a configuration delay).
Baseline controllers reuse the same machinery with other per-user weights:
  mw      : queue length (throughput-optimal, average-delay oriented)
  mlwdf   : a_k * HoL delay / average rate (Andrews et al. 2001)
  goodput : expected delivered packets (rate maximisation, queue-blind except b<=Q)
  edf     : the users with the oldest HoL packets (channel-agnostic)
"""
import numpy as np
from .fbl import fbl_error


def cum_values(q, v, bmax):
    """q: (K,H) counts by age, v: (K,H) value per packet by age.
    Returns U (K, bmax+1) with U[:,b] = value of the b oldest packets (nan if b > queue)."""
    K, H = q.shape
    cnt = q[:, ::-1]
    val = (q * v)[:, ::-1]
    ccnt = np.cumsum(cnt, axis=1)
    cval = np.cumsum(val, axis=1)
    vrev = v[:, ::-1]
    b = np.arange(1, bmax + 1)
    idx = np.stack([np.searchsorted(ccnt[k], b, side="left") for k in range(K)])
    valid = idx < H
    idxc = np.minimum(idx, H - 1)
    prev_cnt = np.where(idxc > 0, np.take_along_axis(ccnt, np.maximum(idxc - 1, 0), axis=1), 0)
    prev_val = np.where(idxc > 0, np.take_along_axis(cval, np.maximum(idxc - 1, 0), axis=1), 0.0)
    Ub = prev_val + (b[None, :] - prev_cnt) * np.take_along_axis(vrev, idxc, axis=1)
    U = np.zeros((K, bmax + 1))
    U[:, 1:] = np.where(valid, Ub, np.nan)
    return U


class Controller:
    def __init__(self, tab, weights="value", V=0.0, Pc=0.0, V_cfg=0.0, la=1.0, tau_cfg=0.0,
                 edf=False):
        self.tab, self.weights, self.V, self.Pc, self.V_cfg, self.la = tab, weights, V, Pc, V_cfg, la
        self.tau_cfg = tau_cfg
        self.edf = edf
        A = len(tab.acts)
        self.energy = tab.n_act[:, None] * Pc + tab.rho[None, :] * tab.ptx[:, None]  # (A, rho) W
        self._cache_ready = None

    # ---------------------------------------------------------------- errors
    def _errors(self, ready, n_cu):
        """(A, rho, bmax) error table for the usable segments; SA actions with
        partially ready segments are recomputed, others taken from the table."""
        tab = self.tab
        if ready.all() and n_cu == tab.n_eff:
            return tab.E, tab.snr
        snr, _ = tab.sa_snr_usable(ready)
        return tab.error_table(snr, n_cu), snr

    # ---------------------------------------------------------------- decide
    def decide(self, U_now, U_next, qpk, ready, active_prev, t):
        """U_now/U_next: (K, bmax+1) per-user cumulative values (nan beyond queue).
        ready: bool (M,) segments usable now; active_prev: bool (M,) active in t-1."""
        tab = self.tab
        K, M = tab.K, tab.M
        backlog = qpk > 0
        valid = ~(tab.mask & ~backlog[None, :]).any(axis=1)
        if not valid.any():
            return None
        # segments that this action switches on (not active before)
        switch_on = tab.segmask & ~active_prev[None, :]
        n_on = switch_on.sum(axis=1)
        # usable now: segments of the action that are ready; newly switched-on
        # segments are usable now only if tau_cfg < 1 (with reduced blocklength)
        frac = self.tau_cfg - np.floor(self.tau_cfg)
        if self.tau_cfg < 1.0:
            ready_now = np.ones(M, bool)   # everything can be used in this slot
            n_now = int(round(tab.n * (1.0 - frac)))
            E_now_full, _ = self._errors(np.ones(M, bool), tab.n_eff)
            E_now_red = tab.error_table(tab.snr, max(n_now, 1)) if frac > 0 else E_now_full
            # actions switching on a segment use the reduced blocklength
            E_now = np.where((n_on > 0)[:, None, None], E_now_red, E_now_full)
        else:
            E_now, _ = self._errors(ready, tab.n_eff)
        E_next = tab.E  # next slot: all segments of the action ready, full blocklength
        val_now = self._value(E_now, U_now, valid)
        val_next = self._value(E_next, U_next, valid) if self.la > 0 else 0.0
        J = val_now[0] + self.la * (val_next[0] if self.la > 0 else 0.0)
        J = J - self.V * self.energy - self.V_cfg * n_on[:, None]
        J[~valid, :] = -np.inf
        if self.edf:
            # channel-agnostic EDF: restrict to the action serving the users with
            # the oldest HoL packets (SM if >=2 backlogged users, else full SA)
            J = self._edf_mask(J, qpk)
        i = int(np.argmax(J))
        a, r = np.unravel_index(i, J.shape)
        if not np.isfinite(J[a, r]) or (val_now[0][a, r] <= 0 and self.la * (val_next[0][a, r] if self.la > 0 else 0) <= 0):
            return None
        b = np.where(tab.mask[a], val_now[1][a, r], 0)
        eps = np.where(tab.mask[a], E_now[a, r][np.maximum(b, 1) - 1], 0.0)
        return dict(act=a, rho_idx=r, b=b, eps=eps, energy=self.energy[a, r], n_on=int(n_on[a]),
                    segs=tab.segmask[a], kind=tab.acts[a]["kind"], j=int(tab.j[a]))

    def _value(self, E, U, valid):
        """Returns (J_val (A, rho), b* (A, rho, K)) for the chosen weighting."""
        tab = self.tab
        succ = 1.0 - E                                  # (A, rho, B)
        valid_b = ~np.isnan(U[:, 1:])                   # (K, B)
        Uc = np.nan_to_num(U[:, 1:], nan=0.0)
        if self.weights == "goodput":
            Uc = np.where(valid_b, np.arange(1, tab.bmax + 1)[None, :], 0.0)
        val = succ[:, :, None, :] * Uc[None, None, :, :]  # (A, rho, K, B)
        val = np.where(valid_b[None, None, :, :], val, -1e30)
        best = val.max(axis=3)
        barg = val.argmax(axis=3) + 1
        best = np.where(tab.mask[:, None, :], np.maximum(best, 0.0), 0.0)
        return best.sum(axis=2), barg

    def _edf_mask(self, J, qpk):
        tab = self.tab
        hol = self._hol
        order = np.argsort(-(hol + 1e-3 * qpk) * (qpk > 0))
        chosen = [k for k in order[: tab.M] if qpk[k] > 0]
        target = np.zeros(tab.K, bool); target[chosen] = True
        if len(chosen) == 1:
            sel = tab.is_sa & (tab.sa_user == chosen[0]) & (tab.j == tab.M)
        else:
            sel = (tab.mask == target[None, :]).all(axis=1) & ~tab.is_sa
        J2 = np.full_like(J, -np.inf); J2[sel] = J[sel]
        return J2


def user_weight_values(weights, q, ages_row, Dmax, a_k, kappa, Rbar, Z=None, zeta=0.0, creq=None,
                       pkt_floor=0.0):
    """Per-packet value matrix v (K, H) for the different weightings.
    value: exp(kappa a_k (age + 1 + shift - Dmax)); mw: 1 per packet (queue length);
    mlwdf: a_k * (HoL + 1) / Rbar per packet; goodput: handled in Controller."""
    K, H = q.shape
    if weights == "value":
        shift = np.zeros(K) if Z is None else zeta * Z / np.maximum(creq, 1e-9)
        # value saturates at the deadline: a packet that has already missed it is
        # worth as much as one at the deadline, not more
        expo = kappa * a_k[:, None] * np.minimum(ages_row + 1.0 + shift[:, None] - Dmax, 0.0)
        return pkt_floor + np.exp(expo)
    if weights in ("mw", "goodput", "edf"):
        return np.ones((K, H))
    if weights == "mlwdf":
        hol = np.max(np.where(q > 0, ages_row, -1), axis=1) + 1.0
        w = a_k * np.maximum(hol, 0) / np.maximum(Rbar, 1e-3)
        return np.repeat(w[:, None], H, axis=1)
    if weights == "pf":
        return np.repeat((1.0 / np.maximum(Rbar, 1e-3))[:, None], H, axis=1)
    raise ValueError(weights)
