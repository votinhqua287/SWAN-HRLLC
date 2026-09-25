"""Frame-level pinching-antenna placement algorithms for SWAN.

TAPP  : tail-aware PA placement, maximises the minimum tail-latency margin
        min_k  R_k^agg(x) / c_req,k   (block-coordinate descent, 1-D grid search)
SUMRATE: maximises sum_k R_k^agg(x)      (same BCD machinery)
CENTER : PAs at the segment centres (fixed, non-reconfigurable benchmark)
NEAREST: each PA above the projection of the closest user (heuristic)
"""
import numpy as np
from .fbl import fbl_rate


def agg_rate_packets(sw, users, pa_x, n, eps0, L, j=None):
    """FBL rate (packets/slot) of every user when served by its j strongest
    segments in aggregation mode (j=None: all segments)."""
    H = sw.los_channel(users, pa_x)
    if j is None or j >= sw.M:
        g = sw.agg_snr(H)
    else:
        a = np.sort(np.abs(H), axis=1)[:, ::-1][:, :j].sum(axis=1)
        g = sw.Pmax * a ** 2 / sw.sigma2
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


def place_tapp(sw, users, c_req, n, eps0, L, grid=200, x_init=None, return_hist=False, j=None):
    """Tail-aware placement: max_x min_k R_k^(j)(x)/c_req_k, with R^(j) the rate
    from the j strongest segments (j=None: full aggregation)."""
    c_req = np.asarray(c_req, float)

    def obj(x):
        return np.min(agg_rate_packets(sw, users, x, n, eps0, L, j) / c_req)

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


def place_maxmin_rate(sw, users, n, eps0, L, grid=200, j=None):
    """Max-min (tail-agnostic) placement: max_x min_k R_k^(j)(x)."""
    return place_tapp(sw, users, np.ones(len(users)), n, eps0, L, grid, j=j)


def place_load(sw, users, c_req, n, eps0, L, grid=200, x_init=None, j=None, return_hist=False):
    """Tail-load placement: min_x sum_k c_req_k / R_k^(j)(x) (tail-latency-aware
    utilisation, i.e. the time share needed to drain every user at its required rate)."""
    c_req = np.asarray(c_req, float)

    def obj(x):
        R = np.maximum(agg_rate_packets(sw, users, x, n, eps0, L, j), 1e-6)
        return -np.sum(c_req / R)

    x0 = sw.x0 + sw.Ls / 2 if x_init is None else x_init
    x, best, hist = _bcd(sw, users, obj, x0, grid)
    return (x, best, hist) if return_hist else x
