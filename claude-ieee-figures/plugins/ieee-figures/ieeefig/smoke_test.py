"""Smoke test for ieeefig: exercises every helper and every audit branch.

Run with ``python smoke_test.py``. It writes into ``_smoke_out/`` and prints a
one-line status per check.
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ieeefig as ief


OUT = Path(__file__).resolve().parent / "_smoke_out"
results = []


def check(name, fn):
    try:
        fn()
        results.append(("pass", name, ""))
    except Exception as exc:  # noqa: BLE001 - the point is to report, not to raise
        results.append(("FAIL", name, f"{type(exc).__name__}: {exc}"))


def expect_raises(name, exc_type, fn):
    try:
        fn()
    except exc_type:
        results.append(("pass", name, ""))
    except Exception as exc:  # noqa: BLE001
        results.append(("FAIL", name, f"raised {type(exc).__name__} instead: {exc}"))
    else:
        results.append(("FAIL", name, "did not raise"))


ief.apply_publication_style()

chi = np.array([0.9, 1.0, 1.1, 1.2, 1.3, 1.4])
proposed = np.array([180.0, 320.0, 640.0, 1500.0, 4200.0, 11000.0])
baseline = np.array([260.0, 470.0, 980.0, 2300.0, 6100.0, 15000.0])
third = baseline * 1.35


# 1. trend figure, double column, two panels, log y, panel labels, audit, export
def trend_case():
    fig, axes = ief.create_subplots(1, 2, column="double")
    ief.make_trend(axes[0], chi, [proposed, baseline, third],
                   ["Proposed", "Predictive-MaxWeight", "MaxCINR"],
                   xlabel=r"Traffic load scale $\chi$", ylabel="Backlog (Mbit)",
                   yscale="log")
    ief.make_trend(axes[1], chi, [proposed * 0.01, baseline * 0.02],
                   ["Proposed", "MaxCINR"],
                   xlabel=r"Traffic load scale $\chi$", ylabel="Overflow (Mbit)")
    ief.add_panel_labels(fig, axes)
    ief.assert_house_style(fig)
    written = ief.finalize_figure(fig, OUT / "trend")
    assert written == [OUT / "trend.pdf"], written
    assert written[0].exists() and written[0].stat().st_size > 1000
    w, h = fig.get_size_inches()
    assert abs(w - ief.IEEE_DOUBLE) < 1e-9, w


check("trend: build, audit, export PDF at IEEE_DOUBLE", trend_case)


# 2. show_shadow must be refused
def shadow_case():
    fig, axes = ief.create_subplots(1, 1)
    ief.make_trend(axes[0], chi, [proposed], ["Proposed"], show_shadow=True)


expect_raises("make_trend(show_shadow=True) refused", ValueError, shadow_case)


# 3. the audit must catch a hand-widened xlim
def bad_xlim_case():
    fig, axes = ief.create_subplots(1, 1)
    ief.make_trend(axes[0], chi, [proposed], ["Proposed"])
    axes[0].set_xlim(0.5, 1.8)
    ief.assert_house_style(fig)


expect_raises("audit catches widened xlim", AssertionError, bad_xlim_case)


# 4. the audit must catch a fill_between band added after the fact
def band_case():
    fig, axes = ief.create_subplots(1, 1)
    ief.make_trend(axes[0], chi, [proposed], ["Proposed"])
    axes[0].fill_between(chi, proposed * 0.9, proposed * 1.1, alpha=0.2)
    ief.assert_house_style(fig)


expect_raises("audit catches fill_between band", AssertionError, band_case)


# 5. the audit must catch error bars
def errorbar_case():
    fig, axes = ief.create_subplots(1, 1)
    ief.make_trend(axes[0], chi, [proposed], ["Proposed"])
    axes[0].errorbar(chi, baseline, yerr=baseline * 0.05)
    ief.assert_house_style(fig)


expect_raises("audit catches error bars", AssertionError, errorbar_case)


# 6. the audit must catch auto ticks that do not match the sweep
def bad_ticks_case():
    fig, axes = ief.create_subplots(1, 1)
    ief.make_trend(axes[0], chi, [proposed], ["Proposed"])
    axes[0].set_xticks([0.9, 1.2, 1.4])
    ief.assert_house_style(fig)


expect_raises("audit catches wrong xticks", AssertionError, bad_ticks_case)


# 7. input validation
expect_raises("mismatched series length rejected", ValueError,
              lambda: ief.make_trend(ief.create_subplots(1, 1)[1][0], chi,
                                     [proposed[:-1]], ["Proposed"]))
expect_raises("unsorted sweep rejected", ValueError,
              lambda: ief.make_trend(ief.create_subplots(1, 1)[1][0], chi[::-1],
                                     [proposed], ["Proposed"]))
expect_raises("bad export format rejected", ValueError,
              lambda: ief.finalize_figure(ief.create_subplots(1, 1)[0],
                                          OUT / "x", formats=["docx"]))


# 8. grouped bars with hatches and annotations
def bar_case():
    fig, axes = ief.create_subplots(1, 1, column="single")
    bars = ief.make_grouped_bar(
        axes[0], ["B=12", "B=14", "B=16"],
        [[31.2, 37.2, 27.3], [21.7, 13.1, 9.4]],
        ["vs. DQN", "vs. MaxWeight"], ylabel="Backlog reduction (\\%)"
        if matplotlib.rcParams["text.usetex"] else "Backlog reduction (%)",
        annotate=True, hatches=["", "//"], fmt="{:.1f}")
    assert bars is not None
    ief.finalize_figure(fig, OUT / "bars")
    assert (OUT / "bars.pdf").exists()


check("grouped bars: hatch channel, annotations, export", bar_case)


# 9. heatmap, scatter, sphere
def misc_case():
    fig, axes = ief.create_subplots(1, 3, column="double")
    ief.make_heatmap(axes[0], np.random.default_rng(0).random((4, 5)),
                     x_labels=list("abcde"), y_labels=list("wxyz"),
                     cbar_label="Utility", annotate=False)
    ief.make_scatter(axes[1], np.arange(20), np.random.default_rng(1).random(20),
                     label="Samples")
    ief.make_sphere_illustration(axes[2])
    ief.finalize_figure(fig, OUT / "misc")
    assert (OUT / "misc.pdf").exists()


check("heatmap + scatter + sphere render and export", misc_case)


# 10. the exported PDF must not carry Type-3 fonts (IEEE PDF eXpress rejects them)
def fonttype_case():
    assert matplotlib.rcParams["pdf.fonttype"] == 42
    raw = (OUT / "trend.pdf").read_bytes()
    assert b"/Type3" not in raw, "Type-3 font found in the exported PDF"


check("exported PDF is free of Type-3 fonts", fonttype_case)


width = max(len(n) for _, n, _ in results)
failed = 0
for status, name, detail in results:
    failed += status == "FAIL"
    print(f"{status:4}  {name:<{width}}  {detail}")
print(f"\n{len(results) - failed}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
