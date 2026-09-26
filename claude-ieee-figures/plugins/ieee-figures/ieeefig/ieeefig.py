"""IEEE-house-style publication figures.

This module implements the API described by the ``scientific-figure-making``
skill (the ``figures4papers`` repository ships that API as a specification with
no implementation), with the conventions of ``ieee-paper-writing`` rule 7b
enforced rather than merely recommended:

* simulation-result curves are plain markered lines with straight segments —
  no error bars, no caps, no shaded confidence bands, no smoothing;
* ``xlim`` is exactly the first and last swept value, and ``xticks`` are
  exactly the swept values, so every tick marks a simulated point and the end
  markers sit on the axis frame;
* geometry is IEEE column geometry, not large-panel geometry;
* series colors are Okabe-Ito colorblind-safe, and every series also carries a
  distinct marker and line style so the figure survives grayscale printing;
* export is vector PDF with Type-42 fonts, which is what IEEE PDF eXpress
  accepts (Type-3 fonts are rejected).

Usage::

    import sys
    sys.path.insert(0, r"D:\\Research\\_tools\\ieeefig")
    import ieeefig as ief

    ief.apply_publication_style()
    fig, axes = ief.create_subplots(1, 2, column="double")
    ief.make_trend(axes[0], chi, [proposed, baseline], ["Proposed", "MaxCINR"],
                   xlabel=r"Traffic load scale $\\chi$", ylabel="Backlog (Mbit)",
                   yscale="log")
    ief.add_panel_labels(fig, axes)
    ief.assert_house_style(fig)
    ief.finalize_figure(fig, "figures/backlog")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

import matplotlib as mpl
import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.container import ErrorbarContainer
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator

__all__ = [
    "IEEE_SINGLE",
    "IEEE_DOUBLE",
    "PALETTE",
    "DEFAULT_COLORS",
    "DEFAULT_MARKERS",
    "DEFAULT_LINESTYLES",
    "FigureStyle",
    "apply_publication_style",
    "create_subplots",
    "finalize_figure",
    "make_trend",
    "make_grouped_bar",
    "annotate_bars",
    "make_heatmap",
    "make_scatter",
    "make_sphere_illustration",
    "add_panel_labels",
    "assert_house_style",
]


# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

#: Width in inches of one IEEE two-column page column.
IEEE_SINGLE = 3.5
#: Width in inches of the full IEEE two-column text block.
IEEE_DOUBLE = 7.16

#: Okabe-Ito colorblind-safe palette, named for the roles the figures use.
#: Every pair in this set stays distinguishable under deuteranopia,
#: protanopia and tritanopia, which the green/red pairing of the
#: ``figures4papers`` palette does not.
PALETTE = {
    "blue_main": "#0072B2",      # proposed scheme
    "blue_secondary": "#56B4E9",
    "vermillion": "#D55E00",     # the scheme being argued against
    "green": "#009E73",
    "orange": "#E69F00",
    "purple": "#CC79A7",
    "yellow": "#F0E442",
    "black": "#000000",
    "neutral": "#767676",
    # compatibility aliases for scripts written against the figures4papers API
    "red_strong": "#D55E00",
    "green_3": "#009E73",
    "highlight": "#E69F00",
}

#: Series order. The first entry is the proposed scheme.
DEFAULT_COLORS = [
    PALETTE["blue_main"],
    PALETTE["vermillion"],
    PALETTE["green"],
    PALETTE["orange"],
    PALETTE["purple"],
    PALETTE["blue_secondary"],
    PALETTE["black"],
    PALETTE["neutral"],
]

#: One distinct marker per series, so the figure reads in grayscale.
DEFAULT_MARKERS = ["o", "s", "^", "v", "D", "x", "P", "*"]

#: One distinct line style per series, for the same reason.
DEFAULT_LINESTYLES = ["-", "--", "-.", ":", (0, (3, 1, 1, 1)), (0, (5, 1)),
                      (0, (1, 1)), (0, (4, 1, 1, 1, 1, 1))]


@dataclass(frozen=True)
class FigureStyle:
    """rcParams bundle. Defaults are IEEE single-column defaults."""

    font_size: int = 8
    axes_linewidth: float = 0.8
    line_width: float = 1.0
    marker_size: float = 3.5
    use_tex: bool = False
    font_family: tuple[str, ...] = ("Arial", "Helvetica", "DejaVu Sans", "sans-serif")
    grid: bool = False


# --------------------------------------------------------------------------
# Style and layout
# --------------------------------------------------------------------------

def apply_publication_style(style: FigureStyle | None = None) -> None:
    """Configure rcParams once, before any figure is created.

    ``font.family`` is set to the fallback stack rather than to ``helvetica``:
    Helvetica is not installed on Windows and the bare name makes matplotlib
    emit a ``findfont`` warning on every call and silently fall back to
    DejaVu Sans.
    """
    style = style or FigureStyle()
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": list(style.font_family),
        "font.size": style.font_size,
        "axes.titlesize": style.font_size,
        "axes.labelsize": style.font_size,
        "xtick.labelsize": style.font_size - 1,
        "ytick.labelsize": style.font_size - 1,
        "legend.fontsize": style.font_size - 1,
        "axes.linewidth": style.axes_linewidth,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.grid": style.grid,
        "grid.linewidth": 0.4,
        "grid.alpha": 0.4,
        "lines.linewidth": style.line_width,
        "lines.markersize": style.marker_size,
        "legend.frameon": False,
        "legend.handlelength": 2.2,
        "legend.columnspacing": 1.0,
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.major.width": style.axes_linewidth,
        "ytick.major.width": style.axes_linewidth,
        "savefig.bbox": "tight",
        "svg.fonttype": "none",
        # Type-42 (TrueType) rather than Type-3: IEEE PDF eXpress rejects Type-3.
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "text.usetex": style.use_tex,
    })


def create_subplots(nrows: int = 1, ncols: int = 1, figsize: tuple[float, float] | None = None,
                    column: str = "single", height: float | None = None, **kwargs):
    """Return ``(fig, axes)`` with ``axes`` flattened to a 1-D array.

    ``column`` picks the width when ``figsize`` is not given: ``"single"``
    gives :data:`IEEE_SINGLE`, ``"double"`` gives :data:`IEEE_DOUBLE`.
    """
    import matplotlib.pyplot as plt

    if figsize is None:
        if column not in ("single", "double"):
            raise ValueError("column must be 'single' or 'double'")
        width = IEEE_SINGLE if column == "single" else IEEE_DOUBLE
        per_panel_height = height if height is not None else (width / ncols) * 0.78
        figsize = (width, per_panel_height * nrows)
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize, **kwargs)
    axes = np.atleast_1d(np.asarray(axes)).ravel()
    return fig, axes


def finalize_figure(fig, out_path, formats: Sequence[str] | None = None, dpi: int = 600,
                    close: bool = True, pad: float = 0.02, **kwargs) -> list[Path]:
    """Save the figure as vector PDF and return the paths written.

    House default is PDF only at 600 dpi. The DPI matters solely for any
    rasterized artist inside the PDF (a heatmap, a dense scatter); vector
    artists are resolution-independent. Raster formats are still accepted if
    passed explicitly, for a slide deck or a README.
    """
    out_path = Path(out_path)
    if formats is None:
        formats = [out_path.suffix.lstrip(".")] if out_path.suffix else ["pdf"]
    allowed = {"pdf", "svg", "eps", "png", "jpg", "jpeg", "tif", "tiff"}
    bad = sorted(set(f.lower() for f in formats) - allowed)
    if bad:
        raise ValueError(f"unsupported format(s): {bad}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    stem = out_path.with_suffix("")
    written: list[Path] = []
    for fmt in formats:
        target = Path(f"{stem}.{fmt.lower()}")
        fig.savefig(target, dpi=dpi, bbox_inches="tight", pad_inches=pad, **kwargs)
        written.append(target)
    if close:
        import matplotlib.pyplot as plt
        plt.close(fig)
    return written


# --------------------------------------------------------------------------
# Plot helpers
# --------------------------------------------------------------------------

def _series_style(index: int, colors, markers, linestyles):
    colors = colors or DEFAULT_COLORS
    markers = markers or DEFAULT_MARKERS
    linestyles = linestyles or DEFAULT_LINESTYLES
    return (colors[index % len(colors)],
            markers[index % len(markers)],
            linestyles[index % len(linestyles)])


def make_trend(ax, x, y_series, labels, colors=None, ylabel=None, xlabel=None,
               show_shadow: bool = False, markers=None, linestyles=None,
               tick_labels: Sequence[str] | None = None, yscale: str | None = None,
               legend: bool = True, legend_kwargs: dict | None = None):
    """Plot one markered line per scheme, with the axis stopping at the data.

    Rule 7b is enforced here rather than left to the caller: ``xlim`` becomes
    exactly ``(x[0], x[-1])`` and ``xticks`` become exactly ``x``. Markers are
    drawn unclipped so the first and last markers sit on the axis frame instead
    of being cut in half by it.

    ``show_shadow`` exists only to keep the signature compatible with the
    ``scientific-figure-making`` API. Passing ``True`` raises: an uncertainty
    band on a simulation-result figure is what rule 7b forbids, and uncertainty
    belongs in the table and in the paired-difference sentence.
    """
    if show_shadow:
        raise ValueError(
            "show_shadow=True is refused: rule 7b forbids shaded confidence "
            "bands and error bars on simulation-result figures. Report the "
            "interval in the table and in the sentence that states the paired "
            "difference instead."
        )

    x = np.asarray(x, dtype=float)
    if x.ndim != 1:
        raise ValueError("x must be 1-D")
    if x.size < 2:
        raise ValueError("x must contain at least two swept values")
    if not np.all(np.diff(x) > 0):
        raise ValueError("x must be strictly increasing (sort the sweep first)")

    y_series = [np.asarray(y, dtype=float) for y in y_series]
    if len(y_series) != len(labels):
        raise ValueError(f"{len(y_series)} series but {len(labels)} labels")
    for i, y in enumerate(y_series):
        if y.shape != x.shape:
            raise ValueError(f"series {i} has length {y.size}, expected {x.size}")

    for i, (y, label) in enumerate(zip(y_series, labels)):
        color, marker, linestyle = _series_style(i, colors, markers, linestyles)
        ax.plot(x, y, label=label, color=color, marker=marker, linestyle=linestyle,
                markerfacecolor="none", markeredgewidth=0.9, clip_on=False,
                zorder=3 + i)

    if yscale:
        ax.set_yscale(yscale)
    # Rule 7b: the axes stop at the data, and every tick marks a simulated point.
    ax.set_xlim(x[0], x[-1])
    ax.xaxis.set_major_locator(FixedLocator(x))
    if tick_labels is not None:
        if len(tick_labels) != x.size:
            raise ValueError("tick_labels must have one entry per swept value")
        ax.set_xticklabels(list(tick_labels))
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if legend:
        ax.legend(**(legend_kwargs or {}))
    return ax


def make_grouped_bar(ax, categories, series, labels, ylabel: str = "Value", colors=None,
                     annotate: bool = False, hatches: Sequence[str] | None = None,
                     bar_width: float | None = None, fmt: str = "{:.2f}"):
    """Grouped bars with black edges, and an optional hatch channel.

    The hatch channel is what keeps adjacent bars separable once the journal
    prints the figure in grayscale.
    """
    categories = list(categories)
    series = [np.asarray(s, dtype=float) for s in series]
    if len(series) != len(labels):
        raise ValueError(f"{len(series)} series but {len(labels)} labels")
    for i, s in enumerate(series):
        if s.size != len(categories):
            raise ValueError(f"series {i} has {s.size} values, expected {len(categories)}")

    n = len(series)
    width = bar_width if bar_width is not None else 0.8 / n
    positions = np.arange(len(categories), dtype=float)
    bars = None
    for i, (values, label) in enumerate(zip(series, labels)):
        color, _, _ = _series_style(i, colors, None, None)
        offset = (i - (n - 1) / 2) * width
        bars = ax.bar(positions + offset, values, width=width, label=label,
                      color=color, edgecolor="black", linewidth=0.6,
                      hatch=(hatches[i % len(hatches)] if hatches else None),
                      zorder=3)
        if annotate:
            annotate_bars(ax, bars, fmt=fmt)

    ax.set_xticks(positions)
    ax.set_xticklabels(categories)
    ax.set_ylabel(ylabel)
    ax.legend()
    return bars


def annotate_bars(ax, bars, fmt: str = "{:.2f}", fontsize: int | None = None,
                  padding: float = 2.0) -> None:
    """Print each bar's value above it."""
    fontsize = fontsize or (mpl.rcParams["font.size"] - 2)
    for bar in bars:
        height = bar.get_height()
        ax.annotate(fmt.format(height),
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, padding), textcoords="offset points",
                    ha="center", va="bottom", fontsize=fontsize)


