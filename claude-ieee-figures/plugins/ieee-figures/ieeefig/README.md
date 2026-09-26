# ieeefig

Publication figures for IEEE papers. One module, no package install.

`ieeefig.py` implements the API that the `scientific-figure-making` skill
specifies (the [figures4papers](https://github.com/ChenLiu-1996/figures4papers)
repository ships that API as a document with no implementation), with the
`ieee-paper-writing` rule 7b conventions enforced in code rather than left to
the caller.

## Use it

```python
import os, sys
sys.path.insert(0, os.path.join(os.environ["CLAUDE_PLUGIN_ROOT"], "ieeefig"))
import ieeefig as ief

ief.apply_publication_style()
fig, axes = ief.create_subplots(1, 2, column="double")
ief.make_trend(axes[0], chi, [proposed, baseline], ["Proposed", "MaxCINR"],
               xlabel=r"Traffic load scale $\chi$", ylabel="Backlog (Mbit)",
               yscale="log")
ief.add_panel_labels(fig, axes)
ief.assert_house_style(fig)     # fails loudly before anything is written
ief.finalize_figure(fig, "figures/backlog")   # -> figures/backlog.pdf
```

## What it enforces

| Rule | Where |
|---|---|
| No error bars, no caps, no shaded confidence bands, no smoothing | `make_trend` refuses `show_shadow=True`; `assert_house_style` rejects any `fill_between` or errorbar artist |
| `xlim` exactly the first and last swept value | `make_trend`, re-checked by `assert_house_style` |
| `xticks` exactly the swept values and nothing else | `FixedLocator(x)`, re-checked by `assert_house_style` |
| End markers sit on the axis frame, not cut in half by it | `clip_on=False` on the series |
| IEEE column geometry | `IEEE_SINGLE = 3.5`, `IEEE_DOUBLE = 7.16`, base font 8 pt, `axes.linewidth` 0.8 |
| Readable in grayscale and under color blindness | Okabe-Ito `PALETTE`, plus one distinct marker and line style per series, plus a hatch channel on bars |
| Accepted by IEEE PDF eXpress | `pdf.fonttype = 42`; Type-3 fonts are rejected by the submission system |
| Vector output only, 600 dpi | `finalize_figure` defaults to PDF alone; raster formats only if asked for explicitly |

`assert_house_style(fig)` is meant to be called from an audit test as well as
from the plotting script, so a figure cannot regress silently after a late edit.

## API

Same names and signatures as the skill's `references/api.md`, so its tutorials
and the repo's `figure_*` scripts transfer:

`apply_publication_style`, `create_subplots`, `finalize_figure`, `make_trend`,
`make_grouped_bar`, `annotate_bars`, `make_heatmap`, `make_scatter`,
`make_sphere_illustration`, plus `FigureStyle`, `PALETTE`, `DEFAULT_COLORS`.

Added beyond the spec: `DEFAULT_MARKERS`, `DEFAULT_LINESTYLES`,
`add_panel_labels`, `assert_house_style`, and `IEEE_SINGLE` / `IEEE_DOUBLE`.

Deliberate differences from the spec, beyond rule 7b: `make_heatmap` defaults to
`viridis` rather than `magma`, because it is monotone in lightness and therefore
survives grayscale conversion.

## Test

```bash
python smoke_test.py
```

12 checks: every helper renders and exports, and every audit branch fires on a
figure that violates it.
