"""Per-run views and their index: one HTML page per transcript of a run set, rendered from plan, transcripts and scores.

    tsbench report views --runs DIR [--runs DIR2 ...] [--out OVERVIEW.html] [--split pilot] [--i-have-preregistered DOI]

For every run set (a folder with MANIFEST.json, see tsbench.score.run_sets) this writes
`<run set>/views/<model>/<cond>/<effort>/<task>-k<i>.html` (one page per transcript) and `<run set>/views/INDEX.html`
(a sortable table of all runs, each linking its page). With `--out` an overview page lists every run set and links its
index. A page shows: the run's identity (model, condition, effort, task, k, plan id), the user and system prompt
(from `plan.jsonl`, else from the pilot task set and the system-prompt file named in the sidecar), the images the runner
harvested, the final answer and the JSON line parsed from it, every tool call with its (truncated) result, the result
event (turns, cost, time) and the `scores.csv` row.

Every page is self-contained (inline CSS and one small inline sort script, no external resource, a strict
Content-Security-Policy), light and dark by `prefers-color-scheme`. The pages are filled from the templates
`views*.html.j2` (tsbench/report/templates/); this module only prepares their data. Transcripts are untrusted: the
templates escape every string that comes from them. The output is a pure function of its inputs (no timestamp). A run
set made on the confirmatory split is refused without `--i-have-preregistered <DOI>`.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import sys
import urllib.parse

from tsbench import plan as plan_mod
from tsbench.core.prereg import is_doi
from tsbench.report import page
from tsbench.report.base import run_split
from tsbench.report.page import href
from tsbench.score.extract import final_answer, read_transcript
from tsbench.score.run_sets import RunSet, run_sets_in
from tsbench.score.score import find_transcripts

TRUNCATE_CHARS = 2000
INPUT_TRUNC_CHARS = 4000

def truncate(text: str, limit: int = TRUNCATE_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [truncated, {len(text) - limit} more characters]"


def _text(value) -> str:
    """A value as the page shows it: None is empty."""
    return "" if value is None else str(value)


def _macros():
    return page.ENV.get_template("views_macros.html.j2").module


# ------------------------------------------------------------------ inputs
def read_scores(runs: pathlib.Path) -> tuple[dict, str | None]:
    path = runs / "scores.csv"
    if not path.is_file():
        return {}, None
    rows = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            rows[(row["model"], row["condition"], row["effort"], row["task_id"], row["k_index"])] = row
    return rows, hashlib.sha256(path.read_bytes()).hexdigest()


EMBED_MAX_BYTES = 2 * 1024 * 1024
_IMAGE_MIME = {".png": "image/png", ".svg": "image/svg+xml"}


def harvested_images(tp: pathlib.Path, meta: dict) -> list[dict]:
    """The images the runner harvested for a transcript (`<stem>.artifacts/`, listed in the sidecar's `artifacts`) as
    [{name, sha256, sha_ok, uri}]. `uri` is a base64 data URI (None when the file is missing, a symlink, too big to
    embed or of another type); `sha_ok` says whether the file still has the recorded sha256. Model-written SVG is only
    ever shown through an <img> data URI, never inlined, so it cannot run script."""
    import base64
    out = []
    folder = tp.with_name(tp.name[: -len(".jsonl")] + ".artifacts")
    for a in meta.get("artifacts") or []:
        name = a.get("name") if isinstance(a, dict) else None
        if not isinstance(name, str) or not name or name != pathlib.PurePath(name).name:
            continue
        mime = _IMAGE_MIME.get(pathlib.PurePath(name).suffix.lower())
        path = folder / name
        item = {"name": name, "sha256": a.get("sha256"), "sha_ok": False, "uri": None}
        try:
            if mime and path.is_file() and not path.is_symlink() and path.stat().st_size <= EMBED_MAX_BYTES:
                data = path.read_bytes()
                item["sha_ok"] = hashlib.sha256(data).hexdigest() == a.get("sha256")
                item["uri"] = f"data:{mime};base64," + base64.b64encode(data).decode("ascii")
        except OSError:
            pass
        out.append(item)
    return out


def images_html(images: list[dict], match=None, max_width: int = 480) -> str:
    """<figure> blocks for harvested images (empty string for none), as Markup."""
    return _macros().images(images, match, max_width)


def read_sidecar(tp: pathlib.Path) -> dict:
    try:
        d = json.loads(tp.with_name(tp.name[: -len(".jsonl")] + ".meta.json").read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def system_prompt_from_argv(meta: dict, runs: pathlib.Path | None = None) -> str | None:
    """The system prompt a run was given, read from the file named after `--system-prompt-file` in the sidecar's argv
    (an `<OUT>/` placeholder is resolved against the run folder `runs`, a `<REPO>/` one against this checkout); None
    when it is not there."""
    argv = meta.get("argv")
    if isinstance(argv, list) and "--system-prompt-file" in argv:
        try:
            raw = str(argv[argv.index("--system-prompt-file") + 1])
            if raw.startswith("<OUT>/"):  # sidecars hold placeholders, not host paths
                if runs is None:
                    return None
                base = pathlib.Path(runs).resolve()
                path = (base / raw[len("<OUT>/"):]).resolve()
                if not path.is_relative_to(base):
                    return None
            else:
                if raw.startswith("<REPO>/"):
                    raw = str(pathlib.Path(__file__).resolve().parents[3] / raw[len("<REPO>/"):])
                path = pathlib.Path(raw)
            if path.is_file():
                return path.read_text(encoding="utf-8")
        except (IndexError, OSError):
            return None
    return None


# ------------------------------------------------------------------ one view
def tool_calls(events: list[dict]) -> list[dict]:
    """Tool calls in order, each with its result (if any) attached by tool_use_id."""
    calls: list[dict] = []
    by_id: dict = {}
    for ev in events:
        content = ((ev.get("message") or {}).get("content")) if isinstance(ev.get("message"), dict) else None
        if not isinstance(content, list):
            continue
        for blk in content:
            if not isinstance(blk, dict):
                continue
            if ev.get("type") == "assistant" and blk.get("type") == "tool_use":
                uid = blk.get("id")
                if isinstance(uid, str) and uid in by_id:  # the same call repeated in the stream counts once
                    continue
                call = {"name": blk.get("name", ""), "input": blk.get("input"), "id": uid, "result": None,
                        "is_error": False}
                calls.append(call)
                if isinstance(uid, str):  # a list or dict id cannot be a key and gets no result
                    by_id[uid] = call
            elif ev.get("type") == "user" and blk.get("type") == "tool_result":
                rid = blk.get("tool_use_id")
                call = by_id.get(rid) if isinstance(rid, str) else None
                if call is not None:
                    from tsbench.score.extract import flatten_text as _flatten
                    call["result"] = _flatten(blk.get("content"))
                    call["is_error"] = bool(blk.get("is_error"))
    return calls


def render_view(*, rid: str, rel: pathlib.PurePosixPath, tr, meta: dict, record: dict | None, score_row: dict | None,
                fallback_prompt: str | None, fallback_system: str | None, plan_id: str | None,
                raw_path: pathlib.Path | None = None) -> str:
    depth = len(rel.parts)  # views/<m>/<c>/<e>/<file>: climb to <runs>
    raw_href = "../" * depth + urllib.parse.quote(str(rel.with_suffix(".jsonl")))
    index_href = "../" * (depth - 1) + "INDEX.html"
    prompt = record["prompt"] if record else fallback_prompt
    system = record["system_prompt_text"] if record else fallback_system
    res = tr.result or {}
    answer_text = tr.result_text or (tr.assistant_texts[-1] if tr.assistant_texts else "")
    parsed = final_answer(tr.result_text, tr.result.get("structured_output")) if tr.result is not None else None
    facts = [("model", (meta.get("model") or rid.split('/')[0])), ("condition", meta.get("condition")),
             ("effort", meta.get("effort")), ("task", meta.get("task_id")), ("k", meta.get("k")),
             ("plan_id", plan_id), ("reported model", meta.get("reported_model") or (tr.init or {}).get("model")),
             ("claude", meta.get("claude_version"))]
    if record is None:  # the sidecar may be missing too: fall back on the path
        p = rel.parts
        facts[0:5] = [("model", p[0]), ("condition", p[1]), ("effort", p[2]), ("task", rel.stem.rsplit("-k", 1)[0]),
                      ("k", rel.stem.rsplit("-k", 1)[-1])]
    calls = []
    for i, c in enumerate(tool_calls(tr.events), 1):
        inp = c["input"] if isinstance(c["input"], str) else json.dumps(c["input"], indent=1, ensure_ascii=False,
                                                                       sort_keys=True)
        state = "error" if c["is_error"] else ("no result" if c["result"] is None else "")
        calls.append({"n": i, "name": _text(c["name"]), "state": state, "input": truncate(inp or "", TRUNCATE_CHARS),
                      "result": truncate(c["result"] or "", TRUNCATE_CHARS)})
    score = None
    if score_row is not None:
        good = str(score_row.get("correct")).lower() in ("true", "1")
        score = {"good": good, "rows": [(_text(k), _text(v)) for k, v in score_row.items() if v != ""]}
    imgs = harvested_images(raw_path, meta) if raw_path is not None else []
    return page.render(
        "views.html.j2", title=rid, rid=rid, index_href=index_href, raw_href=raw_href,
        facts=[(k, _text(v)) for k, v in facts if v not in (None, "")],
        flags=[_text(f) for f in meta.get("flags") or []],
        prompt=truncate(prompt, INPUT_TRUNC_CHARS) if prompt else None,
        system=truncate(system, INPUT_TRUNC_CHARS) if system else None,
        argv=truncate(" ".join(record["argv_template"]), INPUT_TRUNC_CHARS) if record else None,
        images=imgs, image_match=meta.get("image_sha_match"),
        answer=truncate(answer_text, INPUT_TRUNC_CHARS) if answer_text else None,
        parsed=(
            truncate(json.dumps(parsed, indent=1, sort_keys=True), INPUT_TRUNC_CHARS) if parsed is not None else None
        ),
        has_result=tr.result is not None, n_calls=sum(c["name"] != "StructuredOutput" for c in calls), calls=calls,
        run_rows=[(label, _text(val)) for label, val in (
            ("result subtype", res.get("subtype")), ("is_error", res.get("is_error")), ("turns", res.get("num_turns")),
            ("cost USD", res.get("total_cost_usd")), ("wall time s", meta.get("wall_time_s")),
            ("exit code", meta.get("exit_code")), ("transcript lines unreadable", tr.n_bad_lines or None))
            if val is not None],
        score=score)


# ------------------------------------------------------------------ index
def render_index(rows: list[dict], plan_id: str | None, scores_sha: str | None, split: str) -> str:
    head = ["run_id", "class", "condition", "model", "effort", "correct", "error", "cost_usd", "turns", "tool_calls",
            "flags"]
    table = []
    for r in rows:
        correct = r["correct"]
        ctext = {"True": "yes", "False": "no"}.get(str(correct), "" if correct is None else str(correct))
        cells = [{"text": r["run_id"], "sort": r["run_id"], "href": r["href"], "cls": ""}]
        for text, sort, cls in ((r["class"], None, ""), (r["condition"], None, ""), (r["model"], None, ""),
                                (r["effort"], None, ""),
                                (ctext, ctext, "ok" if ctext == "yes" else ("bad" if ctext == "no" else "")),
                                (r["error"], None, ""), (r["cost"], None, ""), (r["turns"], None, ""),
                                (r["tool_calls"], None, ""), (r["flags"], None, "")):
            cells.append({"text": _text(text), "sort": _text(text if sort is None else sort), "cls": cls, "href": None})
        table.append(cells)
    return page.render("views_index.html.j2", title="Run index", split=split, head=head, rows=table, n_rows=len(rows),
                      plan_id=plan_id, scores_sha=scores_sha)


# ------------------------------------------------------------------ driver
def render_dir(runs, split: str = "pilot") -> dict:
    """Write views/ and views/INDEX.html under `runs`. Returns {"n_views", "index"}."""
    runs = pathlib.Path(runs)
    plan = None
    try:
        plan = plan_mod.load_plan(runs / plan_mod.PLAN_NAME)
    except plan_mod.PlanError:
        plan = None
    records = {r["run_id"]: r for r in plan.runs} if plan and not plan.header["sealed"] else {}
    plan_id = plan.plan_id if plan else None
    scores, scores_sha = read_scores(runs)
    task_prompts: dict | None = None
    views = runs / "views"
    rows: list[dict] = []
    for path, model, cond, effort, task_id, k in find_transcripts(runs):
        rid = f"{model}/{cond}/{effort}/{task_id}-k{k}"
        rel = pathlib.PurePosixPath(*path.relative_to(runs).with_suffix(".html").parts)
        tr = read_transcript(path)
        meta = read_sidecar(path)
        record = records.get(rid)
        fallback_prompt = None
        if record is None:
            if task_prompts is None:
                from tsbench.tasks import load
                task_prompts = {t["id"]: t["prompt"] for t in load(split)}
            fallback_prompt = task_prompts.get(task_id)
        score_row = scores.get((model, cond, effort, task_id, str(k)))
        target = views / pathlib.Path(*rel.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_view(rid=rid, rel=rel, tr=tr, meta=meta, record=record, score_row=score_row,
                                      fallback_prompt=fallback_prompt,
                                      fallback_system=system_prompt_from_argv(meta, runs),
                                      plan_id=plan_id, raw_path=path), encoding="utf-8")
        res = tr.result or {}
        err = "no result" if tr.result is None else (res.get("subtype") if res.get("is_error") else "")
        rows.append(
            {
                "run_id": rid,
                "href": "/".join(urllib.parse.quote(p) for p in rel.parts),
                "class": (score_row or {}).get("class") or (record or {}).get("task_class") or "",
                "condition": cond,
                "model": model,
                "effort": effort,
                "correct": (score_row or {}).get("correct"),
                "error": err,
                "cost": res.get("total_cost_usd", ""),
                "turns": res.get("num_turns", ""),
                "tool_calls": sum(u["name"] != "StructuredOutput" for u in tr.tool_uses),
                "flags": ",".join(meta.get("flags") or []),
            }
        )
    views.mkdir(parents=True, exist_ok=True)
    index = views / "INDEX.html"
    index.write_text(render_index(rows, plan_id, scores_sha, run_split(runs, split)), encoding="utf-8")
    return {"n_views": len(rows), "index": index}


def render_overview(entries: list[tuple[RunSet, dict]], out_dir: pathlib.Path) -> str:
    """The overview page: one row per run set with its title, number of views and a relative link to its INDEX.html."""
    rows = [{"name": rs.name, "href": href(res["index"], out_dir), "title": rs.title, "n_views": res["n_views"]}
            for rs, res in entries]
    return page.render("views_overview.html.j2", title="Run sets", rows=rows)



def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tsbench report views", description=__doc__.splitlines()[0])
    ap.add_argument("--runs", action="append", required=True, metavar="DIR",
                    help="a run set, or a folder holding run sets (repeatable)")
    ap.add_argument("--out", default=None, metavar="FILE", help="also write an overview page of all run sets here")
    ap.add_argument("--split", default="pilot", choices=("pilot", "confirmatory"))
    ap.add_argument("--i-have-preregistered", dest="preregistered", metavar="DOI", default=None)
    a = ap.parse_args(argv)
    missing = [d for d in a.runs if not pathlib.Path(d).is_dir()]
    if missing:
        print(f"not a directory: {', '.join(missing)}", file=sys.stderr)
        return 2
    # a folder without any run set (no MANIFEST.json, no transcripts yet) still gets its (empty) index
    run_sets = [rs for d in map(pathlib.Path, a.runs) for rs in (run_sets_in([d]) or [RunSet(d.name, d.name, d)])]
    splits = {rs.name: run_split(rs.path, a.split) for rs in run_sets}
    if "confirmatory" in (*splits.values(), a.split) and not is_doi(a.preregistered):
        print("refusing to render the confirmatory split without --i-have-preregistered <DOI>", file=sys.stderr)
        return 2
    done = []
    for rs in run_sets:
        res = render_dir(rs.path, splits[rs.name])
        done.append((rs, res))
        print(f"{rs.name}: views written: {res['n_views']}  index: {res['index']}")
    if a.out:
        out = pathlib.Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_overview(done, out.parent), encoding="utf-8")
        print(f"overview: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
