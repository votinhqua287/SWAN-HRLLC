# Recipes

Every snippet assumes the import block and one call to
`ief.apply_publication_style()` at module level.

```python
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.environ["CLAUDE_PLUGIN_ROOT"], "ieeefig"))
import ieeefig as ief

ief.apply_publication_style()
```

---

## 1. A single-column parameter sweep

The most common figure in a communications paper: one metric against one swept
variable, three or four schemes.

```python
chi = np.array([0.9, 1.0, 1.1, 1.2, 1.3, 1.4])          # the swept values

fig, axes = ief.create_subplots(column="single")
ief.make_trend(
    axes[0], chi,
    [proposed, predictive_maxweight, maxcinr],
    ["Proposed", "Predictive-MaxWeight", "MaxCINR"],
    xlabel=r"Traffic load scale $\chi$",
    ylabel="Average backlog (Mbit)",
    yscale="log",
)
ief.assert_house_style(fig)
ief.finalize_figure(fig, "figures/backlog_vs_load")
```

`chi` is the array the simulator swept. Never pass a denser grid for a
"smoother" curve: the ticks are the swept values, so a denser grid would put
ticks on points that were never simulated.

---

## 2. Two panels side by side with `(a)` and `(b)`

```python
fig, axes = ief.create_subplots(1, 2, column="double")

ief.make_trend(axes[0], chi, [prop_backlog, base_backlog],
               ["Proposed", "MaxCINR"],
               xlabel=r"Traffic load scale $\chi$",
               ylabel="Average backlog (Mbit)", yscale="log")

ief.make_trend(axes[1], chi, [prop_overflow, base_overflow],
               ["Proposed", "MaxCINR"],
               xlabel=r"Traffic load scale $\chi$",
               ylabel="Average overflow (Mbit)",
               legend=False)          # one legend for the figure is enough

ief.add_panel_labels(fig, axes)
fig.tight_layout(pad=0.4)
ief.assert_house_style(fig)
ief.finalize_figure(fig, "figures/load_sweep")
```

In LaTeX, include it once and refer to the panels in the caption:

```latex
\begin{figure*}[!t]
  \centering
  \includegraphics{figures/load_sweep.pdf}
  \caption{Impact of the traffic-load scaling factor $\chi$ on (a) average total
  queue backlog and (b) average overflow magnitude.}
  \label{fig:load_sweep}
\end{figure*}
```

No `width=` argument: the PDF was authored at `IEEE_DOUBLE`, so it already
fits, and rescaling would shrink the 8 pt labels below legibility.

---

## 3. A shared legend above the panels

When four or more schemes appear in every panel, a per-axes legend eats the
data area.

```python
fig, axes = ief.create_subplots(1, 2, column="double")
# ... two make_trend calls with legend=False ...
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="upper center", ncol=len(labels),
           bbox_to_anchor=(0.5, 1.08), frameon=False)
ief.assert_house_style(fig)
ief.finalize_figure(fig, "figures/sweep", pad=0.04)
```

Raise `pad` slightly so the legend is not clipped by `bbox_inches="tight"`.

---

## 4. Ablation bars

```python
fig, axes = ief.create_subplots(column="single")
bars = ief.make_grouped_bar(
    axes[0],
    categories=["$B=12$", "$B=14$", "$B=16$"],
    series=[[31.2, 37.2, 27.3], [21.7, 13.1, 9.4]],
    labels=["vs. DQN", "vs. MaxWeight"],
    ylabel="Backlog reduction (%)",
    hatches=["", "//"],
    annotate=True, fmt="{:.1f}",
)
ief.finalize_figure(fig, "figures/ablation")
```

The hatch channel is what keeps the bars separable once the journal prints the
figure in grayscale. `assert_house_style` is a no-op on a bar-only axes, since
its checks concern swept line data.

---

## 5. A scalability figure with a decision-time axis

Two quantities of very different magnitude belong on two panels, not on one
axes with a twin y-axis — a twin axis makes the reader guess which curve
belongs to which scale.

```python
B = np.array([12, 14, 16])

fig, axes = ief.create_subplots(1, 2, column="double")
ief.make_trend(axes[0], B, [t_proposed, t_exhaustive, t_dqn],
               ["Proposed", "Exhaustive", "DQN"],
               xlabel="Number of candidate beams $B$",
               ylabel="Decision time per slot (ms)", yscale="log")
ief.make_trend(axes[1], B, [q_proposed, q_exhaustive, q_dqn],
               ["Proposed", "Exhaustive", "DQN"],
               xlabel="Number of candidate beams $B$",
               ylabel="Average backlog (Mbit)", legend=False)
ief.add_panel_labels(fig, axes)
ief.assert_house_style(fig)
ief.finalize_figure(fig, "figures/scalability")
```

With three swept points the ticks are `12, 14, 16` and nothing else, which is
exactly what the data supports.

---

## 6. An audit test for the paper's figures

Put this next to the simulator's other tests. It keeps a figure from regressing
after a late edit, which is when the conventions usually break.

```python
# tests/test_figures.py
import ieeefig as ief
from paper_figures import build_load_sweep, build_scalability

def test_load_sweep_obeys_house_style():
    ief.assert_house_style(build_load_sweep())

def test_scalability_obeys_house_style():
    ief.assert_house_style(build_scalability())

def test_figure_matches_results_file(results):
    """The curve must be the numbers in the result file, not a copy typed in."""
    fig = build_load_sweep()
    line = fig.axes[0].get_lines()[0]
    assert line.get_ydata().tolist() == results["proposed"]["backlog"]
```

The third test is the one that matters most: a figure plotted from hard-coded
numbers pasted out of an old run is the defect class that survives every visual
check, because the figure looks perfectly correct.

---

## 7. Regenerating everything

Keep one entry point so all figures in the paper are rebuilt with one command
and cannot drift apart in style:

```python
# paper_figures.py
BUILDERS = {
    "load_sweep": build_load_sweep,
    "scalability": build_scalability,
    "ablation": build_ablation,
}

if __name__ == "__main__":
    ief.apply_publication_style()
    for name, builder in BUILDERS.items():
        fig = builder()
        ief.assert_house_style(fig)
        print(name, ief.finalize_figure(fig, f"figures/{name}"))
```
