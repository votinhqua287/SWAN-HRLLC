"""Segmented waveguide-enabled pinching-antenna system (SWAN): geometry,
channel model, precoding, and per-subset SNR tables.

Geometry (downlink):
  * M waveguide segments placed end-to-end along the x-axis at height d.
    Segment m (0-based) spans [m*Ls, (m+1)*Ls]; its feed point is at the
    left end x0_m = m*Ls and is connected to the BS by an individual RF chain.
  * One pinching antenna (PA) is activated per segment at x_m in
    [x0_m + margin, x0_m + Ls - margin].
  * K single-antenna users on the ground plane at (xk, yk, 0).

Channel from the PA of segment m to user k (free-space LoS + in-waveguide phase):
  h_{k,m} = sqrt(eta) / r_{k,m} * exp(-j 2 pi r_{k,m} / lambda)
            * exp(-j 2 pi n_eff (x_m - x0_m) / lambda) * exp(-alpha_g (x_m-x0_m)/2)
  eta = c^2 / (16 pi^2 fc^2),  r_{k,m} = sqrt((xk-x_m)^2 + yk^2 + d^2).
alpha_g is an optional in-waveguide power attenuation (Np/m); default 0.

Optional small-scale fading: Rician with K-factor kappa, i.e.
  h = sqrt(kappa/(1+kappa)) h_LoS + sqrt(1/(1+kappa)) |h_LoS| g,  g ~ CN(0,1).
"""
from itertools import combinations
import numpy as np

C0 = 3e8


class SWAN:
    def __init__(self, M=4, Ls=10.0, d=3.0, Dy=10.0, fc=28e9, n_eff=1.4,
                 alpha_g_dBpm=0.0, margin=0.1, sigma2_dBm=-107.0,
                 Pmax_dBm=-10.0, rician_K=np.inf, rng=None):
        self.M, self.Ls, self.d, self.Dy = M, Ls, d, Dy
        self.Dx = M * Ls
        self.fc, self.n_eff = fc, n_eff
        self.lam = C0 / fc
        self.lam_g = self.lam / n_eff
        self.eta = C0 ** 2 / (16 * np.pi ** 2 * fc ** 2)
        self.alpha_g = alpha_g_dBpm / 10.0 * np.log(10.0)  # Np/m (power)
        self.margin = margin
        self.sigma2 = 10 ** ((sigma2_dBm - 30) / 10)  # W
        self.Pmax = 10 ** ((Pmax_dBm - 30) / 10)  # W per segment
        self.rician_K = rician_K
        self.rng = np.random.default_rng() if rng is None else rng
        self.x0 = np.arange(M) * Ls  # feed points
        self.xlo = self.x0 + margin
        self.xhi = self.x0 + Ls - margin

    # ------------------------------------------------------------------ users
    def drop_users(self, K, rng=None):
        rng = self.rng if rng is None else rng
        xs = rng.uniform(0.0, self.Dx, K)
        ys = rng.uniform(-self.Dy / 2, self.Dy / 2, K)
        return np.stack([xs, ys], axis=1)

    # ---------------------------------------------------------------- channel
    def los_channel(self, users, pa_x):
        """LoS channel matrix H (K, M) for PA positions pa_x (M,)."""
        users = np.asarray(users, float)
        pa_x = np.asarray(pa_x, float)
        dx = users[:, 0:1] - pa_x[None, :]
        r = np.sqrt(dx ** 2 + users[:, 1:2] ** 2 + self.d ** 2)
        s = (pa_x - self.x0)[None, :]  # in-waveguide travelled length
        amp = np.sqrt(self.eta) / r * np.exp(-0.5 * self.alpha_g * s)
        phase = -2 * np.pi * (r / self.lam + s / self.lam_g)
        return amp * np.exp(1j * phase)

    def channel(self, users, pa_x, rng=None):
        H = self.los_channel(users, pa_x)
        if np.isfinite(self.rician_K):
            rng = self.rng if rng is None else rng
            kap = self.rician_K
            g = (rng.standard_normal(H.shape) + 1j * rng.standard_normal(H.shape)) / np.sqrt(2)
            H = np.sqrt(kap / (1 + kap)) * H + np.sqrt(1 / (1 + kap)) * np.abs(H) * g
        return H

    # --------------------------------------------------------------- precoding
    def agg_snr(self, H, rho=1.0):
        """Aggregation (single-user) mode: every segment transmits at full power
        with phase alignment (equal-gain transmission). Returns SNR per user."""
        return rho * self.Pmax * np.abs(H).sum(axis=1) ** 2 / self.sigma2

    def zf_snr(self, H_S):
        """Equal-SNR zero-forcing among the users in H_S (S, M), S<=M, with a
        per-segment power constraint. Returns (snr, Ptot) at full power."""
        S = H_S.shape[0]
        if S == 1:
            snr = self.agg_snr(H_S)[0]
            return snr, self.M * self.Pmax
        G = H_S @ H_S.conj().T
        try:
            W = H_S.conj().T @ np.linalg.inv(G)  # (M, S), h_j^H w_i = delta_ij
        except np.linalg.LinAlgError:
            return 0.0, 0.0
        per_seg = (np.abs(W) ** 2).sum(axis=1)  # power per segment for unit p
        p = self.Pmax / per_seg.max()
        return p / self.sigma2, p * per_seg.sum()

    def subset_tables(self, H, Smax=None):
        """Enumerate all user subsets of size 1..Smax and compute their
        equal-SNR ZF SNR (full power) and total power. Returns dict with
        'subsets' (list of tuples), 'mask' (n_sub, K) bool, 'snr', 'ptot'."""
        K = H.shape[0]
        Smax = self.M if Smax is None else min(Smax, self.M)
        subsets, snr, ptot = [], [], []
        for s in range(1, Smax + 1):
            for comb in combinations(range(K), s):
                g, p = self.zf_snr(H[list(comb), :])
                subsets.append(comb)
                snr.append(g)
                ptot.append(p)
        mask = np.zeros((len(subsets), K), bool)
        for i, comb in enumerate(subsets):
            mask[i, list(comb)] = True
        return dict(subsets=subsets, mask=mask, snr=np.array(snr), ptot=np.array(ptot),
                    size=mask.sum(axis=1))


def db(x):
    return 10 * np.log10(x)
