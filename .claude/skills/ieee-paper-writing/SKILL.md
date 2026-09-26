---
name: ieee-paper-writing
description: Rules for drafting IEEE journal manuscripts (TWC/TCOM/TVT) in this repository - 13-page budget for the initial submission, section structure, figure and table economy, figure typography (Times New Roman, only (a)/(b) under the x-label, equal panel sizes, legends inside axes), editable PPTX system diagrams, placeholders for co-author derivations, and the compile-and-count checklist. Use whenever writing or revising paper/main.tex or any paper figure.
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
- Group sweeps into **multi-panel rows** (`figure*`): 2 panels of 3.40 in, 3 panels of 2.28 in,
  or 4 panels of 1.74 in; single-column figures 3.30 in wide. Section 5 gives the exact rules.
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
- [ ] Figures follow Section 5: Times New Roman, only "(a)", "(b)" under the x-labels, all panels of a
      figure the same size, every legend inside its axes without covering data (the figure script
      prints a warning otherwise - read it), system diagrams as editable PPTX.
- [ ] Placeholders: `\todobox` count reported; each one line.
- [ ] `refs.bib` entries with `% TODO verify` listed in the hand-over message.

## 5. Figures: typography, subfigure labels, panel geometry, diagrams
These rules come from the authors' review of earlier drafts; apply them without being asked.
Reference implementation: `experiments/paper_figs.py` (plots) and `paper/figures/src/fig_system.js` (PPTX diagram).

1. **Font: Times New Roman for every figure** - axis labels, tick labels, legends, annotations and
   diagram text. Math in the same font (matplotlib `mathtext.fontset="custom"`,
   `mathtext.rm="Times New Roman"`, `mathtext.it="Times New Roman:italic"`, fallback `stix`) and
   TrueType embedding (`pdf.fonttype=42`). If Times New Roman is not installed, install it first
   (MS core fonts: `times32.exe` from downloads.sourceforge.net/corefonts, unpack with `cabextract`,
   copy the TTFs to `/usr/share/fonts/truetype/msttcorefonts`, `fc-cache -f`, delete the matplotlib
   font cache); never fall back silently to another serif font.
2. **Subfigure labels: only "(a)", "(b)", ... directly under the x-label.** Each panel is its own PDF;
   in LaTeX use `\subfloat[]{\includegraphics{...}\label{...}}` from `subfig`, loaded as
   `\usepackage[caption=false,font=footnotesize,labelformat=simple,captionskip=1pt,farskip=2pt]{subfig}`
   with `\renewcommand{\thesubfigure}{(\alph{subfigure})}` (references print "Fig. 4(a)").
   Never put descriptive text in a subcaption and never put panel titles in the images: describe
   each panel in the main caption ("... versus (a) ..., (b) ..., and (c) ...").
   Do not load `caption`/`subcaption`: they override the IEEEtran caption style ("Fig. 1." / "TABLE I").
   Centre the label under the x-label, not under the whole image: the panels have a wider left margin
   (y-label, ticks) than right margin, so shift the label by their difference with
   `\newlength{\subshift}\setlength{\subshift}{0.30in}` (left minus right margin printed by the figure script),
   `\DeclareCaptionLabelFormat{xlabelcentered}{\hspace*{\subshift}#2}`, `\captionsetup[subfloat]{labelformat=xlabelcentered}`.
3. **Equal panel geometry.** Generate each panel at its printed size and include it at natural size
   (no `width=` scaling), so the printed fonts are 7-7.5 pt (labels), 6.5-7 pt (ticks), 6-6.5 pt
   (legend). All panels of one figure share the same canvas size and the same axes box: compute the
   margins once for the whole row from the largest tick/label extents and never use
   `bbox_inches="tight"` (it silently shrinks a panel whose label or annotation is longer).
   Short axis labels (e.g. `$\Pr\{D>D_{\max}\}$`, "Average power (mW)"); no annotations outside the axes.
4. **Legends inside the axes, fully inside the axes box and not covering data.** Use short labels
   (scheme names without prefixes, e.g. "M-LWDF", "Max-weight"); place them in an empty corner; let
   the figure script check overflow and overlap and report it. If a legend does not fit: shorten the
   labels, then enlarge the whole row equally (never a single panel), then use one shared legend row
   above the panels. Every panel whose curves need a legend gets its own legend (e.g. both panels of
   a two-panel figure).
5. **System diagrams (Fig. 1 and similar) are editable PowerPoint files**, built with pptxgenjs from
   shapes, lines and text boxes (no embedded images), Times New Roman, drawn at 2x the printed size
   with 13-16 pt text (6.5-8 pt printed). Export to PDF with LibreOffice and include it with
   `\includegraphics[width=\columnwidth]{...}`; commit the `.pptx`, the generator script and the `.pdf`.
   Do not use TikZ for figures the authors need to edit.
6. Colours: the validated categorical palette, colour fixed per scheme across all figures, plus a
   distinct marker and line style per scheme (colour-blind and grayscale safe); probabilities on a
   log axis with zero-violation points drawn at the resolution floor.
