---
name: ieee-paper-writing
description: Rules for drafting IEEE journal manuscripts (TWC/TCOM/TVT) in this repository - 13-page budget for the initial submission, section structure, figure and table economy, figures built with the vendored ieee-figures plugin (ieeefig: swept-value ticks, no error bars, Okabe-Ito encoding, house-style audit) plus Times New Roman, box on, grid on, only (a)/(b) under the x-label, equal panel sizes, legends inside axes, editable PPTX system diagrams, placeholders for co-author derivations, and the compile-and-count checklist. Use whenever writing or revising paper/main.tex or any paper figure.
---

# IEEE paper writing (TWC / TCOM initial submission)

## 1. Page budget is a hard constraint - check it before writing prose
- **Initial submission: at most 13 pages** (IEEEtran `journal`, double column, 10 pt), references included.
  Aim for **12.6-13.0 pages**. Later revision rounds add reviewer-requested material, and a
  co-author's derivations/appendices still have to fit; never hand over an 18-page draft.
- Budget by section (double-column pages): Introduction 1.5, System Model 1.5, Problem 0.4,
  Proposed Scheme 2.5 (algorithms included), Results 4.5-5.0, Conclusions 0.3, References 1.2.
- Keep the `[To do]` placeholders for the co-author to **one line each**; the detailed
  instructions live in `docs/math_todo_for_colleague.md`, not in the manuscript.
- After every major edit: `pdflatex && bibtex && pdflatex && pdflatex`, then `pdfinfo main.pdf | grep Pages`
  and report the count. If above budget, cut before adding anything else.

## 2. Figure and table economy
- At most **8-9 figure environments** and **2 tables** in a 13-page paper.
- Group sweeps into **multi-panel rows** (`figure*`, one PDF per figure built with the
  `ieee-figures` plugin): 2-4 panels on a 7.16-in canvas, 1.6-1.9 in tall; single-column figures
  on a 3.5-in canvas, about 2 in tall. Section 5 gives the exact rules.
- One figure per claim: keep only figures that carry a headline result (the hypothesis figures,
  the CCDF, the cost/energy trade-off, the placement comparison, the analytical validation).
  Robustness/sensitivity results go into one sentence or one compact table.
- Never include: convergence plots of a routine algorithm, illustrative plots of a closed-form
  expression, or a sweep whose curves are parallel to another sweep already shown.

## 3. Structure and style (IEEEtran)
- **Abstract: 200-220 words**, one paragraph, no citations, no equations beyond simple numbers: context (1-2 sentences),
  gap (1), model and problem (2), method (2-3), headline results with numbers (1-2). Count the words of the rendered
  abstract (`pdftotext -f 1 -l 1 main.pdf - | sed -n '/^Abstract/,/^Index Terms/p' | wc -w`) and report the count.
  Every number in the abstract must match a statement in the results section. Index terms 5-8.
- Introduction: motivation (1 paragraph), related work in 2-3 compact paragraphs (cite groups of
  works, never one sentence per paper), contributions as 4-5 bullets, organization + notation.
- System model: one subsection per model component, equations numbered, symbols defined once.
- Proposed scheme: algorithms in `algorithmic`, complexity paragraph, theorems stated concisely.
- Results: setup + benchmarks (bullet list), then one subsection per hypothesis/figure; each
  paragraph: what is varied, the two or three numbers that matter, the mechanism.
- Sentences <= 30 words in the results section; numbers in prose only when they change the
  conclusion.
- References: cite the origin paper of every concept, surveys once, and at most ~45 entries.

## 4. Checklist before handing over
- [ ] `pdfinfo` page count <= 13.0 (state it in the hand-over message).
- [ ] Abstract 200-220 words (state the count).
- [ ] No `Overfull \hbox`, no undefined references/citations.
- [ ] Figures referenced in order; every figure and table discussed in the text.
- [ ] Figures follow Section 5: built with the `ieee-figures` plugin, `assert_house_style` clean for
      every figure (`python -m experiments.paper_figs` prints one status line per figure and
      `pytest tests/test_figures.py` re-checks it), Times New Roman, box on and grid on, only "(a)",
      "(b)" under the x-labels, every legend inside its axes without covering data (no WARNING in the
      status lines),
      cropped PDF width <= 516 pt (`figure*`) or <= 252 pt (`figure`), system diagrams as editable PPTX.
- [ ] Placeholders: `\todobox` count reported; each one line.
- [ ] `refs.bib` entries with `% TODO verify` listed in the hand-over message.

## 5. Figures: the `ieee-figures` plugin, typography, panel labels, geometry, diagrams
These rules come from the authors' review of earlier drafts; apply them without being asked.
Reference implementation: `experiments/paper_figs.py` (all plots), `tests/test_figures.py` (audit)
and `paper/figures/src/fig_system.js` (PPTX diagram).

