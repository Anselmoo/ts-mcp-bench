"""The run gallery: one self-contained HTML page with every run of one or more run sets as a card.

    tsbench report gallery --runs DIR [--runs DIR2 ...] --out GALLERY.html [--no-figures]

Inputs: the run sets under each `--runs` folder (tsbench.score.run_sets), and per run its transcript
`<model>/<cond>/<effort>/<task>-k<i>.jsonl`, the sidecar `<task>-k<i>.meta.json`, the run set's `scores.csv` and
`MANIFEST.json`, the images in `<task>-k<i>.artifacts/` and the code tsbench.score.artifacts extracts. Only pilot
tasks are looked up.

Three tabs. "All runs": one card per run (model, condition, effort, gateway, task, class, verdict with icon and text,
the per-run figures of tsbench.report.run_figures, the run's own images and code, and a copyable reproduce block).
"Images": every image of every run (files in `<run>.artifacts/`, MCP image results, inline <svg> in the final
answer), grouped by task. "Code": one card per run that has code. Filters for model, condition, task class and verdict
plus a search box; a d3 / JFS chart (Figura design system) of the share correct per model and condition follows the
filters.

The page is one file: d3 7.9.0 and the JFS bundle are inlined from tsbench/_vendor/figura/js. Every figure and image
is embedded as a data URI, within one budget of ~15 MB: the text of the cards is spent first, then the smallest figures
and images are embedded and the rest is only linked (relative link, opens the file next to the run). Raster images above
~300 KB are downscaled when PIL is installed and the budget can still hold them. The per-run figures are minified SVG,
percent-encoded; a byte-identical figure is embedded once and cloned by the page script. Everything from the
runs is HTML-escaped and every SVG is sanitised before it is embedded; the Content-Security-Policy forbids any
external resource.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import pathlib
import re
import urllib.parse

from tsbench.conditions import gateway_label
from tsbench.report import page, reproduce, run_figures
from tsbench.report.base import as_bool, as_run_sets
from tsbench.report.page import href
from tsbench.score import artifacts
from tsbench.score.run_sets import run_sets_in

EMBED_LIMIT = 300 * 1024          # downscale / prefer linking above this many bytes per image
PAGE_BUDGET = 15 * 1024 * 1024    # total page size we aim for
MAX_SVG = 400 * 1024
FILE_CAP = 12000                  # characters of one code block shown (the full file stays on disk)
ENTRY_CAP = 60                    # code blocks shown per run
SHORT_LINES = 18
IMG_SUFFIX = {".png": "image/png", ".svg": "image/svg+xml", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
              ".gif": "image/gif", ".webp": "image/webp"}

# ------------------------------------------------------------------ svg
_SVG_RE = re.compile(r"<svg\b.*?</svg\s*>", re.S | re.I)
_ANIM_RE = re.compile(
    r"<\s*(?:set|animate|animateTransform|animateMotion)\b[^>]*?(?:/\s*>|>.*?<\s*/\s*(?:set|animate|animateTransform|animateMotion)\s*>)",
    re.S | re.I,
)
_HREF_RE = re.compile(r"""((?:xlink:)?href\s*=\s*)(?:"([^"]*)"|'([^']*)'|([^\s>]+))""", re.I)
_URL_RE = re.compile(r"""url\(\s*(['"]?)\s*(?!#)[^)'"]*\1\s*\)""", re.I)
_IMPORT_RE = re.compile(r"@import[^;{]*;?", re.I)
_DOCTYPE_RE = re.compile(r"<!(?:DOCTYPE|ENTITY)[^>]*>|<\?xml-stylesheet[^>]*\?>", re.I)


# active content in SVG: script/style-like blocks, on* handlers, javascript:/data:text/html links
_BLOCK_TAGS = r"script|iframe|object|embed|foreignObject"
_BLOCK_RE = re.compile(rf"<\s*({_BLOCK_TAGS})\b[^>]*?(?:/\s*>|>.*?<\s*/\s*\1\s*>)", re.S | re.I)
_OPEN_RE = re.compile(rf"<\s*/?\s*({_BLOCK_TAGS})\b[^>]*>", re.S | re.I)
_ON_ATTR_RE = re.compile(r"""[\s/]+on[a-z0-9_:-]+\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)""", re.I)
_JS_HREF_RE = re.compile(r"""((?:xlink:)?href\s*=\s*)(["']?)\s*(?:javascript|data\s*:\s*text/html)[^"'>\s]*\2""", re.I)


