"""Frame-level pinching-antenna placement algorithms for SWAN.

TAPP  : tail-aware PA placement, maximises the minimum tail-latency margin
        min_k  R_k^agg(x) / c_req,k   (block-coordinate descent, 1-D grid search)
SUMRATE: maximises sum_k R_k^agg(x)      (same BCD machinery)
CENTER : PAs at the segment centres (fixed, non-reconfigurable benchmark)
NEAREST: each PA above the projection of the closest user (heuristic)
"""
import numpy as np
from .fbl import fbl_rate


def agg_rate_packets(sw, users, pa_x, n, eps0, L):
    """Aggregation-mode FBL rate of every user in packets/slot."""
    H = sw.los_channel(users, pa_x)
    g = sw.agg_snr(H)
    return n * fbl_rate(n, eps0, g) / L


def _bcd(sw, users, objective, x_init, grid=200, max_iter=30, tol=1e-9):
    x = x_init.copy()
    best = objective(x)
    hist = [best]
    for it in range(max_iter):
        improved = False
        for m in range(sw.M):
            cand = np.linspace(sw.xlo[m], sw.xhi[m], grid)
            vals = np.empty(grid)
            for i, c in enumerate(cand):
                xt = x.copy()
                xt[m] = c
                vals[i] = objective(xt)
            i = int(np.argmax(vals))
            if vals[i] > best + tol:
                x[m] = cand[i]
                best = vals[i]
                improved = True
        hist.append(best)
        if not improved:
            break
    return x, best, np.array(hist)


def place_tapp(sw, users, c_req, n, eps0, L, grid=200, x_init=None, return_hist=False):
    """Tail-aware placement: max_x min_k R_k^agg(x)/c_req_k."""
    c_req = np.asarray(c_req, float)

    def obj(x):
        return np.min(agg_rate_packets(sw, users, x, n, eps0, L) / c_req)

    x0 = sw.x0 + sw.Ls / 2 if x_init is None else x_init
    x, best, hist = _bcd(sw, users, obj, x0, grid)
    return (x, best, hist) if return_hist else x


def place_sumrate(sw, users, n, eps0, L, grid=200, x_init=None):
    def obj(x):
        return np.sum(agg_rate_packets(sw, users, x, n, eps0, L))

    x0 = sw.x0 + sw.Ls / 2 if x_init is None else x_init
    x, best, hist = _bcd(sw, users, obj, x0, grid)
    return x


def place_center(sw, users=None):
    return sw.x0 + sw.Ls / 2


def place_nearest(sw, users):
    """Each segment's PA moves above the user closest to the segment (clipped)."""
    x = place_center(sw)
    users = np.asarray(users, float)
    for m in range(sw.M):
        c = sw.x0[m] + sw.Ls / 2
        dist = np.hypot(users[:, 0] - c, users[:, 1])
        k = int(np.argmin(dist))
        x[m] = np.clip(users[k, 0], sw.xlo[m], sw.xhi[m])
    return x


def place_maxmin_rate(sw, users, n, eps0, L, grid=200):
    """Max-min (tail-agnostic) placement: max_x min_k R_k^agg(x)."""
    return place_tapp(sw, users, np.ones(len(users)), n, eps0, L, grid)