1. **Every plot is built with the `ieee-figures` plugin** vendored in
   `claude-ieee-figures/plugins/ieee-figures` (module `ieeefig/ieeefig.py`; its own skill in
   `skills/ieee-figures/SKILL.md`, API in `references/api.md`, worked recipes in
   `references/recipes.md` - read them before touching a figure). Import it with
   `sys.path.insert(0, "<repo>/claude-ieee-figures/plugins/ieee-figures/ieeefig")`, `import ieeefig as ief`,
   and call `ief.apply_publication_style(ief.FigureStyle(...))` once at start-up; never write a
   per-script `rcParams` block. The plugin's rules (its "rule 7b") are enforced by its helpers and
   re-checked by `ief.assert_house_style(fig)` before every export:
   - one markered line per scheme with straight segments; no error bars, caps, shaded bands or
     smoothing (`make_trend` refuses `show_shadow=True`); uncertainty goes into the table and the text;
   - `xlim` is exactly the first and last swept value and `xticks` are exactly the swept values
     (`make_trend` installs a `FixedLocator`). Log-spaced sweep: `ax.set_xscale("log")` before
     `make_trend` and label the ticks with `tick_labels`; a sweep that contains 0 and spans decades
     (e.g. `tau_cfg` in {0, 0.25, 0.5, 1, 2, 4}) is drawn at equally spaced positions labelled with the
     values (`trend(..., ordinal=True)`);
   - `strict_ticks=False` only for a figure with an axis that is continuous by design (the delay
     threshold of a CCDF, a backlog level); its sweep panels still take their ticks from `make_trend`
     and `tests/test_figures.py` checks them. A parametric trade-off (x is measured, e.g. power versus
     violation probability) is drawn as hollow markers (`ax.scatter`) joined by a `LineCollection`;
     reference guides (target line, diagonal) are `hlines`/`vlines`/`LineCollection`, never `plot`,
     so that the audit sees only data series;
   - IEEE column geometry from `ief.create_subplots(1, n, column="double"|"single", height=...)`
     (7.16-in or 3.5-in canvas; rows of 2-4 panels 1.6-1.9 in tall, single-column figures about 2 in),
     base font 8 pt (ticks and legends 7 pt), all panels of a figure on one canvas with one
     `tight_layout` so their axes boxes are identical. `finalize_figure` crops the PDF: check with
     `pdfinfo` that it is <= 516 pt wide (`\textwidth`) or <= 252 pt (`\columnwidth`) and include it
     with `\includegraphics{name}` - never `width=`;
   - Okabe-Ito colours (`ief.PALETTE`) with colour, marker and line style fixed per scheme across all
     figures (`SERIES` in `paper_figs.py`; proposed scheme = `blue_main`, circle, solid) and distinct
     within every figure; hatch channel on grouped bars (`make_grouped_bar(..., hatches=...)`);
   - vector PDF only, Type-42 fonts (`finalize_figure`); no PNG files in the repository;
   - the script prints one status line per figure (swept points, canvas and cropped size, audit
     result, legend placement) - report it, and treat any WARNING in it as a defect.
2. **Font: Times New Roman for every figure**, passed through
   `ief.FigureStyle(font_family=("Times New Roman", ...))`, with the math faces set to the same font
   once in `apply_style()` (`mathtext.fontset="custom"`, rm/it/bf/sf/tt/cal = Times New Roman,
   fallback `stix`); TrueType embedding comes from the plugin (`pdf.fonttype=42`). If Times New Roman
   is not installed, install it first (MS core fonts: `times32.exe` from
   downloads.sourceforge.net/corefonts, unpack with `cabextract`, copy the TTFs to
   `/usr/share/fonts/truetype/msttcorefonts`, `fc-cache -f`, delete the matplotlib font cache); never
   fall back silently to another font. Diagram text (PPTX) uses the same font.
3. **Box on, grid on** (MATLAB style) for every axes: all four spines
   (`axes.spines.top`/`axes.spines.right` = True, overriding the plugin's two-spine default), inward
   ticks mirrored on the top and right sides (`xtick.top`, `ytick.right`), and a light major grid
   (`ief.FigureStyle(grid=True)`; `grid.linewidth` 0.3, `grid.color` 0.65, `grid.alpha` 0.5; no
   minor grid). The vertical grid is switched off on categorical bar charts (`ax.grid(axis="x",
   visible=False)`). Set once in `apply_style()` next to the font override, never per figure; legends
   keep their opaque white background so that grid lines do not run through the entries.
4. **One PDF per figure; panel labels are only "(a)", "(b)", ... directly under the x-label**, drawn
   by `ief.add_panel_labels` at the height measured from the x-label extent (`finish()` in
   `paper_figs.py`). No panel titles and no text other than the letter; describe the panels in the
   caption ("... versus (a) ..., (b) ..., and (c) ...") and refer to them as `Fig.~\ref{fig:x}(a)`.
   Do not load `subfig`, `caption` or `subcaption` (they change the IEEEtran caption style).
5. **Legends inside the axes and not covering data**: `legend(ax, locs, ncols)` tries the candidate
   corners and column counts, keeps the first that covers no data sample and stays inside the axes
   box, and reports a WARNING otherwise. Frameless look (opaque white background, no edge), short
   labels ("M-LWDF", "Max-weight"). If no corner is free: give the axes head-room (`ylim`), then
   shorten the labels, then use one shared legend row above the panels (`shared_legend`, plugin
   recipe 3; Figs. 4 and 5). Every other panel keeps its own legend.
6. **System diagrams (Fig. 1 and similar) are editable PowerPoint files**, built with pptxgenjs from
   shapes, lines and text boxes (no embedded images), Times New Roman, drawn at 2x the printed size
   with 13-16 pt text (6.5-8 pt printed). Export to PDF with LibreOffice and include it with
   `\includegraphics[width=\columnwidth]{...}`; commit the `.pptx`, the generator script and the `.pdf`.
   Do not use TikZ for figures the authors need to edit. The plugin does not cover schematics.
7. **Audit test**: `tests/test_figures.py` builds every figure and runs `assert_house_style`, checks
   the ticks of the relaxed figures' sweep panels and that a plotted curve equals the results file.
   Run it with the unit tests before committing figures.
8. Probabilities on a log axis, with zero-violation points drawn at the resolution floor
   1/(observed packets); every plotted point inside the y-limits (`make_trend` draws unclipped markers).