def _strip_active(svg: str) -> str:
    """Strip active content from an SVG string."""
    prev = None
    while prev != svg:  # nested/overlapping tricks like <scr<script>ipt>
        prev = svg
        svg = _BLOCK_RE.sub("", svg)
        svg = _OPEN_RE.sub("", svg)
        svg = _ON_ATTR_RE.sub("", svg)
    return _JS_HREF_RE.sub(r'\1\2#\2', svg)


def sanitize_svg(svg: str) -> str:
    """Strip active and external content: <script>, on*= handlers, javascript: links (`_strip_active`), animation
    elements that can rewrite href, DOCTYPE/ENTITY, @import, url(...) that is not a #fragment, and every href that is
    not a #fragment or an embedded data:image/ URI."""
    prev = None
    while prev != svg:
        prev = svg
        svg = _strip_active(svg)
        svg = _ANIM_RE.sub("", svg)
        svg = _DOCTYPE_RE.sub("", svg)

    def href(m: re.Match) -> str:
        val = next((g for g in m.groups()[1:] if g is not None), "").strip()
        if val.startswith("#") or re.match(r"data:image/(?:png|jpe?g|gif|webp);base64,[A-Za-z0-9+/=\s]*$", val, re.I):
            return m.group(0)
        return f'{m.group(1)}"#"'

    svg = _HREF_RE.sub(href, svg)
    svg = _IMPORT_RE.sub("", svg)
    return _URL_RE.sub("url(#)", svg)


# matplotlib boilerplate of the per-run figures
_XML_HEAD_RE = re.compile(r"<\?xml[^>]*\?>\s*")
_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
_METADATA_RE = re.compile(r"<metadata\b.*?</metadata\s*>", re.S | re.I)
_NOOP_ROTATE_RE = re.compile(r"""\stransform="rotate\(-?0(?:\.0+)?(?:\s[^)"]*)?\)\"""")
_STYLE_ATTR_RE = re.compile(r"""\sstyle="([^"]*)\"""")
_FAMILY_RE = re.compile(r"font-family:\s*([^;\"]+)")
_STYLE_OPEN_RE = re.compile(r"<(?:style)\b[^>]*>", re.I)  # the SVG's own element, not page markup
_TAG_GAP_RE = re.compile(r">\s*\n\s*<")
_NEWLINE_RE = re.compile(r"\s*\n\s*")


def minify_svg(svg: str) -> str:
    """The same drawing with the boilerplate of a matplotlib SVG removed: XML header, comments, the metadata block,
    `rotate(-0 ...)` no-ops, the font-family that every <text> repeats (said once in a style rule) and the line
    breaks between tags. Run it on sanitised text."""
    svg = _COMMENT_RE.sub("", _METADATA_RE.sub("", _XML_HEAD_RE.sub("", svg)))
    svg = _NOOP_ROTATE_RE.sub("", svg)
    families = _FAMILY_RE.findall(" ".join(_STYLE_ATTR_RE.findall(svg)))
    if len(families) >= 2 and _STYLE_OPEN_RE.search(svg):  # matplotlib always writes a style element
        family = max(set(families), key=families.count).strip()

        def drop(m: re.Match) -> str:
            kept = [d.strip() for d in m.group(1).split(";") if d.strip() and d.strip() != f"font-family: {family}"]
            return f' style="{"; ".join(kept)}"' if kept else ""

        rule = f"text,tspan{{font-family: {family}}}"
        svg = _STYLE_OPEN_RE.sub(lambda m: m.group(0) + rule, _STYLE_ATTR_RE.sub(drop, svg), count=1)
    return _NEWLINE_RE.sub(" ", _TAG_GAP_RE.sub("><", svg)).strip()


def svg_uri(svg: str) -> str:
    """A data URI of SVG text, percent-encoded (about a quarter smaller than base64 for markup)."""
    return "data:image/svg+xml," + urllib.parse.quote(svg, safe=" /:=;,!*()@$+[]?|{}")


def find_svgs(text: str) -> list[str]:
    """Inline <svg>...</svg> documents of a text, unsanitised."""
    return [m.group(0) for m in _SVG_RE.finditer(text or "") if len(m.group(0)) <= MAX_SVG]


def _normalize_svg(svg: str) -> str:
    return re.sub(r"\s+", "", svg)


