---
name: ieee-paper-writing
description: Rules for drafting IEEE journal manuscripts (TWC/TCOM/TVT) in this repository - page budget for the initial submission, section structure, figure and table economy, placeholders for co-author derivations, and the compile-and-count checklist. Use whenever writing or revising paper/main.tex.
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
- Group sweeps into **multi-panel rows**: `figure*` with 3 panels at `0.32\textwidth`
  (panels generated at 2.25 in x 1.9 in, 7-8 pt fonts) or 4 panels at `0.24\textwidth`
  (1.72 in x 1.55 in). Single-column figures at `0.9\columnwidth`.
- One figure per claim: keep only figures that carry a headline result (the hypothesis figures,
  the CCDF, the cost/energy trade-off, the placement comparison, the analytical validation).
  Robustness/sensitivity results go into one sentence or one compact table.
- Never include: convergence plots of a routine algorithm, illustrative plots of a closed-form
  expression, or a sweep whose curves are parallel to another sweep already shown.
- Every panel needs a legend (<= 6 series), markers + line styles (colour-blind safe palette),
  log y-axis for probabilities, zero-violation points drawn at the resolution floor.

## 3. Structure and style (IEEEtran)
- Abstract <= 250 words: context, gap, method, headline numbers. Index terms 5-8.
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
- [ ] No `Overfull \hbox`, no undefined references/citations.
- [ ] Figures referenced in order; every figure and table discussed in the text.
- [ ] Placeholders: `\todobox` count reported; each one line.
- [ ] `refs.bib` entries with `% TODO verify` listed in the hand-over message.
