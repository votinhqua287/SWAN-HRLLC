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
    # index of the bin containing the b-th oldest packet (vectorised searchsorted)
    idx = (ccnt[:, :, None] < b[None, None, :]).sum(axis=1)
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
        ready: bool (M,) segments usable now; active_prev: bool (M,) active in t-1.
        Only actions whose users are all backlogged are evaluated (pruning)."""
        tab = self.tab
        K, M = tab.K, tab.M
        backlog = qpk > 0
        valid = ~(tab.mask & ~backlog[None, :]).any(axis=1)
        if not valid.any():
            return None
        idx = np.where(valid)[0]                     # candidate actions
        kb = np.where(backlog)[0]                    # backlogged users
        mask_v = tab.mask[idx][:, kb]                # (Av, Kb)
        segmask_v = tab.segmask[idx]                 # (Av, M)
        switch_on = segmask_v & ~active_prev[None, :]
        n_on = switch_on.sum(axis=1)
        frac = self.tau_cfg - np.floor(self.tau_cfg)
        if self.tau_cfg < 1.0:
            E_full = tab.E[idx]
            if frac > 0:
                n_now = int(round(tab.n * (1.0 - frac)))
                if self._cache_ready is None:
                    self._cache_ready = tab.error_table(tab.snr, max(n_now, 1))
                E_red = self._cache_ready[idx]
                E_now = np.where((n_on > 0)[:, None, None], E_red, E_full)
            else:
                E_now = E_full
        else:
            E_all, _ = self._errors(ready, tab.n_eff)
            E_now = E_all[idx]
        E_next = tab.E[idx]
        val_now, b_now = self._value(E_now, U_now[kb], mask_v)
        if self.la > 0:
            val_next, _ = self._value(E_next, U_next[kb], mask_v)
        else:
            val_next = 0.0
        J = val_now + self.la * val_next
        J = J - self.V * self.energy[idx] - self.V_cfg * n_on[:, None]
        if self.edf:
            J = self._edf_mask_v(J, qpk, idx)
        i = int(np.argmax(J))
        a_v, r = np.unravel_index(i, J.shape)
        if not np.isfinite(J[a_v, r]) or (val_now[a_v, r] <= 0 and (self.la * val_next[a_v, r] if self.la > 0 else 0) <= 0):
            return None
        a = int(idx[a_v])
        b = np.zeros(K, int); b[kb] = np.where(mask_v[a_v], b_now[a_v, r], 0)
        eps = np.where(tab.mask[a], E_now[a_v, r][np.maximum(b, 1) - 1], 0.0)
        return dict(act=a, rho_idx=r, b=b, eps=eps, energy=self.energy[a, r], n_on=int(n_on[a_v]),
                    segs=tab.segmask[a], kind=tab.acts[a]["kind"], j=int(tab.j[a]))

    def _value(self, E, U, mask_v):
        """E: (Av, rho, B) errors, U: (Kb, B+1) cumulative values, mask_v: (Av, Kb).
        Returns (J_val (Av, rho), b* (Av, rho, Kb))."""
        tab = self.tab
        succ = 1.0 - E                                  # (Av, rho, B)
        valid_b = ~np.isnan(U[:, 1:])                   # (Kb, B)
        Uc = np.nan_to_num(U[:, 1:], nan=0.0)
        if self.weights == "goodput":
            Uc = np.where(valid_b, np.arange(1, tab.bmax + 1)[None, :], 0.0)
        val = succ[:, :, None, :] * Uc[None, None, :, :]  # (Av, rho, Kb, B)
        val = np.where(valid_b[None, None, :, :], val, -1e30)
        best = val.max(axis=3)
        barg = val.argmax(axis=3) + 1
        best = np.where(mask_v[:, None, :], np.maximum(best, 0.0), 0.0)
        return best.sum(axis=2), barg

    def _edf_mask_v(self, J, qpk, idx):
        tab = self.tab
        hol = self._hol
        order = np.argsort(-(hol + 1e-3 * qpk) * (qpk > 0))
        chosen = [k for k in order[: tab.M] if qpk[k] > 0]
        target = np.zeros(tab.K, bool); target[chosen] = True
        if len(chosen) == 1:
            sel = tab.is_sa & (tab.sa_user == chosen[0]) & (tab.j == tab.M)
        else:
            sel = (tab.mask == target[None, :]).all(axis=1) & ~tab.is_sa
        sel_v = sel[idx]
        J2 = np.full_like(J, -np.inf); J2[sel_v] = J[sel_v]
        return J2

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
    if weights == "mw":   # max-weight: every packet of user k weighs its queue length Q_k
        return np.repeat(q.sum(axis=1, keepdims=True).astype(float), H, axis=1)
    if weights in ("goodput", "edf"):
        return np.ones((K, H))
    if weights == "mlwdf":
        hol = np.max(np.where(q > 0, ages_row, -1), axis=1) + 1.0
        w = a_k * np.maximum(hol, 0) / np.maximum(Rbar, 1e-3)
        return np.repeat(w[:, None], H, axis=1)
    if weights == "pf":
        return np.repeat((1.0 / np.maximum(Rbar, 1e-3))[:, None], H, axis=1)
    raise ValueError(weights)
