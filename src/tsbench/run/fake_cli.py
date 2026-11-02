"""Stand-in for `claude -p` in dry runs and tests. Makes no network call, needs no key.

Same argv as the real call; the prompt arrives on stdin. It works out the condition from
the flags (`--mcp-config` -> C, `--tools Bash` -> B, else A) and writes stream-json lines
shaped like the real ones (see `fake_cli_fixtures/`).

Environment hooks (all optional):
    FAKE_SEED         part of the hash that decides whether the answer is correct
    FAKE_COST_USD     cost reported in the result event (default 0)
    FAKE_BAD_INIT=1   report a wrong model in the init event
    FAKE_NO_RESULT=1  stop before the result event
    FAKE_PROBE_LEAK   comma list of sandbox-probe markers that leak, e.g. IMPORT,NET,TSBIN: a must-fail marker then
                      prints rc=0; KEYENV / PATHS (must be 0) then print rc=1 (a key is visible / the inputs are lost)
    FAKE_PROBE_NO_STACK=1    the venv-B scientific stack does not import (PROBE_NUMPY rc=1)
    FAKE_PROBE_BASH_FAIL=1   Bash "does not run" in the probe (CTRL markers rc=1)
    FAKE_PROBE_ESCAPE=1      the probe tool_use asks for dangerouslyDisableSandbox
    FAKE_429_FIRST=N  the first N calls (counted in the file FAKE_429_STATE) end in an HTTP 429 result
    FAKE_429_TEXT     the text of those 429 results (default: a plain "API rate limit exceeded"); the gateway's
                      "... user daily request limit reached (N of N). Retry after S seconds." makes the runner
                      stop at once
    FAKE_STOP=error_max_turns|error_max_budget_usd   give the answer through StructuredOutput, then stop with that
                      subtype and a result event WITHOUT structured_output (a run stopped by a limit)

The task is identified by matching the prompt against the *pilot* split only. If nothing
matches the answer is generic unparseable text.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sys
import uuid

from tsbench.core.util import use_utf8_streams

FIXTURES = pathlib.Path(__file__).resolve().parent / "fake_cli_fixtures"
FAKE_VERSION = "fake-0"
RATE_LIMIT_TEXT = "API Error: Request rejected (429) \u00b7 API rate limit exceeded"
RATES = {"A": 0.40, "B": 0.60, "C": 0.90}
VALUE_OPTIONS = {
    "--model", "--tools", "--mcp-config", "--settings", "--allowedTools", "--system-prompt-file",
    "--max-turns", "--max-budget-usd", "--effort", "--output-format", "--json-schema",
}
LIST_OPTIONS = {"--disallowedTools"}  # variadic: every following argument up to the next flag


def parse_argv(argv: list[str]) -> dict:
    opts: dict[str, str] = {}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in VALUE_OPTIONS and i + 1 < len(argv):
            opts[a] = argv[i + 1]
            i += 2
        elif a in LIST_OPTIONS:
            j = i + 1
            while j < len(argv) and not argv[j].startswith("--"):
                j += 1
            opts[a] = " ".join(argv[i + 1:j])
            i = j
        else:
            i += 1
    return opts


def condition_of(opts: dict) -> str:
    if "--mcp-config" in opts:
        return "C"
    if opts.get("--tools") == "Bash":
        return "B"
    return "A"


def _digest(prompt: str, model: str, cond: str) -> bytes:
    seed = os.environ.get("FAKE_SEED", "")
    return hashlib.sha256((prompt + model + cond + seed).encode("utf-8")).digest()


def decide(prompt: str, model: str, cond: str) -> tuple[bool, bool]:
    """(answer is correct, answer carries no JSON line), deterministic."""
    d = _digest(prompt, model, cond)
    u = int.from_bytes(d[:8], "big") / 2**64
    no_json = int.from_bytes(d[8:12], "big") % 20 == 0
    return u < RATES[cond], no_json


def find_task(prompt: str) -> dict | None:
    from tsbench.tasks import load

    p = prompt.strip()
    pilot = load("pilot")
    for t in pilot:
        if t["prompt"].strip() == p:
            return t
    for t in pilot:
        if t["prompt"].strip() in p:
            return t
    return None


def schema_of(opts: dict) -> str | None:
    """The answer schema the call asked for, read from its `--json-schema` argument ("curve" if it asks for
    points, "batch" for values, "pairing" for nodes and edges, else "fit"); None without the flag. The fake follows
    the argv, not the task record, so that a runner which passes the wrong schema produces a wrong-shaped answer and
    a test can see it."""
    raw = opts.get("--json-schema")
    if raw is None:
        return None
    try:
        props = json.loads(raw).get("properties", {})
    except (ValueError, AttributeError):
        return "fit"
    for name, key in (("diagram", "image_path"), ("curve", "points"), ("batch", "values"), ("pairing", "nodes")):
        if key in props:
            return name
    return "fit"


def curve_answer_for(task: dict, correct: bool) -> dict:
    pts = task.get("reference_curve") or []
    scale = 1.0 if correct else 1.25
    return {"points": [{"dq_over_b": p["dq_over_b"], "term": p["term"], "e_over_b": round(p["e_over_b"] * scale, 4)}
                       for p in pts], "reason": "fake answer"}


def batch_answer_for(task: dict, correct: bool) -> dict:
    """One entry per reference item. A wrong answer is 10 % off on every second item (the tolerance is 2 %)."""
    items = (task.get("reference") or {}).get("values") or []
    out = []
    for i, it in enumerate(items):
        res = it["result"]
        if not correct and res is not None and i % 2 == 0:
            res = round(res * 1.10, 2)
        out.append({"input": it["input"], "result": res})
    return {"values": out, "reason": "fake answer"}


def pairing_answer_for(task: dict, correct: bool) -> dict:
    """The reference nodes and edges; a wrong answer drops the last edge and miscounts the first node."""
    ref = task.get("reference") or {}
    nodes = [dict(n) for n in ref.get("nodes") or []]
    edges = [dict(e) for e in ref.get("edges") or []]
    if not correct:
        edges = edges[:-1]
        if nodes:
            nodes[0]["count"] = nodes[0]["count"] + 1
    return {"nodes": nodes, "edges": edges, "reason": "fake answer"}


# a 1x1 PNG, written to the cwd by a diagram answer so that the runner's image harvest has something to find
TINY_PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
                         "0000000d4944415478da63f8ffff3f0005fe02fea7d6e5ab0000000049454e44ae426082")


def diagram_answer_for(task: dict, correct: bool) -> dict:
    """The reference levels; a wrong answer is 25 % too high in every level above the ground level. No image (null);
    `save_diagram_image` adds one."""
    ref = task.get("reference") or {}
    scale = 1.0 if correct else 1.25
    points = []
    for x, es, labs in zip(ref.get("grid") or [], ref.get("levels") or [], ref.get("labels") or [], strict=False):
        levels = [{"term": t, "e_over_b": round(e * scale, 4)} for e, t in zip(es, labs, strict=False)]
        points.append({"dq_over_b": x, "levels": levels})
    return {"points": points, "image_path": None, "image_sha256": None, "reason": "fake answer"}


def save_diagram_image(ans: dict) -> None:
    """Write diagram.png into the cwd (the runner's temp dir) and report its path and sha256 in `ans`, so that the image
    harvest and `image_sha_match` run end to end in a dry run."""
    path = pathlib.Path(os.getcwd()) / "diagram.png"
    try:
        path.write_bytes(TINY_PNG)
    except OSError:
        return
    ans["image_path"], ans["image_sha256"] = str(path), hashlib.sha256(TINY_PNG).hexdigest()


def answer_for(task: dict, correct: bool, schema: str | None = None) -> dict:
    if schema == "diagram":
        return diagram_answer_for(task, correct)
    if schema == "curve":
        return curve_answer_for(task, correct)
    if schema == "batch":
        return batch_answer_for(task, correct)
    if schema == "pairing":
        return pairing_answer_for(task, correct)
    if task.get("answer_schema", "fit") != "fit":
        # a fit-shaped answer to a curve/batch/pairing task: wrong by construction
        return {"Dq": None, "B": None, "C": None, "out_of_scope": False, "reason": "fake answer in the wrong schema"}
    ref = task["reference"]
    if task["expect_out_of_scope"]:
        if correct:
            return {"Dq": None, "B": None, "C": None, "out_of_scope": True, "reason": "outside the ligand-field model"}
        return {"Dq": 1000.0, "B": 700.0, "C": None, "out_of_scope": False, "reason": "fake wrong answer"}
    dq = ref["Dq"] if correct else round(ref["Dq"] * 1.15, 2)
    return {"Dq": dq, "B": ref["B"], "C": ref["C"] if "C" in task["required"] else None,
            "out_of_scope": False, "reason": "fake answer"}


def _new_uuid() -> str:
    return str(uuid.uuid4())


def emit(event: dict) -> None:
    try:
        sys.stdout.write(json.dumps(event) + "\n")
        sys.stdout.flush()
    except BrokenPipeError:  # the runner killed us (bad init, timeout)
        os._exit(0)


def assistant_event(session: str, content: list[dict]) -> dict:
    return {"type": "assistant", "session_id": session, "uuid": _new_uuid(),
            "message": {"id": "msg_" + _new_uuid()[:12], "type": "message", "role": "assistant", "content": content}}


def user_event(session: str, tool_use_id: str, text: str) -> dict:
    return {"type": "user", "session_id": session, "uuid": _new_uuid(),
            "message": {"role": "user",
                        "content": [{"type": "tool_result", "tool_use_id": tool_use_id, "content": text}]}}


PROBE_RE = re.compile(r"```(?:bash|sh)?\n(.*?)```", re.S)


def probe_markers(script: str) -> list[str]:
    """The markers a probe script prints, simulated (nothing is executed)."""
    leak = {m for m in os.environ.get("FAKE_PROBE_LEAK", "").split(",") if m}
    bash_fail = os.environ.get("FAKE_PROBE_BASH_FAIL") == "1"
    lines = []
    for name in re.findall(r"PROBE_([A-Z0-9]+)", script):
        if name == "NUMPY":  # the venv-B stack must be importable (FAKE_PROBE_NO_STACK=1: it is not)
            rc = 1 if os.environ.get("FAKE_PROBE_NO_STACK") == "1" or bash_fail else 0
        elif name.startswith("CTRL") or name == "HEREDOC":  # positive controls: must succeed
            rc = 1 if bash_fail else 0
        elif name in ("KEYENV", "PATHS"):  # must be 0; a "leak" is a visible key / lost probe inputs
            rc = 1 if name in leak or bash_fail else 0
        else:
            rc = 0 if name in leak else 1
        lines.append(f"PROBE_{name} rc={rc}")
    seen, out = set(), []
    for ln in lines:  # the script mentions each marker once in an echo, keep order, no duplicates
        if ln.split()[0] not in seen:
            seen.add(ln.split()[0])
            out.append(ln)
    return out


def _rate_limited_now() -> bool:
    """FAKE_429_FIRST=N: the first N calls that share the counter file FAKE_429_STATE answer with HTTP 429."""
    first = int(os.environ.get("FAKE_429_FIRST", "0") or 0)
    state = os.environ.get("FAKE_429_STATE")
    if first <= 0 or not state:
        return False
    path = pathlib.Path(state)
    n = int(path.read_text(encoding="utf-8") or 0) if path.exists() else 0
    path.write_text(str(n + 1), encoding="utf-8")
    return n < first


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    opts = parse_argv(argv)
    use_utf8_streams()  # the runner sends the prompt as UTF-8 bytes whatever the locale is
    prompt = sys.stdin.read()
    model = opts.get("--model", "claude-fake-0-0")
    cond = condition_of(opts)
    session = _new_uuid()
    cost = float(os.environ.get("FAKE_COST_USD", "0") or 0)

    tools: list[str] = []
    servers: list[dict] = []
    if cond == "B":
        tools = ["Bash"]
    elif cond == "C":
        blocked = set(opts.get("--disallowedTools", "").split())
        tools = [t for t in json.loads((FIXTURES / "init_C.json").read_text(encoding="utf-8"))["tools"]
            if t not in blocked]
        servers = [{"name": "tanabesugano", "status": "connected", "source": "dynamic"}]

    structured = "--json-schema" in opts
    if structured:
        tools = tools + ["StructuredOutput"]
    reported = "claude-fake-9-9" if os.environ.get("FAKE_BAD_INIT") == "1" else model
    # the real claude with a key set can emit this before init
    emit({"type": "system", "subtype": "ui_invalidate", "event": "ui.render", "uuid": _new_uuid(),
          "session_id": session})
    emit({"type": "system", "subtype": "init", "cwd": os.getcwd(), "session_id": session, "tools": tools,
          "mcp_servers": servers, "model": reported, "permissionMode": "default", "apiKeySource": "none",
          "claude_code_version": FAKE_VERSION, "uuid": _new_uuid()})

    final_text: str
    structured_answer: dict | None = None
    turns = 1
    m = PROBE_RE.search(prompt) if "PROBE_CTRL1" in prompt else None
    if m and cond == "B":
        script = m.group(1).strip()
        tuid = "toolu_" + _new_uuid()[:12]
        inp: dict = {"command": script, "description": "run the probe script"}
        if os.environ.get("FAKE_PROBE_ESCAPE") == "1":
            inp["dangerouslyDisableSandbox"] = True
        emit(assistant_event(session, [{"type": "tool_use", "id": tuid, "name": "Bash", "input": inp}]))
        emit(user_event(session, tuid, "\n".join(probe_markers(script))))
        final_text = "done"
        turns = 2
    else:
        task = find_task(prompt)
        if task is None:
            final_text = "I could not work this out; here is a prose answer without a parseable line."
        else:
            correct, no_json = decide(prompt, model, cond)
            schema = schema_of(opts)
            ans = answer_for(task, correct, schema)
            if schema == "diagram":
                save_diagram_image(ans)
            if schema == "diagram":
                summary = f"{len(ans['points'])} grid points with six levels each"
            elif schema == "curve":
                summary = f"{len(ans['points'])} points on the term diagram"
            elif schema == "batch":
                summary = f"{len(ans['values'])} results"
            elif schema == "pairing":
                summary = f"{len(ans['nodes'])} term nodes, {len(ans['edges'])} shared-term edges"
            else:
                summary = (f"Dq = {ans['Dq']} cm^-1, B = {ans['B']} cm^-1" if ans["Dq"] is not None
                           else "no reliable Dq/B within the model")
            if cond in ("B", "C"):
                tuid = "toolu_" + _new_uuid()[:12]
                if cond == "B":
                    block = {"type": "tool_use", "id": tuid, "name": "Bash",
                             "input": {"command": f"python3 -c \"print('{summary}')\"", "description": "compute"}}
                else:
                    block = {"type": "tool_use", "id": tuid, "name": "mcp__tanabesugano__ts_fit_spectrum",
                             "input": {"bands_cm1": task["bands_cm1"], "d_count": task["d_count"],
                                       "geometry": task["geometry"]}}
                    if schema in ("curve", "diagram"):
                        block["name"] = "mcp__tanabesugano__ts_terms_table_data"
                        block["input"] = {"d_count": task["d_count"]}
                    elif schema == "batch":
                        block["name"] = ("mcp__tanabesugano__ts_spin_crossover_app"
                                         if task.get("subtype") == "crossover_series"
                                         else "mcp__tanabesugano__ts_compute_app")
                        block["input"] = {"d_count": task["d_count"], **(task.get("params") or {})}
                    elif schema == "pairing":
                        block["name"] = "mcp__tanabesugano__ts_terms_table_data"
                        block["input"] = {"d_count": 5}
                emit(assistant_event(session, [block]))
                emit(user_event(session, tuid, summary))
                turns = 2
            final_text = f"Working it out: {summary}."
            if structured:
                if not no_json:  # the designed 1-in-20 failure: no structured_output, malformed text answer
                    suid = "toolu_" + _new_uuid()[:12]
                    emit(assistant_event(session, [{"type": "tool_use", "id": suid, "name": "StructuredOutput",
                                                    "input": ans}]))
                    emit(user_event(session, suid, "Structured output provided successfully"))
                    structured_answer = ans
                    final_text = json.dumps(ans)
                    turns += 1
            elif not no_json:
                final_text += "\n" + json.dumps(ans)
    emit(assistant_event(session, [{"type": "text", "text": final_text}]))

    if os.environ.get("FAKE_NO_RESULT") == "1":
        return 0
    if _rate_limited_now():
        emit({"type": "result", "subtype": "success", "is_error": True, "api_error_status": 429,
              "result": os.environ.get("FAKE_429_TEXT") or RATE_LIMIT_TEXT, "session_id": session,
              "total_cost_usd": 0, "num_turns": 1, "duration_ms": 1, "duration_api_ms": 0, "permission_denials": [],
              "terminal_reason": "api_error", "uuid": _new_uuid()})
        return 0
    stop = os.environ.get("FAKE_STOP")
    if stop in ("error_max_turns", "error_max_budget_usd"):
        emit({"type": "result", "subtype": stop, "is_error": True, "session_id": session, "total_cost_usd": cost,
              "num_turns": turns, "duration_ms": 1, "duration_api_ms": 0, "permission_denials": [],
              "terminal_reason": "max_turns" if stop == "error_max_turns" else "budget_exhausted",
              "errors": ["stopped by a limit"], "uuid": _new_uuid()})
        return 0
    result_event = ({"structured_output": structured_answer} if structured_answer is not None else {})
    emit({"type": "result", "subtype": "success", **result_event, "is_error": False, "result": final_text,
          "session_id": session, "total_cost_usd": cost, "num_turns": turns, "duration_ms": 1, "duration_api_ms": 0,
          "usage": {"input_tokens": 100, "output_tokens": 50, "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0},
          "permission_denials": [], "terminal_reason": "completed", "uuid": _new_uuid()})
    return 0


if __name__ == "__main__":
    from tsbench.core import trace

    trace.start_if_requested()  # off unless TSBENCH_TRACE names a folder
    raise SystemExit(main())