# ------------------------------------------------------------------ discovery
def _read_json(path: pathlib.Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def load_scores(root: pathlib.Path) -> dict:
    """The rows of a run set's scores.csv by (model, condition, effort, task_id, k); {} without the file."""
    out = {}
    try:
        with open(root / "scores.csv", newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                key = (r.get("model"), r.get("condition"), r.get("effort"), r.get("task_id"), str(r.get("k_index")))
                out[key] = r
    except OSError:
        pass
    return out


def task_class(task_id: str, score_row: dict | None) -> str:
    """The task class from the scores.csv row, else from a pilot id `P-<class>-NN`, else `other`."""
    if score_row and score_row.get("class"):
        return score_row["class"]
    m = re.match(r"^P-([A-Za-z_]+)-\d+", task_id or "")
    return m.group(1) if m else "other"


def verdict_from_scores(row: dict | None) -> str:
    ok = as_bool((row or {}).get("correct", ""))
    return "unscored" if ok is None else "correct" if ok else "wrong"


_TASKS: dict = {}


def pilot_tasks() -> dict:
    """Pilot tasks by id (cached; only the pilot split is ever loaded). {} when the task set cannot be loaded."""
    if "pilot" not in _TASKS:
        try:
            from tsbench.tasks import load
            _TASKS["pilot"] = {t["id"]: t for t in load("pilot")}
        except Exception as exc:  # noqa: BLE001
            run_figures.log(f"pilot task set not loadable ({type(exc).__name__}: {exc})")
            _TASKS["pilot"] = {}
    return _TASKS["pilot"]


def _image_info(path: pathlib.Path, source: str, name: str | None = None) -> dict | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    return {
        "source": source,
        "name": name or path.name,
        "path": path,
        "mime": IMG_SUFFIX.get(path.suffix.lower(), "image/png"),
        "sha256": hashlib.sha256(data).hexdigest(),
        "data": data,
    }


def collect_runs(run_sets, reader=None) -> list[dict]:
    """One dict per transcript of the run sets: identity, verdict, images (list of dicts) and code entries. `reader`
    reads a transcript (default `read_transcript`; the full report passes the one the facts read with, so that no
    transcript is parsed twice)."""
    from tsbench.score.extract import read_transcript
    reader = reader or read_transcript
    runs: list[dict] = []
    manifests: dict = {}
    seen: set[pathlib.Path] = set()
    for rs in as_run_sets(run_sets):
        root = rs.path
        scores = load_scores(root)
        for t in artifacts.find_transcripts(root):
            rt = t.resolve()
            if rt in seen or t.name == "transcript.jsonl":
                continue
            seen.add(rt)
            stem = t.name[: -len(".jsonl")]
            side = _read_json(t.with_name(stem + ".meta.json")) or {}
            parts = t.relative_to(root).parts if t.is_relative_to(root) else t.parts
            model = side.get("model") or (parts[-4] if len(parts) >= 4 else "?")
            cond = side.get("condition") or (parts[-3] if len(parts) >= 3 else "?")
            effort = side.get("effort") or (parts[-2] if len(parts) >= 2 else "?")
            task = side.get("task_id") or re.sub(r"-k\d+$", "", stem)
            k_match = re.search(r"-k(\d+)$", stem)
            k = str(side.get("k") or (k_match.group(1) if k_match else 1))
            row = scores.get((model, cond, effort, task, k))
            task_rec = pilot_tasks().get(task)
            ev = None
            tr = None
            try:
                tr = reader(t)
                ev = run_figures.evaluate(task_rec, tr)
            except Exception as exc:  # noqa: BLE001 - one unreadable transcript must not stop the gallery
                run_figures.log(f"{t.name}: not scored ({type(exc).__name__}: {exc})")
            verdict = ev["verdict"] if ev and ev["verdict"] != "unscored" else verdict_from_scores(row)
            run = {
                "label": rs.name,
                "transcript": t,
                "model": model,
                "cond": cond,
                "effort": effort,
                "task": task,
                "k": k,
                "class": task_rec["class"] if task_rec else task_class(task, row),
                "verdict": verdict,
                "root": root,
                "task_rec": task_rec,
                "ev": ev,
                "figs": [],
                "gateway": None,
                "sha_match": side.get("image_sha_match", side.get("sha_match")),
                "images": [],
                "code": [],
                "code_dir": artifacts.code_dir_of(t),
                "flags": _flags(cond, row, tr),
            }
            view = root / "views" / str(model) / str(cond) / str(effort) / (stem + ".html")
            run["view"] = view if view.exists() else None
            if root not in manifests:
                manifests[root] = reproduce.read_manifest(t, root)
            run["manifest"] = manifests[root]
            run["gateway"] = reproduce.is_gateway(run, run["manifest"])
            calls = artifacts.extract_code(t, tr=tr)
            run["code"] = [c for c in calls if c["kind"] != "image"]
            run["images"] = _images_of_run(t, stem, calls, run["code_dir"], tr)
            runs.append(run)
    runs.sort(
        key=lambda r: (
            r["task"],
            r["model"],
            r["cond"],
            r["effort"],
            r["label"],
            int(r["k"]) if r["k"].isdigit() else 0,
        )
    )
    return runs


def _flags(cond: str, row: dict | None, tr) -> list[str]:
    """The flags of a run (page.run_flags): from its scores.csv row, else counted in the transcript as score_dir
    counts them."""
    if row and row.get("n_tool_uses") not in (None, ""):
        return page.run_flags({**row, "condition": cond})
    if tr is None:
        return []
    from tsbench.score.extract import STRUCTURED_TOOL
    names = [u["name"] for u in tr.tool_uses if u["name"] != STRUCTURED_TOOL]
    return page.run_flags({"condition": cond, "n_tool_uses": len(names),
                           "n_mcp_calls": sum(n.startswith("mcp__") for n in names)})


def _images_of_run(t: pathlib.Path, stem: str, calls: list[dict], code_dir: pathlib.Path, tr=None) -> list[dict]:
    """Every image of one run, each once (by sha256): harvested files, MCP image results, inline <svg> answers."""
    imgs: list[dict] = []
    have_sha: set[str] = set()
    have_svg: set[str] = set()

    def add(info: dict | None):
        if info is None or info["sha256"] in have_sha:
            return
        have_sha.add(info["sha256"])
        if info["mime"] == "image/svg+xml":
            have_svg.add(_normalize_svg(info["data"].decode("utf-8", "replace")))
        imgs.append(info)

    art = t.with_name(stem + ".artifacts")
    if art.is_dir():
        for p in sorted(art.iterdir()):
            if p.is_file() and not p.is_symlink() and p.suffix.lower() in IMG_SUFFIX:
                add(_image_info(p, "artifact"))
    for c in calls:
        if c["kind"] == "image":
            add(_image_info(code_dir / c["path"], "mcp", c["path"]))
    for text in artifacts.answer_texts(tr if tr is not None else t):
        for svg in find_svgs(text):
            if _normalize_svg(svg) in have_svg:
                continue
            data = svg.encode("utf-8")
            sha = hashlib.sha256(data).hexdigest()
            if sha in have_sha:
                continue
            have_sha.add(sha)
            have_svg.add(_normalize_svg(svg))
            imgs.append({"source": "svg-answer", "name": f"answer-{len(imgs) + 1}.svg", "path": None,
                         "mime": "image/svg+xml", "sha256": sha, "data": data})
    return imgs


# ------------------------------------------------------------------ images -> src
def _downscale(data: bytes, mime: str) -> tuple[bytes, str]:
    """Shrink a big raster image with PIL when available; otherwise return it unchanged."""
    try:
        from PIL import Image
    except ImportError:
        return data, mime
    try:
        with Image.open(io.BytesIO(data)) as im:
            im.load()
            w, h = im.size
            best = (data, mime)
            for side in (1400, 1000, 700):
                c = im.copy()
                c.thumbnail((side, side))
                buf = io.BytesIO()
                if mime == "image/jpeg":
                    c.convert("RGB").save(buf, "JPEG", quality=80, optimize=True)
                else:
                    c.save(buf, "PNG", optimize=True)
                if len(buf.getvalue()) < len(best[0]):
                    best = (buf.getvalue(), mime)
                if len(best[0]) <= EMBED_LIMIT:
                    break
            return best
    except Exception:
        return data, mime


class ImagePool:
    """Decides per image or figure whether it is embedded as a data URI or only linked (relative link), within the
    page budget. Images and the per-run figures share the one budget; the smallest are embedded first. A big raster
    image is downscaled only when the budget can still hold it."""

    def __init__(self, out_dir: pathlib.Path):
        self.out_dir = out_dir
        self.items: list[dict] = []
        self.figures: dict[str, dict] = {}  # minified SVG text -> its one item (byte-identical figures share it)

    def add(self, info: dict) -> dict:
        data, mime = info["data"], info["mime"]
        if mime == "image/svg+xml":
            data = sanitize_svg(data.decode("utf-8", "replace")).encode("utf-8")
        item = {"info": info, "data": data, "mime": mime, "embed": False,
                "lazy": mime != "image/svg+xml" and len(data) > EMBED_LIMIT}
        self.items.append(item)
        return item

    def add_figure(self, svg: str, path: pathlib.Path) -> dict:
        """A per-run figure (sanitised, minified SVG text); the same text twice gives the same item."""
        item = self.figures.get(svg)
        if item is None:
            data = svg.encode("utf-8")
            info = {"path": path, "data": data, "mime": "image/svg+xml", "source": "figure", "name": path.name}
            item = {"info": info, "data": data, "mime": info["mime"], "embed": False, "lazy": False,
                    "uri": svg_uri(svg)}
            self.figures[svg] = item
            self.items.append(item)
        return item

    @staticmethod
    def _cost(it: dict) -> int:
        return len(it["uri"]) if "uri" in it else len(it["data"]) * 4 // 3 + 64

    def decide(self, budget: int) -> None:
        """Embed the smallest first while the budget lasts; the rest is linked (or dropped without a file). The big
        raster images come last and are downscaled only while something can still fit."""
        used = 0
        ready = sorted((i for i in self.items if not i["lazy"]), key=self._cost)
        big = sorted((i for i in self.items if i["lazy"]), key=lambda i: len(i["data"]))
        for it in [*ready, *big]:
            if it["lazy"]:
                if used + 64 > budget:  # nothing is left to hold even the smallest image
                    it["embed"] = False if it["info"]["path"] is not None else None
                    continue
                it["data"], it["mime"] = _downscale(it["data"], it["mime"])
                it["lazy"] = False
            cost = self._cost(it)
            if used + cost <= budget:
                it["embed"] = True
                used += cost
            else:
                it["embed"] = False if it["info"]["path"] is not None else None

    def src(self, it: dict) -> str | None:
        """The data URI of an embedded image; None for an image that is only linked or dropped."""
        if not it["embed"]:
            return None
        return it["uri"] if "uri" in it else f"data:{it['mime']};base64,{base64.b64encode(it['data']).decode()}"

    def link(self, it: dict) -> str | None:
        """The relative link to an image that is not embedded (None when there is no file or no relative path)."""
        if it["embed"] is False and it["info"]["path"] is not None:
            return href(it["info"]["path"], self.out_dir)
        return None


# ------------------------------------------------------------------ page data
# The page is templates/gallery.html.j2 (cards in gallery_macros.html.j2). The functions below make plain data for it:
# strings, numbers, lists and dicts, never HTML.
def _opts(values) -> list[str]:
    return sorted({v for v in values if v})


def _attrs(r: dict) -> dict:
    s = " ".join([r["model"], r["cond"], r["task"], r["class"], r["label"], r["verdict"], str(r["effort"]),
                  "gateway" if r.get("gateway") else "", *(page.FLAG_TEXT[f] for f in r.get("flags") or [])]).lower()
    return {"model": r["model"], "cond": r["cond"], "cls": r["class"], "ok": r["verdict"], "s": s}


def sha_text(v, source: str = "", data: bytes | None = None) -> str:
    """What the gallery says about an image's sha256: whether the hash the model reported matches the harvested file.
    An image returned by the MCP server (ts_plot_png) never was a file for the model, so it cannot claim a hash; the
    hash computed from the extracted bytes is shown instead of a missing claim."""
    if "mcp" in str(source).lower():
        digest = hashlib.sha256(data).hexdigest()[:16] if data else "?"
        return f"made by the MCP server · sha256 (computed) {digest}…"
    if v is True or str(v).lower() == "true":
        return "sha256 matches"
    if v is False or str(v).lower() == "false":
        return "sha256 does not match"
    return "sha256: not reported by the model"


def _sha(v, source: str, data: bytes | None) -> dict:
    """sha_text with the colour class of the claim: good, bad, or none."""
    cls = ""
    if "mcp" not in str(source).lower():
        cls = (
            "good"
            if v is True or str(v).lower() == "true"
            else "bad"
            if v is False or str(v).lower() == "false"
            else ""
        )
    return {"text": sha_text(v, source, data), "cls": cls}


def _head(r: dict, out_dir: pathlib.Path) -> dict:
    return {"model": r["model"], "cond": r["cond"], "effort": str(r["effort"]), "k": r["k"], "task": r["task"],
            "cls": r["class"], "label": r["label"], "verdict": r["verdict"],
            "gateway": (gateway_label(reproduce.gateway_url(r.get("manifest") or {})) if r.get("gateway")
                        else "Anthropic API"),
            "flags": [page.FLAG_TEXT[f] for f in r.get("flags") or []],
            "icon": run_figures.VERDICT_ICON.get(r["verdict"], "–"),
            "label_text": run_figures.VERDICT_LABEL.get(r["verdict"], r["verdict"]),
            "view": href(r["view"], out_dir) if r["view"] is not None else None}


def reproduce_text(r: dict) -> str | None:
    """The commands of the copyable reproduce block of a run; None when they cannot be made."""
    try:
        return reproduce.commands(r, r.get("manifest"))
    except Exception as exc:  # noqa: BLE001
        run_figures.log(f"{r.get('task')}: reproduce block failed ({type(exc).__name__}: {exc})")
        return None


def _image_card(r: dict, it: dict, pool: ImagePool, out_dir: pathlib.Path, ident: str = "") -> dict:
    info = it["info"]
    return {"attrs": _attrs(r), "head": _head(r, out_dir), "ident": ident, "src": pool.src(it), "link": pool.link(it),
            "alt": f"{r['task']} {r['model']} {info['name']}", "source": info["source"], "name": info["name"],
            "kb": len(info["data"]) // 1024, "linked": it["embed"] is False,
            "sha": _sha(r["sha_match"], info["source"], info["data"]), "repro": reproduce_text(r)}


def _read_capped(path: pathlib.Path) -> tuple[str, bool]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "", False
    return (text[:FILE_CAP], True) if len(text) > FILE_CAP else (text, False)


def _block(label: str, status: dict, body: str, capped: bool, excerpt: str, rel: str) -> dict:
    lines = body.count("\n") + 1
    return {"label": label, "status": status, "lines": lines, "open": lines <= SHORT_LINES, "body": body,
            "capped": capped, "excerpt": excerpt, "rel": rel}


def _code_blocks(r: dict) -> list[dict]:
    """The code blocks of a run (Bash commands, heredoc files, MCP calls)."""
    blocks = []
    code_dir = r["code_dir"]
    for c in r["code"][:ENTRY_CAP]:
        is_err = c.get("is_error") or (c.get("exit") not in (0, None))
        status = ({"text": f"error (exit {c.get('exit')})", "cls": "bad"} if is_err
                  else ({"text": "exit 0", "cls": "good"} if c.get("exit") == 0 else {"text": "no result", "cls": ""}))
        rel = f"{code_dir.name}/{c['path']}"
        if c["kind"] == "bash":
            body, capped = c.get("skeleton") or "", False
            if len(body) > FILE_CAP:
                body, capped = body[:FILE_CAP], True
            blocks.append(_block(f"Bash #{c.get('call', 0)}", status, body, capped, c.get("result_excerpt", ""), rel))
        elif c["kind"] == "heredoc":
            body, capped = _read_capped(code_dir / c["path"])
            blocks.append(_block(f"heredoc {c['name']} (Bash #{c.get('call', 0)})", status, body, capped, "", rel))
        else:
            body, capped = _read_capped(code_dir / c["path"])
            blocks.append(_block(f"MCP {c['name']}", status, body, capped, c.get("result_excerpt", ""), rel))
    return blocks


def _code_card(r: dict, out_dir: pathlib.Path, ident: str = "") -> dict:
    return {"attrs": _attrs(r), "head": _head(r, out_dir), "ident": ident, "blocks": _code_blocks(r),
            "more": max(len(r["code"]) - ENTRY_CAP, 0),
            "n_files": sum(c["kind"] in ("bash", "heredoc") for c in r["code"]),
            "n_mcp": sum(c["kind"] == "mcp" for c in r["code"]), "repro": reproduce_text(r)}


def figure_svg(path: pathlib.Path) -> str | None:
    """A per-run figure (an SVG made by tsbench.report.run_figures), sanitised like any SVG and minified; None if
    unreadable."""
    try:
        return minify_svg(sanitize_svg(path.read_text(encoding="utf-8")))
    except OSError:
        return None


def figure_data_uri(path: pathlib.Path) -> str | None:
    """A per-run figure as a data URI; None if unreadable."""
    svg = figure_svg(path)
    return None if svg is None else svg_uri(svg)


def _figs(r: dict, pool: ImagePool, refs: dict[int, tuple[dict, pathlib.Path]]) -> list[dict]:
    """The figure entries of a run card. `_place_figures` fills each one once the pool has decided; `refs` maps an
    entry (by id) to its pool item and figure file."""
    out = []
    figs_dir = run_figures.figures_dir_of(r["transcript"])
    for f in r.get("figs") or []:
        svg = figure_svg(figs_dir / f["file"])
        if svg:
            entry = {"alt": f"{f['title']} {r['task']} {r['model']}", "title": f["title"], "src": None, "ident": None,
                     "clone": None, "link": None}
            refs[id(entry)] = (pool.add_figure(svg, figs_dir / f["file"]), figs_dir / f["file"])
            out.append(entry)
    return out


def _place_figures(entries: list[dict], refs: dict[int, tuple[dict, pathlib.Path]], pool: ImagePool) -> None:
    """After `decide`, in page order: the first card with a figure carries its data URI, every byte-identical one
    points to it by id (the page script clones it), a figure beyond the budget is a link to its file."""
    first: dict[int, str] = {}
    for entry in entries:
        it, path = refs[id(entry)]
        if not it["embed"]:
            entry["link"] = href(path, pool.out_dir)
        elif id(it) in first:
            entry["clone"] = first[id(it)]
        else:
            first[id(it)] = entry["ident"] = f"fg-{len(first)}"
            entry["src"] = pool.src(it)


def _run_card(r: dict, out_dir: pathlib.Path, img_ids: list[str], code_id: str | None, pool: ImagePool,
              refs: dict[int, tuple[dict, pathlib.Path]]) -> dict:
    ev = r.get("ev") or {}
    return {"attrs": _attrs(r), "head": _head(r, out_dir),
            "why": ev["reason"] if r["verdict"] != "correct" and ev.get("reason") else None,
            "figs": _figs(r, pool, refs),
            "img_ids": " ".join(img_ids), "code_id": code_id, "n_code": len(r["code"]), "repro": reproduce_text(r)}


def _weight(data) -> int:
    """The text a card carries, in characters; the page budget is spent on it before the images."""
    if isinstance(data, str):
        return len(data)
    if isinstance(data, dict):
        return sum(_weight(v) for v in data.values())
    if isinstance(data, (list, tuple)):
        return sum(_weight(v) for v in data)
    return 0


def context(run_sets, out_dir: pathlib.Path, make_figs: bool = True, reader=None) -> tuple[dict, dict]:
    """The data of the page and its counts: {runs, runs_with_code, code_files, images_by_source, cards, figures, ...}.
    `run_sets`: RunSet objects or plain run folders. `reader`: see `collect_runs`."""
    out_dir = pathlib.Path(out_dir)
    runs = collect_runs(run_sets, reader)

    # per-run figures (matplotlib, Figura style), medians per class for the metric strips
    medians = run_figures.class_medians((r["class"], (r["ev"] or {}).get("metrics")) for r in runs if r["ev"])
    fig_kinds: dict[str, int] = {}
    for r in runs:
        if make_figs and r["ev"]:
            try:
                r["figs"] = run_figures.make_figures(r["transcript"], r["task_rec"], r["ev"], medians.get(r["class"]))
            except Exception as exc:  # noqa: BLE001
                run_figures.log(f"{r['transcript'].name}: no figure ({type(exc).__name__}: {exc})")
        for f in r["figs"]:
            fig_kinds[f["kind"]] = fig_kinds.get(f["kind"], 0) + 1

    pool = ImagePool(out_dir)
    img_items: list[tuple[dict, dict]] = [(r, pool.add(info)) for r in runs for info in r["images"]]
    img_ids: dict[int, list[str]] = {}
    img_html_ids = []
    for n, (r, _it) in enumerate(img_items):
        img_html_ids.append(f"im-{n}")
        img_ids.setdefault(id(r), []).append(f"im-{n}")
    code_runs = [r for r in runs if r["code"]]
    code_ids = {id(r): f"co-{n}" for n, r in enumerate(code_runs)}
    code_cards = [_code_card(r, out_dir, code_ids[id(r)]) for r in code_runs]
    run_cards: dict[str, list[dict]] = {}
    fig_refs: dict[int, tuple[dict, pathlib.Path]] = {}
    for r in runs:
        run_cards.setdefault(r["task"], []).append(
            _run_card(r, out_dir, img_ids.get(id(r), []), code_ids.get(id(r)), pool, fig_refs)
        )
    class_of = {r["task"]: r["class"] for r in runs}
    run_order = sorted(run_cards, key=lambda t: (class_of[t], t))
    # the text of the cards is spent first; images and figures share what is left of the page budget
    text_size = _weight(code_cards) + _weight(list(run_cards.values())) + 900_000
    pool.decide(max(PAGE_BUDGET - text_size, 0))
    figure_entries = [e for t in run_order for c in run_cards[t] for e in c["figs"]]
    _place_figures(figure_entries, fig_refs, pool)

    groups: dict[str, list[dict]] = {}
    for (r, it), ident in zip(img_items, img_html_ids, strict=False):
        groups.setdefault(r["task"], []).append(_image_card(r, it, pool, out_dir, ident))

    by_source: dict[str, int] = {}
    for _, it in img_items:
        by_source[it["info"]["source"]] = by_source.get(it["info"]["source"], 0) + 1
    verdicts: dict[str, int] = {}
    for r in runs:
        verdicts[r["verdict"]] = verdicts.get(r["verdict"], 0) + 1
    classes = {r["class"] for r in runs}
    counts = {
        "runs": len(runs),
        "runs_with_code": len(code_runs),
        "code_files": sum(c["kind"] in ("bash", "heredoc") for r in code_runs for c in r["code"]),
        "mcp_calls": sum(c["kind"] == "mcp" for r in code_runs for c in r["code"]),
        "images": len(img_items),
        "images_by_source": dict(sorted(by_source.items())),
        "embedded": sum(1 for _, i in img_items if i["embed"]),
        "linked": sum(1 for _, i in img_items if i["embed"] is False),
        "cards": len(runs),
        "cards_with_figures": sum(1 for r in runs if r["figs"]),
        "figures": sum(fig_kinds.values()),
        "figures_embedded": sum(1 for e in figure_entries if e["src"] or e["clone"]),
        "figures_linked": sum(1 for e in figure_entries if not (e["src"] or e["clone"])),
        "figures_unique": len(pool.figures),
        "figures_by_kind": dict(sorted(fig_kinds.items())),
        "figures_by_class": dict(
            sorted({c: sum(len(r["figs"]) for r in runs if r["class"] == c) for c in classes}.items())
        ),
        "verdicts": dict(sorted(verdicts.items())),
        "cards_by_class": dict(sorted({c: sum(1 for r in runs if r["class"] == c) for c in classes}.items())),
    }

    ctx = {"title": "Run gallery", "counts": counts, "n_sets": len({r["label"] for r in runs}),
           "models": _opts(r["model"] for r in runs), "conds": _opts(r["cond"] for r in runs),
           "classes": _opts(r["class"] for r in runs), "verdicts": list(run_figures.VERDICT_LABEL.items()),
           "run_tasks": [{"task": t, "cls": class_of[t], "cards": run_cards[t]}
                         for t in run_order],
           "image_tasks": [{"task": t, "cards": groups[t]} for t in sorted(groups)], "code_cards": code_cards}
    return ctx, counts


def build_html(run_sets, out_dir: pathlib.Path, make_figs: bool = True) -> tuple[str, dict]:
    """The page and its counts (see `context`). `run_sets`: RunSet objects or plain run folders."""
    ctx, counts = context(run_sets, out_dir, make_figs)
    return page.render("gallery.html.j2", **ctx, ctx=ctx), counts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tsbench report gallery", description=__doc__.splitlines()[0])
    ap.add_argument("--runs", action="append", required=True, metavar="DIR",
                    help="a run set, or a folder holding run sets (repeatable)")
    ap.add_argument(
        "--no-figures", action="store_true", dest="no_figures", help="do not (re)draw the per-run SVG figures"
    )
    ap.add_argument("--out", required=True, metavar="FILE")
    args = ap.parse_args(argv)
    run_sets = run_sets_in(args.runs)
    if not run_sets:
        ap.error("no run set found under --runs")
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    page, counts = build_html(run_sets, out.parent, make_figs=not args.no_figures)
    out.write_text(page, encoding="utf-8")
    print(out, f"{len(page) / 1e6:.1f} MB")
    print(json.dumps(counts, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
