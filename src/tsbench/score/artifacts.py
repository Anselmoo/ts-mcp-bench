"""Save the code the solver models wrote, next to the transcript.

    tsbench report artifacts --runs runs [--runs <dir> ...]

For every transcript (`<model>/<cond>/<effort>/<task>-k<i>.jsonl`, or a draw run's `transcript.jsonl`) this writes
`<task>-k<i>.code/` (`transcript.code/` for the latter) with

  NN_cmd.sh            the command string of every Bash tool_use, in order
  NN_<name>.py ...     every heredoc of such a command as its own file (`cat > x.py <<'EOF' ... EOF` -> x.py;
                       `python - <<'EOF'` -> inline_N.py)
  NN_mcp_<tool>.json   the input JSON of every MCP tool call (what was asked of the solver's tool)
  mcp_image_N.png      base64 images found in tool results
  calls.json           ordered list of {kind: bash|heredoc|mcp|image, name, path, sha256, exit, is_error,
                       result_excerpt, ...}

Nothing is ever executed. The call is idempotent: a `.code` dir whose calls.json is newer than the transcript is
left alone. A transcript without any Bash / MCP call and without images gets an empty calls.json only.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import pathlib
import re

from tsbench.score.extract import Transcript, is_progress_line, read_transcript

CALLS = "calls.json"
CACHE_BYTES = 512 * 1024 * 1024  # file size of the transcripts a `TranscriptCache` keeps parsed
EXCERPT = 400
_HEREDOC_RE = re.compile(r"<<(-?)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")
_REDIRECT_RE = re.compile(r"(?<![02-9&>])>>?\s*(['\"]?)([^\s'\"<>|;&]+)\1")  # stdout (>, 1>) only: not 2>, &>
_TEE_RE = re.compile(r"\btee\s+(?:-a\s+)?(['\"]?)([^\s'\"<>|;&]+)\1")
_QUOTED_OR_SEPARATOR = re.compile(r"""'[^']*'|"[^"]*"|(?P<sep>\|\||&&|\||;|(?<![>&])&(?!>))""")
_WRITER_RE = re.compile(r"\s*[({]*\s*(?:(?:then|do|else)\s+)?(?:\S*/)?(?P<name>cat|tee)\b")
_EXIT_RE = re.compile(r"(?:^|\n)\s*(?:Exit code|exit code|exit status|Exit status)[: ]+(-?\d+)")
_MIME_EXT = {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif", "image/webp": "webp",
             "image/svg+xml": "svg"}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def iter_events(path):
    """Yield the JSON objects of a stream-json transcript; broken lines (a run still writing) are skipped."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line or is_progress_line(line):
                continue
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if isinstance(ev, dict):
                yield ev


def _events_of(source):
    """The events of a transcript given as a path or as a parsed `Transcript` (whose events are the same lines)."""
    return source.events if isinstance(source, Transcript) else iter_events(source)


class TranscriptCache:
    """`read_transcript` with a memory, so that the readers of one report (the benchmark facts and the run gallery)
    parse a transcript once. Call it with a path. It keeps the parsed transcripts of at most `max_bytes` of file size,
    the oldest read first out, and reads a file again when its size or timestamp has changed. The budget is file size
    (`CACHE_BYTES`, 512 MiB): a set of transcripts larger than that is still read correctly, but the transcripts that
    were pushed out are parsed again by the next reader."""

    def __init__(self, max_bytes: int = CACHE_BYTES):
        self.max_bytes = max_bytes
        self._kept: dict[str, tuple[tuple[int, int], Transcript]] = {}
        self._size = 0

    def __call__(self, path) -> Transcript:
        p = pathlib.Path(path)
        key = str(p.resolve())
        st = p.stat()
        stamp = (st.st_mtime_ns, st.st_size)
        hit = self._kept.get(key)
        if hit is not None and hit[0] == stamp:
            return hit[1]
        self._drop(key)
        tr = read_transcript(p)
        if st.st_size <= self.max_bytes:
            while self._kept and self._size + st.st_size > self.max_bytes:
                self._drop(next(iter(self._kept)))
            self._kept[key] = (stamp, tr)
            self._size += st.st_size
        return tr

    def _drop(self, key: str) -> None:
        old = self._kept.pop(key, None)
        if old is not None:
            self._size -= old[0][1]


def code_dir_of(transcript) -> pathlib.Path:
    t = pathlib.Path(transcript)
    return (t.with_name(t.name[: -len(".jsonl")] + ".code") if t.name.endswith(".jsonl")
            else t.with_name(t.name + ".code"))


def _commands_of_line(line: str) -> list[tuple[int, int, str]]:
    """The commands of one shell line as (start, end, the separator after it); a quoted separator does not count."""
    out, start = [], 0
    for m in _QUOTED_OR_SEPARATOR.finditer(line):
        if m.group("sep"):
            out.append((start, m.start(), m.group("sep")))
            start = m.end()
    return [*out, (start, len(line), "")]


def _heredoc_target(line: str, at: int) -> str | None:
    """The file the heredoc that starts at offset `at` of the line is written to: a stdout redirect or a tee of its own
    `cat` or `tee` command, or the tee that command pipes into. A redirect of another command on the line is not one."""
    commands = _commands_of_line(line)
    i = next(i for i, (_, end, _) in enumerate(commands) if at < end)
    start, end, sep = commands[i]
    own = line[start:end]
    if not _WRITER_RE.match(own):
        return None
    m = _REDIRECT_RE.search(own) or _TEE_RE.search(own)  # never a target that starts with & (>&2 is a stream)
    if m is None and sep == "|":
        following = line[commands[i + 1][0]:commands[i + 1][1]]
        writer = _WRITER_RE.match(following)
        m = _TEE_RE.search(following) if writer and writer["name"] == "tee" else None
    return m.group(2) if m else None


def split_heredocs(command: str) -> tuple[list[dict], str]:
    """Split the heredocs out of a shell command.

    Returns ([{name, body, lines}], skeleton): `name` is the file the heredoc is redirected to (cat > x.py <<'EOF',
    cat <<'EOF' > x.py, tee x.py <<EOF, cat <<EOF | tee x.py) or None; `skeleton` is the command with every body
    replaced by a one-line marker. A heredoc without its terminator takes the rest of the command."""
    lines = command.split("\n")
    out: list[dict] = []
    skel: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        skel.append(line)
        i += 1
        found = list(_HEREDOC_RE.finditer(line))
        if not found:
            continue
        pending = [(m.group(1) == "-", m.group(3)) for m in found]
        target = _heredoc_target(line, found[0].start())
        first_python = bool(re.search(r"\bpython[0-9.]*\b", line))
        for strip_tabs, delim in pending:
            body: list[str] = []
            while i < len(lines):
                cur = lines[i]
                i += 1
                if (cur.lstrip("\t") if strip_tabs else cur).rstrip() == delim:
                    break
                body.append(cur)
            name = target if len(pending) == 1 else None
            out.append({"name": name, "body": "\n".join(body) + "\n", "lines": len(body),
                        "python": first_python and name is None})
            skel.append(f"... [heredoc {delim}: {len(body)} lines, see file] ...")
            skel.append(delim)
    return out, "\n".join(skel)


def _safe_name(name: str | None, fallback: str) -> str:
    base = (name or "").replace("\\", "/").rsplit("/", 1)[-1]
    base = re.sub(r"[^\w.\-]+", "_", base).strip("._")
    return base[:60] or fallback


def _result_text(content) -> str:
    if isinstance(content, str):
        return content
    parts = []
    if isinstance(content, list):
        for b in content:
            if isinstance(b, dict):
                if b.get("type") == "text":
                    parts.append(str(b.get("text", "")))
                elif b.get("type") == "image":
                    parts.append("[image]")
            elif isinstance(b, str):
                parts.append(b)
    return "\n".join(parts)


def scan_tool_calls(transcript) -> tuple[list[dict], dict[str, dict]]:
    """Ordered tool_use blocks (deduplicated by id) and the tool_result per tool_use_id.

    `transcript` is a path or a parsed `Transcript`; the latter is not read from disk again."""
    uses: list[dict] = []
    seen: set[str] = set()
    results: dict[str, dict] = {}
    for ev in _events_of(transcript):
        msg = ev.get("message")
        content = msg.get("content") if isinstance(msg, dict) else None
        if not isinstance(content, list):
            continue
        for b in content:
            if not isinstance(b, dict):
                continue
            if ev.get("type") == "assistant" and b.get("type") == "tool_use":
                uid = b.get("id")
                if isinstance(uid, str) and uid:  # a repeated event is one call; no usable id: never merged
                    if uid in seen:
                        continue
                    seen.add(uid)
                uses.append(b)
            elif ev.get("type") == "user" and b.get("type") == "tool_result":
                rid = b.get("tool_use_id")
                if isinstance(rid, str):  # a list or dict id belongs to no call
                    results[rid] = b
    return uses, results


def result_of(results: dict[str, dict], use: dict) -> dict | None:
    """The tool_result of a tool_use block; None when it has no usable (string) id or no result."""
    uid = use.get("id")
    return results.get(uid) if isinstance(uid, str) else None


def answer_texts(transcript) -> list[str]:
    """Texts of the final answer: assistant text blocks and the `result` string (for inline <svg> search).

    `transcript` is a path or a parsed `Transcript`."""
    texts: list[str] = []
    for ev in _events_of(transcript):
        if ev.get("type") == "result" and isinstance(ev.get("result"), str):
            texts.append(ev["result"])
        msg = ev.get("message")
        if ev.get("type") == "assistant" and isinstance(msg, dict) and isinstance(msg.get("content"), list):
            texts += [b["text"] for b in msg["content"]
                      if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str)]
    return texts


def _fresh(code_dir: pathlib.Path, transcript: pathlib.Path) -> bool:
    calls = code_dir / CALLS
    try:
        return calls.stat().st_mtime_ns >= pathlib.Path(transcript).stat().st_mtime_ns
    except OSError:
        return False


def _write_if_changed(path: pathlib.Path, data: bytes) -> None:
    try:
        if path.read_bytes() == data:
            return
    except OSError:
        pass
    path.write_bytes(data)


def extract_code(transcript_path, write: bool = True, tr: Transcript | None = None) -> list[dict]:
    """Extract Bash commands, heredoc files, MCP calls and MCP images of one transcript.

    Returns the ordered `calls.json` list. With write=True the files go to `<stem>.code/` (idempotent, see module
    docstring); with write=False nothing touches the disk. `tr` is the already parsed transcript of that path; with
    it the file is not read again. Never executes anything."""
    transcript = pathlib.Path(transcript_path)
    code_dir = code_dir_of(transcript)
    if write and _fresh(code_dir, transcript):
        try:
            cached = json.loads((code_dir / CALLS).read_text(encoding="utf-8"))
            if isinstance(cached, list):
                return cached
        except (OSError, ValueError):
            pass
    uses, results = scan_tool_calls(tr if tr is not None else transcript)
    entries: list[dict] = []
    files: dict[str, bytes] = {}
    n = 0
    img_n = 0

    def add_file(name: str, data: bytes) -> str:
        files[name] = data
        return name

    for use in uses:
        tname = str(use.get("name") or "")
        inp = use.get("input") if isinstance(use.get("input"), dict) else {}
        res = result_of(results, use) or {}
        is_error = bool(res.get("is_error"))
        text = _result_text(res.get("content"))
        excerpt = text.strip()[:EXCERPT]
        m = _EXIT_RE.search(text)
        exit_code = int(m.group(1)) if m else (1 if is_error else (0 if res else None))
        # images in the result, whatever tool made them
        if isinstance(res.get("content"), list):
            for b in res["content"]:
                if isinstance(b, dict) and b.get("type") == "image" and isinstance(b.get("source"), dict):
                    src = b["source"]
                    try:
                        data = base64.b64decode(src.get("data") or "", validate=False)
                    except (binascii.Error, ValueError):
                        continue
                    if not data:
                        continue
                    img_n += 1
                    mime = src.get("media_type") or "image/png"
                    fname = f"mcp_image_{img_n}.{_MIME_EXT.get(mime, 'bin')}"
                    add_file(fname, data)
                    entries.append({"kind": "image", "name": fname, "path": fname, "sha256": _sha(data),
                                    "media_type": mime, "tool": tname, "bytes": len(data), "is_error": False,
                                    "exit": None, "result_excerpt": ""})
        if tname == "Bash":
            cmd = str(inp.get("command") or "")
            if not cmd:
                continue
            heredocs, skeleton = split_heredocs(cmd)
            fn = add_file(f"{n:02d}_cmd.sh", cmd.encode("utf-8"))
            entries.append({"kind": "bash", "name": "cmd.sh", "path": fn, "sha256": _sha(cmd.encode("utf-8")),
                            "call": n, "exit": exit_code, "is_error": is_error, "result_excerpt": excerpt,
                            "skeleton": skeleton, "description": str(inp.get("description") or "")[:200]})
            n += 1
            for j, h in enumerate(heredocs, 1):
                fallback = f"inline_{j}.py" if h["python"] else f"heredoc_{j}.txt"
                hname = _safe_name(h["name"], fallback)
                fn = add_file(f"{n:02d}_{hname}", h["body"].encode("utf-8"))
                entries.append({"kind": "heredoc", "name": hname, "path": fn, "sha256": _sha(h["body"].encode("utf-8")),
                                "call": n - 1, "target": h["name"], "lines": h["lines"], "exit": exit_code,
                                "is_error": is_error, "result_excerpt": excerpt})
                n += 1
        elif tname.startswith("mcp__"):
            short = _safe_name(tname.split("__", 2)[-1], "tool")
            body = (json.dumps(inp, indent=1, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
            fn = add_file(f"{n:02d}_mcp_{short}.json", body)
            entries.append({"kind": "mcp", "name": tname, "path": fn, "sha256": _sha(body), "call": n,
                            "exit": exit_code, "is_error": is_error, "result_excerpt": excerpt})
            n += 1
    if write:  # no entries: an empty calls.json is still the stamp that the transcript was read
        code_dir.mkdir(parents=True, exist_ok=True)
        for stale in code_dir.iterdir():  # leftovers of an earlier numbering of this very dir
            if stale.is_file() and not stale.is_symlink() and stale.name not in files and stale.name != CALLS:
                stale.unlink()
        for name, data in files.items():
            _write_if_changed(code_dir / name, data)
        # calls.json is written last: its mtime is the "up to date" stamp
        (code_dir / CALLS).write_text(json.dumps(entries, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return entries


def find_transcripts(root) -> list[pathlib.Path]:
    """`<task>-k<i>.jsonl` and draw `transcript.jsonl` below `root` (sandbox probes and views are skipped)."""
    out = []
    for p in sorted(pathlib.Path(root).rglob("*.jsonl")):
        parts = set(p.parts)
        if "_sandbox_probe" in parts or "views" in parts or p.name.startswith("plan"):
            continue
        if p.name == "transcript.jsonl" or re.search(r"-k\d+\.jsonl$", p.name):
            out.append(p)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs", action="append", required=True, help="run directory (repeatable)")
    args = ap.parse_args(argv)
    n_runs = n_code = n_files = n_img = 0
    for root in args.runs:
        for t in find_transcripts(root):
            calls = extract_code(t)
            if calls:
                n_runs += 1
                n_code += sum(c["kind"] in ("bash", "heredoc", "mcp") for c in calls)
                n_img += sum(c["kind"] == "image" for c in calls)
                n_files += len(calls)
    print(f"runs with code: {n_runs}, code entries: {n_code}, images: {n_img}, files: {n_files}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