def make_heatmap(ax, matrix, x_labels=None, y_labels=None, cmap: str = "viridis",
                 cbar_label: str | None = None, annotate: bool = False,
                 fmt: str = "{:.2f}", vmin: float | None = None, vmax: float | None = None):
    """Render a 2-D heatmap.

    The default colormap is ``viridis`` rather than ``magma``: it is
    perceptually uniform *and* monotone in lightness, so it survives grayscale
    conversion, which a diverging or a hue-cycling map does not.
    """
    matrix = np.asarray(matrix, dtype=float)
    if matrix.ndim != 2:
        raise ValueError("matrix must be 2-D")

    im = ax.imshow(matrix, cmap=cmap, aspect="auto", vmin=vmin, vmax=vmax)
    if x_labels is not None:
        if len(x_labels) != matrix.shape[1]:
            raise ValueError("x_labels length must equal the number of columns")
        ax.set_xticks(np.arange(matrix.shape[1]))
        ax.set_xticklabels(list(x_labels))
    if y_labels is not None:
        if len(y_labels) != matrix.shape[0]:
            raise ValueError("y_labels length must equal the number of rows")
        ax.set_yticks(np.arange(matrix.shape[0]))
        ax.set_yticklabels(list(y_labels))
    if cbar_label is not None:
        cbar = ax.figure.colorbar(im, ax=ax)
        cbar.set_label(cbar_label)
        cbar.outline.set_linewidth(mpl.rcParams["axes.linewidth"])
    if annotate:
        mid = 0.5 * (np.nanmin(matrix) + np.nanmax(matrix))
        for r in range(matrix.shape[0]):
            for c in range(matrix.shape[1]):
                ax.text(c, r, fmt.format(matrix[r, c]), ha="center", va="center",
                        fontsize=mpl.rcParams["font.size"] - 2,
                        color="white" if matrix[r, c] < mid else "black")
    return im


