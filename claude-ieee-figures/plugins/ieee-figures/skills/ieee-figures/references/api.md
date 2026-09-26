# `ieeefig` API

Import:

```python
import os, sys
sys.path.insert(0, os.path.join(os.environ["CLAUDE_PLUGIN_ROOT"], "ieeefig"))
import ieeefig as ief
```

---

## Constants

| Name | Value | Notes |
|---|---|---|
| `IEEE_SINGLE` | `3.5` | Width in inches of one column of an IEEE two-column page |
| `IEEE_DOUBLE` | `7.16` | Width in inches of the full text block |
| `PALETTE` | dict | Okabe-Ito, keyed by role: `blue_main` (proposed), `vermillion` (the scheme being argued against), `green`, `orange`, `purple`, `blue_secondary`, `yellow`, `black`, `neutral`. Aliases `red_strong`, `green_3`, `highlight` exist for scripts written against the figures4papers palette |
| `DEFAULT_COLORS` | list | Series order; index 0 is the proposed scheme |
| `DEFAULT_MARKERS` | list | `o s ^ v D x P *` |
| `DEFAULT_LINESTYLES` | list | Solid, dashed, dash-dot, dotted, then four longer patterns |

Every pair in the Okabe-Ito set stays distinguishable under deuteranopia,
protanopia and tritanopia. A green/red pairing does not, which is why the
palette does not offer one as its primary contrast.

---

## `FigureStyle`

```python
@dataclass(frozen=True)
class FigureStyle:
    font_size: int = 8
    axes_linewidth: float = 0.8
    line_width: float = 1.0
    marker_size: float = 3.5
    use_tex: bool = False
    font_family: tuple[str, ...] = ("Arial", "Helvetica", "DejaVu Sans", "sans-serif")
    grid: bool = False
```

Defaults are single-column defaults. For a figure that will be placed at full
double-column width and therefore reduced less, `font_size=9` is also fine;
above that the figure starts to look oversized next to 10 pt body text.

---

## Style and layout

### `apply_publication_style(style=None)`

Sets rcParams once, before any figure is created. Beyond the fields of
`FigureStyle` it sets: top and right spines off, frameless legend, ticks
pointing inward, `savefig.bbox="tight"`, `svg.fonttype="none"`, and
`pdf.fonttype = ps.fonttype = 42` so the exported PDF carries TrueType rather
than Type-3 fonts.

### `create_subplots(nrows=1, ncols=1, figsize=None, column="single", height=None, **kwargs)`

Returns `(fig, axes)` with `axes` always a flattened 1-D array, so `axes[0]`
works for a single panel too. When `figsize` is omitted the width comes from
`column`, and each panel gets a height of `0.78 × (width / ncols)` unless
`height` overrides it. Extra keyword arguments pass through to
`plt.subplots` (`sharey=True`, `gridspec_kw={...}`, …).

### `finalize_figure(fig, out_path, formats=None, dpi=600, close=True, pad=0.02, **kwargs)`

Writes the figure and returns the list of paths written. Defaults to PDF alone;
the extension of `out_path` is used when it has one. Parent directories are
created. Passing a format outside
`{pdf, svg, eps, png, jpg, jpeg, tif, tiff}` raises.

`dpi` affects only rasterized artists inside the PDF — a heatmap, a dense
scatter. Vector artists are resolution-independent, so a higher DPI does not
make a line plot sharper, it only makes the file larger.

---

## Plot helpers

### `make_trend(ax, x, y_series, labels, *, colors=None, ylabel=None, xlabel=None, show_shadow=False, markers=None, linestyles=None, tick_labels=None, yscale=None, legend=True, legend_kwargs=None)`

One markered line per scheme. Enforces the first two house rules:

- `xlim` becomes exactly `(x[0], x[-1])`;
- `xticks` become exactly `x`, via a `FixedLocator`;
- markers are drawn with `clip_on=False`, so the end markers sit on the frame
  instead of being cut in half by it;
- `show_shadow=True` **raises `ValueError`**. The parameter exists only to keep
  the signature compatible with the figures4papers API.

Rejects: a non-1-D `x`, fewer than two swept values, an `x` that is not
strictly increasing, a series whose length differs from `x`, and a
`labels` list whose length differs from `y_series`.

`tick_labels` replaces the tick text without moving the ticks — use it when the
swept variable is best shown as a formatted string. `yscale="log"` is the usual
choice for a backlog or an error curve spanning decades.

### `make_grouped_bar(ax, categories, series, labels, ylabel="Value", colors=None, annotate=False, hatches=None, bar_width=None, fmt="{:.2f}")`

Grouped bars with black edges. `series` is one array per legend entry, each of
length `len(categories)`. Pass `hatches=["", "//", "xx"]` to add the grayscale
channel. Returns the last `BarContainer`, for use with `annotate_bars`.

### `annotate_bars(ax, bars, fmt="{:.2f}", fontsize=None, padding=2.0)`

Prints each bar's value above it. Default font size is two points below the
base size.

### `make_heatmap(ax, matrix, x_labels=None, y_labels=None, cmap="viridis", cbar_label=None, annotate=False, fmt="{:.2f}", vmin=None, vmax=None)`

Default colormap is `viridis`, not `magma`: it is perceptually uniform *and*
monotone in lightness, so it survives grayscale conversion. Cell annotations
switch between white and black text at the midpoint of the data range.

### `make_scatter(ax, x, y, label=None, color=None, size=12, alpha=0.8, marker="o")`

Single series. Default size suits column width; the matplotlib default of 36 is
too large there.

### `make_sphere_illustration(ax, light_dir=(-0.5, 0.5, 0.8), resolution=128, alpha=0.6, color=None)`

Lambertian-shaded disk that reads as a 3-D sphere, for conceptual diagrams.
Kept for parity with the figures4papers API; rarely needed in a
communications paper.

### `add_panel_labels(fig, axes, labels=None, y=-0.28, fontsize=None)`

Puts `(a)`, `(b)`, … centred under each panel. Lower `y` (more negative) when
the x-axis label is tall or wraps.

---

## Audit

### `assert_house_style(fig, strict_ticks=True)`

Raises `AssertionError` listing every violation it finds. On each axes that
carries line data it checks:

- no `ErrorbarContainer` — no error bars or caps;
- no `PolyCollection` — no `fill_between` uncertainty band;
- all series share one x grid;
- `xlim` equals the first and last plotted x value;
- `xticks` inside the data range equal the plotted x values exactly.

Axes with no line data — a heatmap panel, a legend-only panel, a schematic —
are skipped. Set `strict_ticks=False` for an axes whose x variable is
continuous or categorical by design.

Call it in the plotting script *and* in the project's audit test:

```python
def test_figure_2_obeys_house_style():
    fig = build_figure_2()
    ief.assert_house_style(fig)
```

---

## Validation summary

| Call | Raises when |
|---|---|
| `make_trend` | `show_shadow=True`; `x` not 1-D, shorter than 2, or not strictly increasing; a series length mismatch; a label count mismatch; a `tick_labels` length mismatch |
| `make_grouped_bar` | series count differs from label count; a series length differs from the category count |
| `make_heatmap` | `matrix` not 2-D; a label list whose length differs from the matching axis |
| `make_scatter` | `x` and `y` shapes differ |
| `create_subplots` | `column` is neither `"single"` nor `"double"` |
| `finalize_figure` | an unsupported output format |
| `add_panel_labels` | label count differs from panel count |
