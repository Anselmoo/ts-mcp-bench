"""Static SVG figures of the full report, one module per chart family.

Every function is pure: it takes plain data (lists, dicts, numbers, strings) and returns one SVG string. No file I/O, no
script. The shared helpers (scales, axes, legend, text, colours) are in `base`; the classes they write are styled by
templates/svg.css, so the figures follow the page in light and dark mode.
"""
