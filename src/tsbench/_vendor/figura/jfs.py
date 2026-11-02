"""Figura helpers for matplotlib: figures at their final size, panel labels, colour theme and font set-up."""
from __future__ import annotations
import string
import matplotlib.pyplot as plt

MM = 1 / 25.4  # inch per mm
COLUMNS = {  # mm: single and double column width
    "single": 84.6, "double": 177.8,
}
COLORS = {
    "ink": "#1a1a1a", "ink-muted": "#4d4d4d", "rule": "#7a7a7a", "grid": "#d9d9d9", "fill-soft": "#e6ebf6",
    "series-1": "#0039a6", "series-2": "#b07800", "series-3": "#b8336a", "series-4": "#2f8ac4",
    "series-5": "#008060", "series-6": "#8c2d19", "oi-orange": "#e69f00", "oi-sky": "#56b4e9", "oi-yellow": "#f0e442",
    "exp-data": "#1a1a1a", "fit-total": "#b07800", "theory": "#0039a6", "fit-background": "#7a7a7a", "residual": "#7a7a7a",
    "highlight": "#f0e44266", "div-neg": "#0072b2", "div-mid": "#f7f7f7", "div-pos": "#d55e00",
    "paper": "#ffffff", "grid-minor": "#ececec",
    "house-primary": "#0039a6", "house-deep": "#081b33", "house-tint": "#e6ebf6", "house-signal": "#3361b8",
    "map-0": "#440154", "map-1": "#3b528b", "map-2": "#21918c", "map-3": "#5ec962", "map-4": "#fde725",
}
COMPONENT_EDGE = ["series-1", "series-3", "series-4", "series-5"]
NEUTRAL = dict(COLORS)
# Themes override NEUTRAL; `neutral` keeps it as it is
THEMES = {
 "neutral": {},
}


def use_theme(name: str = "neutral"):
    """Switch COLORS and the axes colour cycle to a theme of THEMES; an unknown name gets the neutral colours."""
    if name not in THEMES:
        THEMES[name] = {}
    COLORS.clear(); COLORS.update(NEUTRAL); COLORS.update(THEMES[name])
    for k in ("exp-data",): COLORS[k] = COLORS["ink"]
    COLORS["fit-total"], COLORS["theory"] = COLORS["series-2"], COLORS["series-1"]
    plt.rcParams["axes.prop_cycle"] = plt.cycler(color=[COLORS[f"series-{i}"] for i in range(1, 7)])
    for k in ("axes.edgecolor", "axes.labelcolor", "text.color", "xtick.color", "ytick.color"):
        plt.rcParams[k] = COLORS["ink"]


def figure(width: str | float = "single", height_mm: float | None = None, **subplots_kw):
    """Figure at its final size. width: a COLUMNS key or mm. Uses constrained layout."""
    w = COLUMNS[width] if isinstance(width, str) else float(width)
    h = height_mm if height_mm is not None else w * 0.75
    subplots_kw.setdefault("layout", "constrained")
    fig, axs = plt.subplots(figsize=(w * MM, h * MM), **subplots_kw)
    return fig, axs


def panel_labels(axs, start: str = "a", x: float = -0.02, y: float = 1.0):
    """8pt bold upright lowercase panel letters in the top-left corner of each axes."""
    axs = getattr(axs, "flat", axs if isinstance(axs, (list, tuple)) else [axs])
    i0 = string.ascii_lowercase.index(start)
    for i, ax in enumerate(axs):
        ax.text(x, y, string.ascii_lowercase[i0 + i], transform=ax.transAxes, fontsize=8,
                fontweight="bold", va="bottom", ha="right")


def component(ax, x, y, base, i: int):
    """Fit component: 25 % fill + outline in its series colour."""
    c = COLORS[COMPONENT_EDGE[i % 4]]
    ax.fill_between(x, base, base + y, color=c, alpha=0.25, lw=0)
    ax.plot(x, base + y, color=c, lw=0.75)


def use_font(family: str = "sans-serif"):
    """'sans-serif' or 'serif'. Mathtext follows the chosen face."""
    plt.rcParams["font.family"] = family
    plt.rcParams["mathtext.fontset"] = "custom"
    from matplotlib import font_manager
    installed = {f.name for f in font_manager.fontManager.ttflist}
    stack = plt.rcParams["font." + ("serif" if family == "serif" else "sans-serif")]
    face = next((n for n in stack if n in installed), stack[0])  # first installed face of the stack
    for k in ("rm", "it", "bf"):
        plt.rcParams["mathtext." + k] = face + {"rm": "", "it": ":italic", "bf": ":bold"}[k]


def grid(ax, which: str = "major"):
    """Optional grid under the data: 'major' (grid token) or 'both' (adds grid-minor)."""
    ax.grid(True, which="major", color=COLORS["grid"], lw=0.5)
    if which == "both":
        ax.grid(True, which="minor", color="#ececec", lw=0.5)


def inset_zoom(ax, xlim, ylim, bounds=(0.05, 0.55, 0.4, 0.4), magnification_label: bool = True):
    """Magnified inset: box on the parent in `rule`, dashed leaders, inset framed in `ink`.
    Returns the inset axes; plot into it like any axes."""
    ia = ax.inset_axes(bounds, xlim=xlim, ylim=ylim)
    ia.tick_params(labelsize=6, length=2)
    ia.set_yticks([])
    for sp in ia.spines.values():
        sp.set_visible(True); sp.set_linewidth(0.5)
    ind = ax.indicate_inset_zoom(ia, edgecolor=COLORS["rule"], lw=0.5, alpha=1)
    # matplotlib >= 3.10 returns an InsetIndicator, older versions a (rectangle, connectors) tuple
    rect, lines = (ind.rectangle, ind.connectors) if hasattr(ind, "connectors") else ind
    for c in [rect, *(lines or [])]:
        c.set_linewidth(0.5); c.set_alpha(1)
        c.set_linestyle((0, (1.5 / 0.5, 1 / 0.5)))  # dash tuples scale with linewidth: 1.5 pt on, 1 pt off
    if magnification_label:
        mag = (ax.get_ylim()[1] - ax.get_ylim()[0]) / (ylim[1] - ylim[0])
        ia.text(0.03, 0.95, f"×{mag:.0f}", transform=ia.transAxes, fontsize=6, va="top", color=COLORS["ink-muted"])
    return ia
