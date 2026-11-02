/* Figura (namespace JFS): d3 v7 helpers that draw figures at their final size.
   Units: every figure is an SVG whose user unit is 1 pt; width/height attributes are in mm,
   so the exported file has the final size. Colours and fonts are written as literal
   values (no CSS variables) so the SVG survives Inkscape / Illustrator / rsvg / PDF export. */
(function () {
  "use strict";
  var d3 = window.d3;
  var MM = 72 / 25.4; // pt per mm

  // ---- tokens (fallbacks = DEF; live CSS custom properties win when no theme is set) ----
  var DEF = {
    paper: "#ffffff", ink: "#1a1a1a", "ink-muted": "#4d4d4d", rule: "#7a7a7a", grid: "#d9d9d9", "grid-minor": "#ececec", "fill-soft": "#e6ebf6",
    "house-primary": "#0039a6", "house-deep": "#081b33", "house-tint": "#e6ebf6", "house-signal": "#3361b8",
    "series-1": "#0039a6", "series-2": "#b07800", "series-3": "#b8336a", "series-4": "#2f8ac4", "series-5": "#008060", "series-6": "#8c2d19",
    "oi-orange": "#e69f00", "oi-sky": "#56b4e9", "oi-yellow": "#f0e442",
    "component-1": "#0039a640", "component-2": "#b8336a40", "component-3": "#2f8ac440", "component-4": "#00806040",
    highlight: "#f0e44266", "map-0": "#440154", "map-1": "#3b528b", "map-2": "#21918c", "map-3": "#5ec962", "map-4": "#fde725",
    "div-neg": "#0072b2", "div-mid": "#f7f7f7", "div-pos": "#d55e00"
  };
  var ALIAS = { "exp-data": "ink", "fit-total": "series-2", theory: "series-1", "fit-background": "rule", residual: "rule" };
  // themes override DEF; `neutral` keeps it as it is (a page may add its own, e.g. a dark one)
  var THEMES = {"neutral": {}};
  var ACTIVE = null;
  /** Force a theme for drawing and export (e.g. in Node/Playwright where no page theme exists). null = follow the page. */
  function useTheme(id) { ACTIVE = id && THEMES[id] ? id : null; return ACTIVE; }
  function tok(name) {
    if (ALIAS[name]) return tok(ALIAS[name]);
    if (ACTIVE) return THEMES[ACTIVE][name] || DEF[name];
    try {
      var v = getComputedStyle(document.documentElement).getPropertyValue("--" + name).trim();
      if (/^#|^rgb|^hsl|^oklch/.test(v)) return v;
    } catch (e) {}
    return DEF[name];
  }
  var COLUMNS = { single: 84.6, double: 177.8 }; // mm: single and double column width
  var FONT = "Arial, Helvetica, Arimo, 'Liberation Sans', 'Nimbus Sans', sans-serif";
  /** The three type stacks: sans (default), serif, mono (listings). */
  var FONTS = {
    sans: FONT,
    serif: "'Times New Roman', Times, Tinos, 'Liberation Serif', 'Nimbus Roman', 'TeX Gyre Termes', serif",
    mono: "'Courier New', Courier, Cousine, 'Liberation Mono', 'Nimbus Mono PS', 'TeX Gyre Cursor', monospace"
  };
  var SIZE = { panel: 8, axis: 7, tick: 6, legend: 6, annotation: 6 };
  var STROKE = { axis: 0.5, data: 1, component: 0.75, emphasis: 1.5 };
  function series(i) { return tok("series-" + ((i % 6) + 1)); }
  // tick numbers: no thousands separator (7112, not 7,112), one fixed precision per axis, Unicode minus
  function fixed(sc, n) { var d = sc.domain(), st = d3.tickStep(Math.min(d[0], d[1]), Math.max(d[0], d[1]), n); return d3.format("." + d3.precisionFixed(st) + "f"); }
  var TICK = { major: 2, minor: 1 };
  /** Minor tick values between the majors: 4 subdivisions for a 2-step (2, 20, 0.2), 5 for 1- and 5-steps. */
  function minorTicks(sc, n) {
    var d = sc.domain(), lo = Math.min(d[0], d[1]), hi = Math.max(d[0], d[1]), st = d3.tickStep(lo, hi, n);
    var lead = Math.round(st / Math.pow(10, Math.floor(Math.log10(st) + 1e-9))), m = st / (lead === 2 ? 4 : 5), out = [];
    for (var v = Math.ceil(lo / m - 1e-9) * m; v <= hi + 1e-9; v += m) { if (Math.abs(v / st - Math.round(v / st)) > 1e-6) out.push(+v.toFixed(10)); }
    return out;
  }
  /** Log axes: majors at decades, minors at 2–9 × decade, labels 0.01 … 1000, beyond that 10ⁿ. */
  var SUP = { "-": "\u207b", 0: "\u2070", 1: "\u00b9", 2: "\u00b2", 3: "\u00b3", 4: "\u2074", 5: "\u2075", 6: "\u2076", 7: "\u2077", 8: "\u2078", 9: "\u2079" };
  function logFmt(v) {
    var e = Math.round(Math.log10(v));
    if (e >= -2 && e <= 3) return d3.format("~g")(v);
    return "10" + String(e).split("").map(function (c) { return SUP[c]; }).join("");
  }
  function ticksFor(sc, n, fmt) {
    if (sc.base) {
      var d = sc.domain(), lo = Math.min(d[0], d[1]), hi = Math.max(d[0], d[1]), maj = [], mnr = [];
      for (var e = Math.floor(Math.log10(lo)); e <= Math.ceil(Math.log10(hi)); e++) {
        var dec = Math.pow(10, e);
        if (dec >= lo * 0.999 && dec <= hi * 1.001) maj.push(dec);
        for (var k = 2; k <= 9; k++) { var v = k * dec; if (v > lo && v < hi) mnr.push(v); }
      }
      return { major: maj, minor: mnr, fmt: fmt || logFmt };
    }
    return { major: sc.ticks(n), minor: minorTicks(sc, n), fmt: fmt || fixed(sc, n) };
  }
  function mm(w) { return typeof w === "string" ? COLUMNS[w] : w; }

  // ---- figure: an SVG at final size ----
  function figure(container, o) {
    o = o || {};
    var wmm = mm(o.width || "single"), hmm = o.height || wmm * 0.75;
    var W = wmm * MM, H = hmm * MM, scale = o.displayScale == null ? 2 : o.displayScale;
    var node = typeof container === "string" ? document.querySelector(container) : container;
    var svg = d3.select(node).append("svg")
      .attr("xmlns", "http://www.w3.org/2000/svg")
      .attr("width", wmm + "mm").attr("height", hmm + "mm")
      .attr("viewBox", "0 0 " + W + " " + H)
      .attr("font-family", FONTS[o.font] || FONT).attr("font-size", SIZE.axis).attr("fill", tok("ink"))
      .style("width", (wmm * 96 / 25.4 * scale) + "px").style("height", "auto").style("display", "block")
      .style("background", tok("paper"));
    svg.append("rect").attr("class", "jfs-ground").attr("width", W).attr("height", H).attr("fill", tok("paper"));
    return { svg: svg, W: W, H: H, wmm: wmm, hmm: hmm };
  }

  // ---- axes: inward ticks, 0.5pt spines, no grid, no top/right box unless asked ----
  function axes(parent, o) {
    var r = o.rect, g = parent.append("g").attr("transform", "translate(" + r.x + "," + r.y + ")");
    var x = (o.xScale || (o.xLog ? d3.scaleLog() : d3.scaleLinear())).domain(o.xDomain).range(o.reverseX ? [r.w, 0] : [0, r.w]);
    var y = o.yBand ? d3.scalePoint().domain(o.yBand).range([0, r.h]).padding(0.6)
      : (o.yScale || (o.yLog ? d3.scaleLog() : d3.scaleLinear())).domain(o.yDomain).range([r.h, 0]);
    if (o.nice !== false && !o.yBand && !o.yLog) y.nice();
    function style(sel) {
      sel.selectAll("path.domain").attr("stroke", tok("ink")).attr("stroke-width", STROKE.axis);
      sel.selectAll(".tick line").attr("stroke", tok("ink")).attr("stroke-width", STROKE.axis);
      sel.selectAll(".tick text").attr("fill", tok("ink")).attr("font-size", o.tickSize || SIZE.tick).attr("font-family", null);
      sel.attr("font-family", null).attr("font-size", null);
    }
    var nx = o.xTicks || 5, ny = o.yTicksN || 4;
    var tx = ticksFor(x, nx, o.xFormat), ty = o.yBand ? null : ticksFor(y, ny, o.yFormat);
    // grid under everything else (decorative: grid / grid-minor tokens)
    if (o.grid) {
      var gg = g.append("g").attr("class", "jfs-grid");
      var drawGrid = function (vals, c, axis) {
        vals.forEach(function (v) {
          var p = axis === "x" ? x(v) : y(v);
          gg.append("line").attr("x1", axis === "x" ? p : 0).attr("x2", axis === "x" ? p : r.w).attr("y1", axis === "x" ? 0 : p).attr("y2", axis === "x" ? r.h : p)
            .attr("stroke", c).attr("stroke-width", STROKE.axis);
        });
      };
      var gy = o.yTicks !== false && ty;
      if (o.grid === "both") { drawGrid(tx.minor, tok("grid-minor"), "x"); if (gy) drawGrid(ty.minor, tok("grid-minor"), "y"); }
      drawGrid(tx.major, tok("grid"), "x"); if (gy) drawGrid(ty.major, tok("grid"), "y");
    }
    var xa = g.append("g").attr("class", "jfs-xaxis").attr("transform", "translate(0," + r.h + ")")
      .call(d3.axisBottom(x).tickValues(tx.major).tickFormat(tx.fmt).tickSizeInner(-TICK.major).tickSizeOuter(0).tickPadding(3));
    style(xa);
    if (o.minor !== false) style(g.append("g").attr("transform", "translate(0," + r.h + ")").attr("class", "jfs-minor")
      .call(d3.axisBottom(x).tickValues(tx.minor).tickFormat("").tickSizeInner(-TICK.minor).tickSizeOuter(0)).call(function (s) { s.select("path.domain").remove(); }));
    if (o.xLabel) g.append("text").attr("x", r.w / 2).attr("y", r.h + 17).attr("text-anchor", "middle").attr("font-size", SIZE.axis).text(o.xLabel);
    if (o.yTicks === false) {
      g.append("line").attr("x1", 0).attr("x2", 0).attr("y1", 0).attr("y2", r.h).attr("stroke", tok("ink")).attr("stroke-width", STROKE.axis);
    } else if (o.yBand) {
      // categorical axis: labels only, no ticks
      style(g.append("g").attr("class", "jfs-yaxis").call(d3.axisLeft(y).tickSize(0).tickPadding(4)));
    } else {
      var ya = g.append("g").attr("class", "jfs-yaxis").call(d3.axisLeft(y).tickValues(ty.major).tickFormat(ty.fmt).tickSizeInner(-TICK.major).tickSizeOuter(0).tickPadding(3));
      style(ya);
      if (o.minor !== false) style(g.append("g").attr("class", "jfs-minor")
        .call(d3.axisLeft(y).tickValues(ty.minor).tickFormat("").tickSizeInner(-TICK.minor).tickSizeOuter(0)).call(function (s) { s.select("path.domain").remove(); }));
    }
    if (o.yLabel) g.append("text").attr("transform", "translate(" + (o.yTicks === false ? -6 : -(o.yLabelOffset || 20)) + "," + r.h / 2 + ") rotate(-90)")
      .attr("text-anchor", "middle").attr("font-size", SIZE.axis).text(o.yLabel);
    if (o.box) g.append("rect").attr("width", r.w).attr("height", r.h).attr("fill", "none").attr("stroke", tok("ink")).attr("stroke-width", STROKE.axis);
    var clipId = "jfs-clip-" + Math.random().toString(36).slice(2, 8);
    g.append("clipPath").attr("id", clipId).append("rect").attr("width", r.w).attr("height", r.h);
    var plot = g.append("g").attr("clip-path", "url(#" + clipId + ")");
    return { g: g, plot: plot, x: x, y: y, rect: r };
  }

  function panelLabel(parent, letter, x, y) {
    return parent.append("text").attr("x", x).attr("y", y).attr("font-size", SIZE.panel).attr("font-weight", 700)
      .attr("dominant-baseline", "hanging").text(letter);
  }
  function line(ax, xs, ys, color, width, dash) {
    var pts = xs.map(function (v, i) { return [v, ys[i]]; });
    return ax.plot.append("path").datum(pts).attr("fill", "none").attr("stroke", color).attr("stroke-width", width || STROKE.data)
      .attr("stroke-linejoin", "round").attr("stroke-dasharray", dash || null)
      .attr("d", d3.line().x(function (d) { return ax.x(d[0]); }).y(function (d) { return ax.y(d[1]); }));
  }
  function area(ax, xs, ys, base, fill, stroke) {
    var pts = xs.map(function (v, i) { return [v, ys[i], base ? base[i] : 0]; });
    ax.plot.append("path").datum(pts).attr("fill", fill).attr("stroke", stroke || "none").attr("stroke-width", STROKE.component)
      .attr("d", d3.area().x(function (d) { return ax.x(d[0]); }).y0(function (d) { return ax.y(d[2]); }).y1(function (d) { return ax.y(d[1]); }));
  }
  function directLabel(ax, text, x, y, color, anchor) {
    return ax.g.append("text").attr("x", ax.x(x)).attr("y", ax.y(y)).attr("fill", color || tok("ink"))
      .attr("font-size", SIZE.legend).attr("text-anchor", anchor || "start").text(text);
  }

  // ---- export: standalone SVG string / download ----
  function serialize(f) {
    var node = (f.svg ? f.svg.node() : f).cloneNode(true);
    node.removeAttribute("style");
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + new XMLSerializer().serializeToString(node);
  }
  function download(f, name) {
    var a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([serialize(f)], { type: "image/svg+xml" }));
    a.download = name || "figure.svg"; document.body.appendChild(a); a.click(); a.remove();
  }

  window.JFS = {
    tok: tok, useTheme: useTheme, THEMES: THEMES, minorTicks: minorTicks, FONTS: FONTS, fixedFormat: fixed, ticksFor: ticksFor,
    COLUMNS: COLUMNS, SIZE: SIZE, STROKE: STROKE, MM: MM, FONT: FONT, series: series,
    figure: figure, axes: axes, panelLabel: panelLabel, line: line, area: area, directLabel: directLabel,
    serialize: serialize, download: download
  };
})();
