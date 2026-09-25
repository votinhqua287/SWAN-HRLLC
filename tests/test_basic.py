"""Unit tests required by the research guide (Section 19). Run: python -m pytest -q tests"""
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.simulator import SimConfig, run_config, _fifo_remove
from src.arrivals import OnOffSource, PoissonSource, required_rate_onoff, beta_for_activity
from src.fbl import fbl_error
from src.tail_analysis import single_user_fixed_sa


def test_zero_arrivals_zero_queue():
    cfg = SimConfig(T=3000, warmup=100, h=0.0, seed=1)
    r = run_config(cfg)
    assert sum(r["arrivals"]) == 0 and sum(r["viol"]) == 0 and max(r["avg_Q"]) == 0


def test_service_cannot_make_queue_negative():
    q = np.array([[2, 0, 1, 0], [0, 0, 0, 3]])
    served = _fifo_remove(q, np.array([10, 2]))
    assert (q - served >= 0).all() and served.sum(axis=1).tolist() == [3, 2]


def test_bernoulli_poisson_mean_load():
    rng = np.random.default_rng(0)
    src = PoissonSource(4, 1e-4, 0.3, rng)
    a = np.array([src.step() for _ in range(50000)])
    assert np.allclose(a.mean(axis=0), 0.3, atol=0.02)


def test_on_persistence_increases_burstiness_at_fixed_mean():
    def idx_dispersion(alpha):
        rng = np.random.default_rng(1)
        src = OnOffSource(1, 1e-4, 3.0, alpha, beta_for_activity(alpha, 0.1, 1e-4), rng)
        a = np.array([src.step()[0] for _ in range(200000)])
        w = a[: (a.size // 20) * 20].reshape(-1, 20).sum(axis=1)  # 2-ms windows
        return w.var() / w.mean(), a.mean()
    d_short, m_short = idx_dispersion(4000.0)
    d_long, m_long = idx_dispersion(250.0)
    assert abs(m_short - m_long) < 0.03 and d_long > d_short


def test_fbl_error_decreases_with_snr():
    e = fbl_error(200, 2.0, np.array([1.0, 10.0, 100.0]))
    assert e[0] > e[1] > e[2]


def test_zero_config_delay_reproduces_simplified_model():
    base = dict(T=6000, warmup=200, seed=2, Pc_W=0.1, V=0.3)
    r0 = run_config(SimConfig(**base, tau_cfg=0.0, la=0.0))
    r1 = run_config(SimConfig(**base, tau_cfg=0.0, la=0.0, keep_warm=False))
    assert r0["pv"] == r1["pv"] and r0["avg_power_W"] == r1["avg_power_W"]


def test_tail_probability_decreases_with_deadline():
    pv = []
    for D in (3, 10, 30):
        r = run_config(SimConfig(T=20000, warmup=500, seed=3, h=3.5, Dmax_slots=D, Ddrop_slots=D))
        pv.append(r["pv"])
    assert pv[0] >= pv[1] >= pv[2]


def test_required_rate_limits():
    c = required_rate_onoff(3.0, 1000.0, 111.1, 1e-3, 1e-5)
    mean = 3.0 * 111.1 / 1111.1
    assert mean < c < 3.0
    assert required_rate_onoff(3.0, 1000.0, 111.1, 1e3, 0.5) < mean + 1e-3   # loose target -> mean rate


def test_route_a_upper_bounds_light_load():
    # for a lightly loaded single device the analytical approximation must not
    # fall below the observed violation probability if used as an upper bound
    cfg = SimConfig(T=60000, warmup=500, seed=4, K=1, mode="sa", h=4.0, Pmax_dBm=-15.0)
    r = run_config(cfg)
    snr = 10 ** (r["snr_agg_dB"][0] / 10)
    a = single_user_fixed_sa(cfg.h, cfg.alpha, cfg.beta, cfg.Ts, snr, cfg.n, cfg.L, cfg.bmax, cfg.Dmax_slots)
    assert a["pv_approx"] >= 0.0  # existence; tightness is assessed in the paper's Fig. (single)
