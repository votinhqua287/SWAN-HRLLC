"""Audit of the manuscript figures (recipe 6 of the ieee-figures plugin).

Every figure must pass ``ieeefig.assert_house_style``; the sweep panels of the figures that are
audited with ``strict_ticks=False`` (because one of their panels has a continuous x axis) must
still tick exactly the swept values; and a plotted curve must be the numbers of the results
files, not values typed into the script.
"""
import numpy as np
import pytest
import matplotlib.pyplot as plt

from experiments import paper_figs as pf
from experiments.run_campaign import load

pf.apply_style()


def _sweep_ticks_match(ax):
    x = np.asarray(ax.get_lines()[0].get_xdata(), float)
    ticks = np.asarray(ax.get_xticks(), float)
    ticks = ticks[(ticks >= x.min() - 1e-9) & (ticks <= x.max() + 1e-9)]
    return ticks.size == x.size and np.allclose(ticks, x)


@pytest.mark.parametrize("name", list(pf.BUILDERS))
def test_house_style(name):
    fig = pf.BUILDERS[name][0]()
    try:
        pf.audit(fig, name)
    finally:
        plt.close(fig)


def test_sweep_panels_of_relaxed_figures_tick_the_swept_values():
    fig = pf.build_energy()
    try:
        assert _sweep_ticks_match(fig.axes[2])  # (c) evaluated targets
        assert _sweep_ticks_match(fig.axes[3])  # (d) activation delays at ordinal positions
    finally:
        plt.close(fig)


def test_key_figure_plots_the_results_files():
    fig = pf.build_key()
    try:
        R = load("key")["TLA-SWAN"]
        vals = sorted(R)
        expected = pf._floor([R[v]["pv"] for v in vals], [R[v]["arr"] for v in vals])
        line = fig.axes[1].get_lines()[0]  # TLA-SWAN is the first series of panel (b)
        assert np.allclose(line.get_xdata(), vals)
        assert np.allclose(line.get_ydata(), expected)
        assert line.get_label() == "TLA-SWAN"
    finally:
        plt.close(fig)