def make_scatter(ax, x, y, label=None, color=None, size: float = 12, alpha: float = 0.8,
                 marker: str = "o"):
    """Single-series scatter."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.shape != y.shape:
        raise ValueError("x and y must have the same shape")
    return ax.scatter(x, y, label=label, color=color or PALETTE["blue_main"],
                      s=size, alpha=alpha, marker=marker, linewidths=0.5,
                      edgecolors="none", zorder=3)


def make_sphere_illustration(ax, light_dir=(-0.5, 0.5, 0.8), resolution: int = 128,
                             alpha: float = 0.6, color=None):
    """Draw a Lambertian-shaded disk that reads as a 3-D sphere.

    For conceptual diagrams only; kept for parity with the
    ``scientific-figure-making`` API.
    """
    from matplotlib.colors import LinearSegmentedColormap, to_rgb

    grid = np.linspace(-1.0, 1.0, resolution)
    xx, yy = np.meshgrid(grid, grid)
    rr = xx ** 2 + yy ** 2
    inside = rr <= 1.0
    zz = np.sqrt(np.clip(1.0 - rr, 0.0, None))

    light = np.asarray(light_dir, dtype=float)
    light /= np.linalg.norm(light)
    shade = np.clip(xx * light[0] + yy * light[1] + zz * light[2], 0.0, 1.0)
    shade = np.where(inside, shade, np.nan)

    base = np.asarray(to_rgb(color or PALETTE["blue_main"]))
    cmap = LinearSegmentedColormap.from_list("sphere", [base * 0.15, base, np.ones(3)])
    img = ax.imshow(shade, cmap=cmap, extent=(-1, 1, -1, 1), origin="lower",
                    alpha=alpha, interpolation="bilinear")
    ax.set_aspect("equal")
    ax.set_axis_off()
    return img


def add_panel_labels(fig, axes, labels: Iterable[str] | None = None, y: float = -0.28,
                     fontsize: int | None = None) -> None:
    """Put ``(a)``, ``(b)``, … under each panel, centred on its axes."""
    axes = np.atleast_1d(np.asarray(axes)).ravel()
    if labels is None:
        labels = [f"({chr(ord('a') + i)})" for i in range(axes.size)]
    labels = list(labels)
    if len(labels) != axes.size:
        raise ValueError("one label per axes is required")
    fontsize = fontsize or mpl.rcParams["font.size"]
    for ax, label in zip(axes, labels):
        ax.text(0.5, y, label, transform=ax.transAxes, ha="center", va="top",
                fontsize=fontsize)


# --------------------------------------------------------------------------
# Audit
# --------------------------------------------------------------------------

def assert_house_style(fig, strict_ticks: bool = True) -> None:
    """Fail if the figure violates rule 7b. Call it before exporting.

    Checks, on every axes that carries line data:

    * no ``ErrorbarContainer`` — no error bars or caps;
    * no ``PolyCollection`` — no ``fill_between`` uncertainty band;
    * ``xlim`` equals the first and last plotted x value;
    * ``xticks`` equal the plotted x values exactly, so every tick marks a
      simulated point (disable with ``strict_ticks=False`` for a figure whose
      x axis is categorical or continuous by design).

    This is meant to be called from an audit test as well as from the plotting
    script, so that a figure cannot regress silently after a late edit.
    """
    problems: list[str] = []
    for index, ax in enumerate(fig.axes):
        lines = [ln for ln in ax.get_lines() if ln.get_xdata(orig=False).size > 1]
        if not lines:
            continue
        name = ax.get_label() or f"axes[{index}]"

        if any(isinstance(c, ErrorbarContainer) for c in ax.containers):
            problems.append(f"{name}: error bars present (rule 7b)")
        if any(isinstance(c, PolyCollection) for c in ax.collections):
            problems.append(f"{name}: fill_between band present (rule 7b)")

        xdata = np.asarray(lines[0].get_xdata(orig=False), dtype=float)
        for ln in lines[1:]:
            other = np.asarray(ln.get_xdata(orig=False), dtype=float)
            if other.shape != xdata.shape or not np.allclose(other, xdata):
                problems.append(f"{name}: series are plotted on different x grids")
                break

        lo, hi = ax.get_xlim()
        if not (np.isclose(lo, xdata.min()) and np.isclose(hi, xdata.max())):
            problems.append(
                f"{name}: xlim is ({lo:.6g}, {hi:.6g}) but the data span is "
                f"({xdata.min():.6g}, {xdata.max():.6g}) (rule 7b)")

        if strict_ticks:
            ticks = np.asarray(ax.get_xticks(), dtype=float)
            ticks = ticks[(ticks >= xdata.min() - 1e-9) & (ticks <= xdata.max() + 1e-9)]
            if ticks.size != xdata.size or not np.allclose(ticks, xdata):
                problems.append(
                    f"{name}: xticks are not exactly the swept values (rule 7b); "
                    f"got {ticks.size} ticks for {xdata.size} simulated points")

    if problems:
        raise AssertionError("house-style violations:\n  - " + "\n  - ".join(problems))


def _line_artists_unused() -> None:  # pragma: no cover - keeps Line2D import meaningful
    _ = Line2D
