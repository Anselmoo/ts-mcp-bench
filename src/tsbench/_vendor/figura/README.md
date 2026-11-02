# Figura (vendored)

Figura is a small figure style for matplotlib and d3: figures at their final size in mm, 7 / 6 pt text, inward
ticks, literal colours. tsbench keeps a copy of the parts it uses here.

| File | Content | Used by |
|---|---|---|
| `jfs.py` | matplotlib helpers: column widths, colour theme, font set-up, panel labels | `tsbench.figures` (render, plots, listing), `tsbench.report.run_figures` |
| `jfs.mplstyle` | matplotlib style sheet (sizes, ticks, fonts) | the same modules, through `plt.style.use` |
| `js/bundle.js` | d3 helpers in `window.JFS`: tokens, themes, `figure`, `axes`, `panelLabel`, SVG download | the report pages; `tsbench.report.page` inlines it, `templates/runtime.js` draws with it |
| `js/d3.min.js` | d3 7.9.0 | needed by `bundle.js`; inlined next to it |

The report pages are single HTML files: `tsbench.report.page.figura_js()` reads both scripts as text and inlines
them into each page.

## Licences

- `js/d3.min.js`: d3 7.9.0, ISC licence, Copyright 2010-2023 Mike Bostock.
- `jfs.py`, `jfs.mplstyle`, `js/bundle.js`: Figura, by the author of tsbench, MIT licence (see `LICENSE` at the repository root).

## Local changes

- Demo components and their sample data are removed from `js/bundle.js`; it keeps the helpers listed above.
- The publisher themes and column presets are replaced by one neutral theme (`neutral`, the colours tsbench draws
  with) and two widths, `single` (84.6 mm) and `double` (177.8 mm). The graphical-abstract presets and the unused
  export helper of `jfs.py` are removed.
