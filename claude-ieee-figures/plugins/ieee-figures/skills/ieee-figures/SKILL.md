---
name: ieee-figures
description: >-
  Produce matplotlib figures for IEEE journal and conference papers (TWC, TCOM,
  TVT, COMML, JSAC, and IEEE conferences) using the bundled `ieeefig` module.
  Use whenever a figure is destined for a two-column IEEE manuscript: plotting a
  parameter sweep, a convergence curve, an ablation bar chart, a scalability
  comparison, or a heatmap; writing or editing the script that generates such a
  figure; fixing a figure that is illegible at column width, unreadable in
  grayscale, or rejected by IEEE PDF eXpress for Type-3 fonts. Trigger even when
  the request does not say "IEEE" — "vẽ figure cho bài báo", "plot the backlog
  versus load", "làm figure simulation results", "make this figure
  publication-ready", or editing a `plot_*.py` next to a `paper/` folder all
  count. Do NOT use for interactive or web plots (Plotly, Altair, Bokeh),
  exploratory plots with no publication target, GIS or heavy 3D rendering,
  schematic diagrams drawn in Illustrator or TikZ, or for writing the prose that
  describes a figure.
---

# IEEE figures

Figures for IEEE two-column papers, built with the `ieeefig` module that ships
with this plugin. The module exists because the conventions below are violated
by habit, not by ignorance: they get re-broken on every figure when they are
checked by eye instead of by code. `ieeefig` sets them and then re-checks them.

## Always do this

1. **Import the bundled module rather than writing fresh `rcParams`.** It lives
   at `${CLAUDE_PLUGIN_ROOT}/ieeefig`:

   ```python
   import os, sys
   sys.path.insert(0, os.path.join(os.environ["CLAUDE_PLUGIN_ROOT"], "ieeefig"))
   import ieeefig as ief
   ```

   In a project that vendors the module instead, point `sys.path` at that copy.
   Either way, do not hand-roll a style block: a per-script `rcParams` dict is
   how two figures in the same paper end up with different fonts.

2. **Call `ief.assert_house_style(fig)` before exporting.** It fails loudly on a
   figure that violates §"The four rules" below. Put the same call in the
   project's audit test, so a figure cannot regress silently after a late edit.

3. **Export vector PDF only**, through `ief.finalize_figure(fig, path)`. LaTeX
   embeds the PDF at full quality and the figure stays sharp at any zoom.

4. **Report what you ran.** State the sweep values, the figure size, and that
   the audit passed — `6 swept points, 7.16 in double column, audit clean` is a
   status line the author can act on.

## The four rules

These are the points where IEEE practice departs from general
publication-figure advice, including from the `scientific-figure-making` skill
if it is also installed. **When they conflict, this skill wins**, because it is
the one that knows the figure is going into a two-column manuscript.

### 1. No error bars, no caps, no shaded bands, no smoothing

Each scheme is one ordinary markered line with straight segments between
simulated points. Uncertainty is reported in the table and in the sentence that
states a paired difference, never as a band behind a curve — a band on a
6-point sweep at column width is a smear, and a caption that mentions
confidence intervals invites a reviewer to ask how many runs produced them.

`ief.make_trend` refuses `show_shadow=True` rather than silently ignoring it.

### 2. The axes stop at the data

`xlim` is exactly the first and last swept value, and `xticks` are exactly the
swept values and nothing else, so every tick marks a simulated point and the end
markers sit on the axis frame instead of floating inside it. Matplotlib's
automatic locator will otherwise place ticks at round numbers that correspond to
nothing you simulated, which reads as interpolation.

`ief.make_trend` sets both; `assert_house_style` re-checks both.

### 3. Column geometry, not panel geometry

`IEEE_SINGLE = 3.5` inches, `IEEE_DOUBLE = 7.16` inches, base font 8 pt,
`axes.linewidth` 0.8. Use `ief.create_subplots(nrows, ncols, column="single"|"double")`.

Figure advice written for machine-learning venues assumes a large single panel —
`figsize=(45, 12)`, `font.size=24`, `axes.linewidth=3`. Scaled into a 3.5-inch
column that is unreadable. Never author at poster size and shrink in LaTeX:
decide the final width first, and never pass `width=` to `\includegraphics` to
correct a mis-sized figure, because it rescales the fonts along with everything
else.

### 4. Readable in grayscale and under color blindness

Every series carries three redundant channels: a color from the Okabe-Ito
palette (`ief.PALETTE`), a distinct marker (`ief.DEFAULT_MARKERS`), and a
distinct line style (`ief.DEFAULT_LINESTYLES`). Bars get a hatch channel.
Color alone fails twice over — for the ~8% of male reviewers with a color vision
deficiency, and for every reader who prints the PDF.

Do not pair greens against reds to carry the main contrast.

## Submission mechanics that cause desk rejections

- **Type-3 fonts are rejected by IEEE PDF eXpress.** Matplotlib emits them by
  default. `apply_publication_style` sets `pdf.fonttype = 42` and
  `ps.fonttype = 42`; the plugin's smoke test greps the exported PDF for
  `/Type3` to prove it.
- **Helvetica is not installed on Windows.** Setting `font.family = "helvetica"`
  produces a `findfont` warning on every call and silently falls back to
  DejaVu Sans, so two machines render the same script differently. The module
  uses the fallback stack `["Arial", "Helvetica", "DejaVu Sans", "sans-serif"]`.
- **`text.usetex=True` needs a working LaTeX installation** and makes plotting
  slow. Prefer matplotlib's mathtext (`r"$\chi$"`, `r"$N_{\max}$"`), which
  renders the same symbols without the dependency. Set
  `FigureStyle(use_tex=True)` only when the labels genuinely need LaTeX macros
  the paper defines.

## Reference

| File | Open when |
|------|-----------|
| [references/api.md](references/api.md) | Function signatures, `PALETTE`, validation rules, what each helper enforces |
| [references/recipes.md](references/recipes.md) | Worked figures: sweep, multi-panel with `(a)`/`(b)`, ablation bars, scalability with a log axis, audit test |

The module's own source at `${CLAUDE_PLUGIN_ROOT}/ieeefig/ieeefig.py` is short
and documented; read it when a helper's behavior is in question rather than
guessing from the signature.

## What this skill does not do

Writing the prose that describes a figure, the caption, or the Simulation
Results section is a different job — a figure caption is a claim, and it has to
match what the code plotted. Keep the two tasks separate, and do not invent a
causal explanation for a curve shape to make a paragraph read smoothly. If a
plotted result looks wrong — non-monotonic where monotonicity is expected, a
text value that disagrees with the figure — stop and flag it rather than
producing a figure that hides it.

## Attribution

The API shape (`apply_publication_style`, `make_trend`, `make_grouped_bar`,
`finalize_figure`, `FigureStyle`, `PALETTE`) follows the specification published
in the `scientific-figure-making` skill of
[ChenLiu-1996/figures4papers](https://github.com/ChenLiu-1996/figures4papers)
(CC BY-NC 4.0), which documents that API without shipping an implementation.
`ieeefig` is an independent implementation written to IEEE conventions; no code
or text from that repository is redistributed here. Its `figure_*` scripts are
worth reading as worked examples of the non-IEEE, large-panel style.
