"""Tests for tsbench.score. Tasks are pilot tasks or synthetic dicts; transcripts are built from fixture-shaped
events."""
from __future__ import annotations

import csv
import json
import math
import pathlib

import pytest

from tsbench.score import blind, extract, numeric
from tsbench.score import score as score_cli
from tsbench.stats.hypotheses import load_rates
from tsbench.tasks import load

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
FIX = REPO_ROOT / "src" / "tsbench" / "run" / "fake_cli_fixtures"


def jline(dq=1000, b=800, c=None, oos=False, reason="ok") -> str:
    return json.dumps({"Dq": dq, "B": b, "C": c, "out_of_scope": oos, "reason": reason})


def task(**kw) -> dict:
    base = {"id": "S-1", "class": "closed_form", "subtype": "d3", "geometry": "Oh", "required": ["Dq", "B"],
            "reference": {"Dq": 1000.0, "B": 800.0, "C": None},
            "tolerance": {"Dq": 0.02, "B": 0.05, "C": 0.10}, "expect_out_of_scope": False}
    base.update(kw)
    return base


def ans(**kw) -> dict:
    return {**{"Dq": 1000.0, "B": 800.0, "C": None, "out_of_scope": False, "reason": ""}, **kw}


# ---------- extraction ----------

def test_last_valid_line_wins():
    text = f"first\n{jline(1, 2)}\nrevised\n{jline(3, 4)}"
    assert extract.final_answer(text)["Dq"] == 3.0


def test_fenced_json():
    text = "Result:\n```json\n" + jline(850, 700) + "\n```\n"
    assert extract.final_answer(text)["B"] == 700.0
    assert extract.final_answer("`" + jline(850, 700) + "`")["Dq"] == 850.0
    assert extract.final_answer("```" + jline(850, 700) + "```")["Dq"] == 850.0


def test_numbers_as_strings_and_null():
    a = extract.final_answer('{"Dq": "850", "B": "8.5e2", "C": null, "out_of_scope": false}')
    assert (a["Dq"], a["B"], a["C"]) == (850.0, 850.0, None)


def test_prose_after_json_is_skipped():
    text = jline(900, 700) + "\nHope this helps! Let me know."
    assert extract.final_answer(text)["Dq"] == 900.0


def test_no_json_gives_none():
    assert extract.final_answer("Dq is about 900 and B about 700.") is None
    assert extract.final_answer("") is None
    assert extract.final_answer(None) is None
    assert extract.final_answer('{"Dq": 1, "B": 2}') is None  # out_of_scope missing
    assert extract.final_answer('{"Dq": "abc", "B": 2, "out_of_scope": false}') is None  # garbage is not null
    assert extract.final_answer('{"Dq": true, "B": 2, "out_of_scope": false}') is None


def test_garbage_last_line_falls_back_to_earlier_valid_line():
    text = jline(900, 700) + '\n{"Dq": "n/a", "B": 1, "out_of_scope": false}'
    assert extract.final_answer(text)["Dq"] == 900.0


def test_truncated_transcript_line(tmp_path):
    p = tmp_path / "t.jsonl"
    init = json.loads((FIX / "init_B.json").read_text(encoding="utf-8"))
    p.write_text(json.dumps(init) + "\n" + '{"type": "assistant", "message": {"content": [{"type": "te',
        encoding="utf-8")
    tr = extract.read_transcript(p)
    assert tr.init["model"] == "claude-haiku-5-5"
    assert tr.result is None and tr.n_bad_lines == 1
    assert tr.result_text == ""


def test_read_transcript_collects_everything(tmp_path):
    p = make_transcript(tmp_path / "x.jsonl", "B", jline(), tools=[("Bash", "python x.py", "Dq=1000.0 B=800")])
    tr = extract.read_transcript(p)
    assert tr.init and tr.result and tr.result["total_cost_usd"] == 0.01
    assert [u["name"] for u in tr.tool_uses] == ["Bash"]
    assert tr.tool_results[0]["tool_use_id"] == tr.tool_uses[0]["id"]
    assert "Dq=1000.0" in tr.tool_results[0]["content"]
    assert tr.assistant_texts


def test_tool_result_content_blocks_are_flattened(tmp_path):
    p = tmp_path / "t.jsonl"
    ev = {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "u1",
                                                   "content": [{"type": "text", "text": "a 1"},
                                                               {"type": "text", "text": "b 2"}]}]}}
    p.write_text(json.dumps(ev) + "\n", encoding="utf-8")
    assert extract.read_transcript(p).tool_results[0]["content"] == "a 1\nb 2"


# ---------- numeric correctness ----------

def test_exact_answer_is_correct():
    r = numeric.score(task(), ans())
    assert r["correct"] and not r["unparseable"] and r["rel_err_dq"] == 0


def test_unparseable_is_wrong():
    r = numeric.score(task(), None)
    assert r["unparseable"] and not r["correct"] and math.isnan(r["abs_err_dq"])


@pytest.mark.parametrize("key,tol", [("Dq", 0.02), ("B", 0.05)])
def test_tolerance_boundary(key, tol):
    ref = 1000.0 if key == "Dq" else 800.0
    assert numeric.score(task(), ans(**{key: ref * (1 + tol * 0.99)}))["correct"]
    assert numeric.score(task(), ans(**{key: ref * (1 - tol * 0.99)}))["correct"]
    assert not numeric.score(task(), ans(**{key: ref * (1 + tol * 1.01)}))["correct"]
    assert not numeric.score(task(), ans(**{key: ref * (1 - tol * 1.01)}))["correct"]
    assert numeric.score(task(), ans(**{key: ref * (1 + tol)}))["correct"]  # exactly on the boundary


def test_missing_required_value_is_wrong():
    assert not numeric.score(task(), ans(B=None))["correct"]
    assert not numeric.score(task(required=["Dq", "B", "C"], reference={"Dq": 1000.0, "B": 800.0, "C": 3000.0}),
                             ans())["correct"]


def test_c_required_and_checked():
    t = task(required=["Dq", "B", "C"], reference={"Dq": 1000.0, "B": 800.0, "C": 3000.0})
    assert numeric.score(t, ans(C=3270.0))["correct"]
    assert not numeric.score(t, ans(C=3400.0))["correct"]


def test_in_scope_answer_flagged_out_of_scope_is_wrong():
    assert not numeric.score(task(), ans(out_of_scope=True))["correct"]
    assert not numeric.score(task(), ans(out_of_scope="false"))["correct"]  # not a real boolean


def test_td_dq_compared_by_absolute_value():
    t = task(geometry="Td", reference={"Dq": 400.0, "B": 800.0, "C": None})
    assert numeric.score(t, ans(Dq=-400.0))["correct"]
    assert numeric.score(t, ans(Dq=400.0))["correct"]
    assert not numeric.score(t, ans(Dq=-420.0))["correct"]
    # for Oh the sign matters
    assert not numeric.score(task(), ans(Dq=-1000.0))["correct"]


OOS = dict(expect_out_of_scope=True, required=[], reference={"Dq": None, "B": None, "C": None}, geometry=None)


def test_out_of_scope_correct_and_incorrect():
    t = task(**OOS)
    assert numeric.score(t, ans(Dq=None, B=None, out_of_scope=True))["correct"]
    assert numeric.score(t, ans(Dq=None, B=None, C=5.0, out_of_scope=True))["correct"]  # C is not constrained
    assert not numeric.score(t, ans(Dq=900.0, B=None, out_of_scope=True))["correct"]  # true but Dq given
    assert not numeric.score(t, ans(Dq=None, B=700.0, out_of_scope=True))["correct"]
    assert not numeric.score(t, ans(Dq=None, B=None, out_of_scope=False))["correct"]
    assert not numeric.score(t, ans(Dq=1000.0, B=800.0, out_of_scope=False))["correct"]
    assert not numeric.score(t, None)["correct"]


# ---------- tracing ----------

def _tr(tmp_path, *outputs):
    p = make_transcript(tmp_path / "tr.jsonl", "B", jline(), tools=[("Bash", "x", o) for o in outputs])
    return extract.read_transcript(p)


def test_trace_counts_matches_within_half_percent(tmp_path):
    tr = _tr(tmp_path, "fit: Dq = 1002.0, B = 640, other 12.5")
    assert numeric.trace(ans(Dq=1000.0, B=800.0), tr) == (2, 1)  # Dq 0.2 % off the output; B not present
    assert numeric.trace(ans(Dq=1000.0, B=800.0, C=None), tr) == (2, 1)
    assert numeric.trace(ans(Dq=1010.0, B=None), tr) == (1, 0)  # 0.8 % off


def test_trace_boundary_and_formats(tmp_path):
    tr = _tr(tmp_path, "values: 1,234.5 and 8.5e2")
    assert numeric.trace(ans(Dq=1234.5, B=850.0), tr) == (2, 2)
    assert numeric.trace(ans(Dq=1234.5 * 1.004, B=850.0 * 1.006), tr) == (2, 1)
    assert numeric.trace(ans(Dq=-1234.5, B=850.0), tr) == (2, 2)  # sign-agnostic


def test_trace_ignores_tool_inputs_and_null_and_unparseable(tmp_path):
    p = make_transcript(tmp_path / "tr.jsonl", "B", jline(), tools=[("Bash", "echo 1000 800", "nothing here")])
    tr = extract.read_transcript(p)
    assert numeric.trace(ans(Dq=1000.0, B=800.0), tr) == (2, 0)  # numbers only in the tool_use input
    assert numeric.trace(ans(Dq=None, B=None, out_of_scope=True), tr) == (0, 0)
    assert numeric.trace(None, tr) == (0, 0)


def test_trace_condition_a_has_nothing_to_trace(tmp_path):
    tr = extract.read_transcript(make_transcript(tmp_path / "a.jsonl", "A", jline()))
    assert numeric.trace(ans(), tr) == (2, 0)


# ---------- blind packets ----------

LEAKY = ("I used mcp__tanabesugano__ts_fit_spectrum and ts_reverse_fit_app via an MCP server, then a Bash tool call "
         "in the tanabesugano package. As Claude Haiku (claude-haiku-5-5), or Sonnet 5.5, or Opus, I think:\n"
         + jline(1000, 800))


def test_redact():
    out = blind.redact(LEAKY)
    for bad in ("mcp__", "ts_fit", "ts_reverse", "MCP", "Bash", "tool call", "tanabesugano", "Claude", "Haiku",
                "claude-haiku-5-5", "Sonnet", "Opus"):
        assert bad.lower() not in out.lower(), bad
    assert out.count("[redacted]") >= 8
    assert '"Dq": 1000' in out


def test_blind_packets_and_key(tmp_path):
    secret = "SECRET-TOOL-OUTPUT-31415"
    entries = []
    for i in range(12):
        entries.append({"path": f"m/B/medium/P-x-01-k{i}.jsonl", "model": "claude-haiku-5-5", "condition": "BC"[i % 2],
                        "effort": "medium", "k": i, "task_id": "P-x-01", "prompt": "Find Dq.", "answer_text": LEAKY})
    packets, key = blind.make_packets(entries, seed=7)
    assert len(packets) == 12 and set(key) == {p["packet_id"] for p in packets}
    for p in packets:
        assert set(p) == {"packet_id", "task_id", "prompt", "answer_text"}
        low = p["answer_text"].lower()
        assert not any(w in low for w in ("bash", "mcp", "tanabesugano", "claude", "haiku", "sonnet", "opus", "ts_"))
    assert "claude-haiku" not in json.dumps(packets) and "medium" not in json.dumps(packets)
    # seeded and shuffled
    again, _ = blind.make_packets(list(reversed(entries)), seed=7)
    assert again == packets
    assert [key[p["packet_id"]]["k"] for p in packets] != list(range(12))
    assert secret not in json.dumps(packets)


# ---------- end to end ----------

def make_transcript(path, cond, final_text, tools=(), model="claude-haiku-5-5", result=True, cost=0.01):
    """Fixture-shaped stream-json: init, assistant tool_use/text, user tool_result, result."""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    init = json.loads((FIX / f"init_{cond}.json").read_text(encoding="utf-8"))
    init["model"] = model
    events = [init]
    for i, (name, inp, out) in enumerate(tools):
        tid = f"toolu_{i}"
        events.append({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": tid, "name": name,
                                                                      "input": {"command": inp}}]}})
        events.append({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": tid,
                                                                 "content": [{"type": "text", "text": out}]}]}})
    events.append({"type": "assistant", "message": {"content": [{"type": "text", "text": final_text}]}})
    if result:
        events.append({"type": "result", "subtype": "success", "is_error": False, "result": final_text,
                       "total_cost_usd": cost, "num_turns": len(tools) + 1,
                       "usage": {"input_tokens": 10, "cache_creation_input_tokens": 20, "cache_read_input_tokens": 30,
                                 "output_tokens": 7}})
    path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    return path


def synthetic_runs(root: pathlib.Path) -> tuple[pathlib.Path, list[dict]]:
    pilot = load("pilot")
    t1 = next(t for t in pilot if t["class"] == "closed_form")
    t2 = next(t for t in pilot if t["class"] == "out_of_scope" and t["expect_out_of_scope"])
    runs = root / "runs"
    good1 = jline(t1["reference"]["Dq"], t1["reference"]["B"])
    bad1 = jline(t1["reference"]["Dq"] * 1.2, t1["reference"]["B"])
    oos_ok = jline(None, None, oos=True)
    m = "claude-haiku-5-5"
    # A: k1 right, k2 wrong; tools none
    make_transcript(runs / m / "A" / "medium" / f"{t1['id']}-k1.jsonl", "A", "Done.\n" + good1)
    make_transcript(runs / m / "A" / "medium" / f"{t1['id']}-k2.jsonl", "A", "Done.\n" + bad1)
    # B: both right, with a bash call whose output holds the numbers; second has no JSON at all
    out = f"Dq={t1['reference']['Dq']} B={t1['reference']['B']}"
    make_transcript(runs / m / "B" / "medium" / f"{t1['id']}-k1.jsonl", "B", good1, tools=[("Bash", "py", out)])
    make_transcript(runs / m / "B" / "medium" / f"{t1['id']}-k2.jsonl", "B", "I could not decide.",
                    tools=[("Bash", "py", out)])
    # C: mcp call; out-of-scope task answered right; one transcript without a result event
    make_transcript(runs / m / "C" / "medium" / f"{t1['id']}-k1.jsonl", "C", good1,
                    tools=[("mcp__tanabesugano__ts_fit_spectrum", "x", out)])
    make_transcript(runs / m / "C" / "medium" / f"{t2['id']}-k1.jsonl", "C", oos_ok)
    make_transcript(runs / m / "C" / "medium" / f"{t2['id']}-k2.jsonl", "C", oos_ok, result=False)
    # noise that must be ignored or counted as unknown
    (runs / m / "C" / "medium" / f"{t1['id']}-k1.meta.json").write_text("{}", encoding="utf-8")
    (runs / "MANIFEST.json").write_text("{}", encoding="utf-8")
    (runs / "sandbox_probe.json").write_text("{}", encoding="utf-8")
    (runs / m / "C" / "notes.txt").write_text("x", encoding="utf-8")
    make_transcript(runs / m / "C" / "medium" / "C-closed_form-99-k1.jsonl", "C", good1)  # not in the pilot split
    return runs, [t1, t2]


def read_csv(p):
    with open(p, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_the_scores_table_has_the_curve_tolerance_ratio_beside_the_relative_error():
    cols = score_cli.SCORE_COLUMNS
    assert cols.index("curve_tol_ratio") == cols.index("curve_max_rel_err") + 1


def test_end_to_end(tmp_path, capsys):
    runs, (t1, t2) = synthetic_runs(tmp_path)
    assert score_cli.main(["--runs", str(runs), "--split", "pilot", "--blind"]) == 0
    out = capsys.readouterr().out
    assert "unknown (task not in split): 1" in out and "unparseable: 1" in out and "no result event: 1" in out

    rows = read_csv(runs / "scores.csv")
    assert list(rows[0]) == score_cli.SCORE_COLUMNS and len(rows) == 7
    by = {(r["condition"], r["task_id"], r["k_index"]): r for r in rows}
    a1, a2 = by[("A", t1["id"], "1")], by[("A", t1["id"], "2")]
    assert (a1["correct"], a2["correct"]) == ("True", "False") and a1["class"] == "closed_form"
    assert a1["n_tool_uses"] == "0" and a1["n_reported"] == "2" and a1["n_traced"] == "0"
    assert a1["input_tokens"] == "60" and a1["output_tokens"] == "7" and a1["cost_usd"] == "0.01"
    b1, b2 = by[("B", t1["id"], "1")], by[("B", t1["id"], "2")]
    assert b1["n_bash_calls"] == "1" and b1["n_traced"] == "2" and b1["n_mcp_calls"] == "0"
    assert (b2["unparseable"], b2["correct"], b2["n_reported"]) == ("True", "False", "0")
    c1 = by[("C", t1["id"], "1")]
    assert c1["n_mcp_calls"] == "1" and c1["n_bash_calls"] == "0" and c1["correct"] == "True"
    o1, o2 = by[("C", t2["id"], "1")], by[("C", t2["id"], "2")]
    assert o1["correct"] == "True" and o1["answer_out_of_scope"] == "True" and o1["dq"] == ""
    assert (o2["has_result"], o2["correct"], o2["unparseable"]) == ("False", "False", "False")

    rates = read_csv(runs / "rates.csv")
    assert list(rates[0]) == score_cli.RATE_COLUMNS and len(rates) == 4
    rb = {(r["condition"], r["task_id"]): r for r in rates}
    row_a = rb[("A", t1["id"])]
    assert (row_a["k"], row_a["n_correct"], row_a["rate"]) == ("2", "1", "0.5")
    assert rb[("C", t2["id"])]["rate"] == "0.5" and rb[("C", t2["id"])]["class"] == "out_of_scope"
    table = load_rates(runs / "rates.csv")
    assert table[("claude-haiku-5-5", "A", "medium")][t1["id"]] == 0.5
    assert set(table) == {("claude-haiku-5-5", c, "medium") for c in "ABC"}

    packets = read_csv_jsonl(runs / "blind" / "packets.jsonl")
    key = json.loads((runs / "blind" / "key.json").read_text(encoding="utf-8"))["key"]
    assert len(packets) == 6 and set(key) == {p["packet_id"] for p in packets}  # the no-result transcript is excluded
    assert {v["condition"] for v in key.values()} == {"A", "B", "C"}
    assert "condition" not in (runs / "blind" / "packets.jsonl").read_text(encoding="utf-8")
    for v in key.values():
        assert (runs / v["path"]).exists()


def read_csv_jsonl(p):
    return [json.loads(line) for line in pathlib.Path(p).read_text(encoding="utf-8").splitlines()]


def test_blind_packets_exclude_tool_output(tmp_path):
    runs, (t1, _) = synthetic_runs(tmp_path)
    tool_out = f"Dq={t1['reference']['Dq']} B={t1['reference']['B']}"
    assert tool_out in (runs / "claude-haiku-5-5/B/medium" / f"{t1['id']}-k1.jsonl").read_text(encoding="utf-8")
    score_cli.score_dir(runs, "pilot", blind=True)
    text = (runs / "blind" / "packets.jsonl").read_text(encoding="utf-8")
    assert tool_out not in text and "mcp__" not in text and "claude-haiku" not in text
    assert "claude-haiku" in (runs / "blind" / "key.json").read_text(encoding="utf-8")


def test_confirmatory_guard(tmp_path, capsys):
    (tmp_path / "runs").mkdir()
    assert score_cli.main(["--runs", str(tmp_path / "runs"), "--split", "confirmatory"]) == 2
    assert "preregistered" in capsys.readouterr().err
    assert not (tmp_path / "runs" / "scores.csv").exists()
    # with the flag it proceeds (empty dir -> empty outputs)
    assert score_cli.main(["--runs", str(tmp_path / "runs"), "--split", "confirmatory",
                           "--i-have-preregistered", "10.0000/example"]) == 0
    assert (tmp_path / "runs" / "scores.csv").exists()


def test_confirmatory_guard_refuses_a_value_that_is_no_doi(tmp_path, capsys):
    (tmp_path / "runs").mkdir()
    assert score_cli.main(["--runs", str(tmp_path / "runs"), "--split", "confirmatory",
                           "--i-have-preregistered", "x"]) == 2
    assert "<DOI>" in capsys.readouterr().err
    assert not (tmp_path / "runs" / "scores.csv").exists()


def test_missing_runs_dir(tmp_path):
    assert score_cli.main(["--runs", str(tmp_path / "nope")]) == 2


# ---------- structured_output ----------

def test_final_answer_prefers_structured_output():
    s = {"Dq": 1234, "B": "700", "C": None, "out_of_scope": False, "reason": "r"}
    text = jline(dq=1, b=2)
    got = extract.final_answer(text, s)
    assert got == {"Dq": 1234.0, "B": 700.0, "C": None, "out_of_scope": False, "reason": "r"}


@pytest.mark.parametrize("bad", [None, "x", {"Dq": 1}, {"Dq": "abc", "B": 1, "out_of_scope": False}])
def test_final_answer_falls_back_to_last_json_line(bad):
    assert extract.final_answer(jline(dq=5, b=6), bad)["Dq"] == 5.0
    assert extract.final_answer("prose only", bad) is None  # unparseable semantics unchanged


def test_structured_output_without_text_json_is_parsed(tmp_path):
    s = {"Dq": 1000.0, "B": 800.0, "C": None, "out_of_scope": False, "reason": ""}
    p = tmp_path / "t.jsonl"
    evs = [{"type": "assistant", "message": {"content": [
               {"type": "tool_use", "id": "s", "name": "StructuredOutput", "input": s}]}},
           {"type": "result", "result": "no json here", "structured_output": s}]
    p.write_text("".join(json.dumps(e) + "\n" for e in evs), encoding="utf-8")
    tr = extract.read_transcript(p)
    assert numeric.score(task(), extract.final_answer(tr.result_text, tr.result.get("structured_output")))["correct"]


def test_score_counts_exclude_structured_output(tmp_path):
    from tsbench.score.extract import read_transcript
    s = {"Dq": 1.0, "B": 2.0, "C": None, "out_of_scope": False, "reason": ""}
    p = tmp_path / "t.jsonl"
    evs = [{"type": "assistant", "message": {"content": [
               {"type": "tool_use", "id": "b", "name": "Bash", "input": {}},
               {"type": "tool_use", "id": "s", "name": "StructuredOutput", "input": s}]}},
           {"type": "result", "result": "", "structured_output": s}]
    p.write_text("".join(json.dumps(e) + "\n" for e in evs), encoding="utf-8")
    tr = read_transcript(p)
    names = [u["name"] for u in tr.tool_uses if u["name"] != extract.STRUCTURED_TOOL]
    assert names == ["Bash"]


# ---------- helpers of the scorer: cells, hashes, answer shapes ----------

def test_cell_blanks_none_and_nan_only():
    assert score_cli._cell(None) == ""
    assert score_cli._cell(float("nan")) == ""
    assert score_cli._cell(0) == 0 and score_cli._cell(False) is False and score_cli._cell("x") == "x"
    assert score_cli._cell(0.5) == 0.5


def test_prefix_hashes_are_sha256_of_the_canonical_prefix_lines():
    import hashlib
    tasks = {"b": {"z": 1, "a": "é"}, "a": {"id": 2}, "c": {"k": [1, 2]}}
    lines = ['{"a": "é", "z": 1}\n', '{"id": 2}\n', '{"k": [1, 2]}\n']  # sorted keys, no \u escapes
    want = {hashlib.sha256("".join(lines[: n + 1]).encode("utf-8")).hexdigest() for n in range(3)}
    assert len(want) == 3
    assert score_cli._prefix_hashes(tasks) == want
    assert score_cli._prefix_hashes({}) == set()


def test_structured_answer_needs_the_shape_of_its_schema():
    f = score_cli._structured_answer
    batch = {"values": [1]}
    assert f("batch", batch) is batch
    assert f("batch", {"values": 1}) is None and f("batch", {"values": "x"}) is None and f("batch", {}) is None
    pairing = {"nodes": [], "edges": []}
    assert f("pairing", pairing) is pairing
    assert f("pairing", {"nodes": [], "edges": 1}) is None
    assert f("pairing", {"nodes": 1, "edges": []}) is None
    assert f("pairing", {"nodes": 1, "edges": 1}) is None
    diagram = {"points": []}
    assert f("diagram", diagram) is diagram and f("diagram", {"points": 3}) is None
    assert f("fit", batch) is None and f("curve", diagram) is None
    assert f("batch", [1]) is None and f("batch", None) is None and f("diagram", "points") is None


# ---------- check_runs_match ----------

def _manifest(runs, **kw):
    runs.mkdir(parents=True, exist_ok=True)
    (runs / "MANIFEST.json").write_text(json.dumps(kw), encoding="utf-8")


def test_check_runs_match_manifest_hash_of_the_split_is_accepted_for_any_task_dict(tmp_path):
    from tsbench.tasks import hash_path
    digest = next(ln.split("  ", 1)[0] for ln in hash_path("v2").read_text(encoding="utf-8").splitlines()
                  if ln.endswith("  pilot"))
    _manifest(tmp_path, tasks_sha256=digest)
    # the task dict is not the pilot split, so only the hash file can vouch for the manifest
    assert score_cli.check_runs_match(tmp_path, {"X-1": {"prompt": "p"}}, "v2", "pilot") is None
    _manifest(tmp_path, tasks_sha256="0" * 64)
    with pytest.raises(ValueError, match="tasks_sha256 differs"):
        score_cli.check_runs_match(tmp_path, {"X-1": {"prompt": "p"}}, "v2", "pilot")


def test_check_runs_match_accepts_the_hash_of_a_prefix_of_the_tasks(tmp_path):
    tasks = {"A": {"prompt": "a"}, "B": {"prompt": "b"}}
    first = sorted(score_cli._prefix_hashes({"A": tasks["A"]}))[0]
    _manifest(tmp_path, tasks_sha256=first)
    assert score_cli.check_runs_match(tmp_path, tasks, "v2", "pilot") is None


def test_check_runs_match_reads_the_hash_file_name_after_the_first_two_spaces(tmp_path, monkeypatch):
    import tsbench.tasks
    hashes = tmp_path / "tasks.sha256"
    hashes.write_text("abc123  my  split\n", encoding="utf-8")
    monkeypatch.setattr(tsbench.tasks, "hash_path", lambda version: hashes)
    runs = tmp_path / "runs"
    _manifest(runs, tasks_sha256="abc123")
    assert score_cli.check_runs_match(runs, {"X": {"prompt": "p"}}, "v2", "my  split") is None


def test_check_runs_match_unreadable_manifest_is_ignored(tmp_path):
    (tmp_path / "MANIFEST.json").write_text("{not json", encoding="utf-8")
    assert score_cli.check_runs_match(tmp_path, {"A": {"prompt": "a"}}, "v2", "pilot") is None


def test_check_runs_match_refuses_a_manifest_in_another_task_order(tmp_path):
    tasks = {"A": {"prompt": "a"}, "B": {"prompt": "b"}}
    _manifest(tmp_path, tasks=["B", "A"])
    with pytest.raises(ValueError, match="not the v2 pilot order"):
        score_cli.check_runs_match(tmp_path, tasks, "v2", "pilot")
    _manifest(tmp_path, tasks=["A"])  # a prefix in file order is fine
    assert score_cli.check_runs_match(tmp_path, tasks, "v2", "pilot") is None
    _manifest(tmp_path, tasks=["B", "A"], plan_id="p1")  # a plan's subset may be in any order
    assert score_cli.check_runs_match(tmp_path, tasks, "v2", "pilot") is None
    _manifest(tmp_path, tasks=[])
    assert score_cli.check_runs_match(tmp_path, tasks, "v2", "pilot") is None


def test_check_runs_match_plan_prompts(tmp_path):
    tasks = {"A": {"prompt": "a"}, "B": {"prompt": "b"}}
    plan = tmp_path / "plan.jsonl"
    rows = [{"kind": "run", "task_id": "A", "prompt": "a"}, {"kind": "header", "task_id": "A", "prompt": "zzz"},
            {"kind": "run", "task_id": "other", "prompt": "zzz"}]
    plan.write_text("\n".join(json.dumps(r) for r in rows) + "\n\n", encoding="utf-8")
    assert score_cli.check_runs_match(tmp_path, tasks, "v2", "pilot") is None
    rows += [{"kind": "run", "task_id": "B", "prompt": "changed"}, {"kind": "run", "task_id": "B", "prompt": "x"}]
    plan.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    with pytest.raises(ValueError, match=r"prompts that differ from task set v2 for 1 task id\(s\)"):
        score_cli.check_runs_match(tmp_path, tasks, "v2", "pilot")
    plan.write_text("{broken\n", encoding="utf-8")
    assert score_cli.check_runs_match(tmp_path, tasks, "v2", "pilot") is None


def test_check_runs_match_reads_every_file_as_utf8(tmp_path, io_spy):
    tasks = {"A": {"prompt": "a"}}
    _manifest(tmp_path, tasks=["A"])
    (tmp_path / "plan.jsonl").write_text(json.dumps({"kind": "run", "task_id": "A", "prompt": "a"}) + "\n",
                                         encoding="utf-8")
    score_cli.check_runs_match(tmp_path, tasks, "v2", "pilot")
    reads = io_spy.kinds("read_text")
    assert len(reads) >= 3 and all(kw.get("encoding") == "utf-8" for kw in reads)


# ---------- not_evaluable_reason ----------

OVERFLOW_TEXT = "API Error: 400 litellm.ContextWindowExceededError: maximum context length is 131072 tokens"

def _tr_with(result):
    return extract.Transcript(result=result)


@pytest.mark.parametrize("result,want", [
    (None, None),
    ({"is_error": False, "api_error_status": 429}, None),                      # not an error: nothing to excuse
    ({"is_error": True, "api_error_status": 429}, "rate_limited"),
    ({"is_error": True, "api_error_status": "429"}, "rate_limited"),            # a string status counts, too
    ({"is_error": True, "api_error_status": 430}, "api_error"),
    ({"is_error": True, "result": "You hit the Rate Limit"}, "rate_limited"),
    ({"is_error": True, "result": "HTTP error (429) from the API"}, "rate_limited"),
    ({"is_error": True, "result": "no limit (500)"}, None),
    ({"is_error": True, "api_error_status": 400}, "api_error"),
    ({"is_error": True, "api_error_status": 400, "result": "API Error: 400 invalid tool schema"}, "api_error"),
    ({"is_error": True, "api_error_status": 400, "result": OVERFLOW_TEXT}, None),  # a context overflow is wrong
    ({"is_error": True, "api_error_status": 413, "result": "Request too large"}, None),
    ({"is_error": True, "api_error_status": 500, "result": "maximum context length"}, "api_error"),
    ({"is_error": True, "api_error_status": 429, "result": "prompt is too long"}, "rate_limited"),
    ({"is_error": True, "api_error_status": 399}, None),
    ({"is_error": True, "api_error_status": 503}, "api_error"),
    ({"is_error": True, "api_error_status": "503"}, None),                      # only a real int is a status
    ({"is_error": True, "terminal_reason": "api_error"}, "api_error"),
    ({"is_error": True, "terminal_reason": "max_turns"}, None),
    ({"is_error": True, "result": "API Error: overloaded"}, "api_error"),
    ({"is_error": True, "result": "the API Error: is inside"}, None),
    ({"is_error": True, "result": "something else"}, None),
    ({"is_error": True}, None),
    ({"is_error": True, "result": None}, None),
    ("not a dict", None),
])
def test_not_evaluable_reason(result, want):
    assert score_cli.not_evaluable_reason(_tr_with(result)) == want


@pytest.mark.parametrize("text", ["rate limit", "limit (429)"])
def test_rate_limit_text_alone_is_enough(text):
    assert score_cli.not_evaluable_reason(_tr_with({"is_error": True, "result": text})) == "rate_limited"
    # a status that is not 429 does not hide the text
    assert score_cli.not_evaluable_reason(_tr_with({"is_error": True, "result": text,
                                                    "api_error_status": 500})) == "rate_limited"


def test_not_evaluable_reason_looks_at_the_result_text_only_for_the_text_rules():
    # the text of another key must not count, and a missing text is the empty text
    res = {"is_error": True, "reason": "rate limit (429)", "result": ""}
    assert score_cli.not_evaluable_reason(_tr_with(res)) is None
    assert score_cli.not_evaluable_reason(_tr_with({"is_error": True, "result": 0})) is None


# ---------- score_dir: rows, rates, blind ----------

def _result_event(**kw):
    ev = {"type": "result", "subtype": "success", "is_error": False, "result": "", "num_turns": 3,
          "total_cost_usd": 0.02, "duration_ms": 2500, "duration_api_ms": 1500,
          "usage": {"input_tokens": 10, "cache_creation_input_tokens": 20, "cache_read_input_tokens": 30,
                    "output_tokens": 7, "output_tokens_details": {"thinking_tokens": 5}}}
    ev.update(kw)
    return ev


def _write_events(path, events, cond="A"):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    init = json.loads((FIX / f"init_{cond}.json").read_text(encoding="utf-8"))
    path.write_text("".join(json.dumps(e) + "\n" for e in [init, *events]), encoding="utf-8")
    return path


def _closed_form():
    return next(t for t in load("pilot") if t["class"] == "closed_form")


def _mixed_runs(root):
    """k1 rate limited, k2 right with usage and a sidecar, k3 without a result event (sorted in this order)."""
    t = _closed_form()
    good = jline(t["reference"]["Dq"], t["reference"]["B"])
    base = root / "runs" / "m1" / "A" / "low"
    _write_events(base / f"{t['id']}-k1.jsonl", [_result_event(is_error=True, api_error_status=429, result="x")])
    _write_events(base / f"{t['id']}-k2.jsonl", [_result_event(result=good)])
    (base / f"{t['id']}-k2.meta.json").write_text(json.dumps({"wall_time_s": 4.5}), encoding="utf-8")
    _write_events(base / f"{t['id']}-k3.jsonl", [{"type": "assistant", "message": {"content": [
        {"type": "text", "text": good}]}}])
    return root / "runs", t


def test_score_dir_row_values(tmp_path):
    runs, t = _mixed_runs(tmp_path)
    rows = {r["k_index"]: r for r in score_cli.score_dir(runs, "pilot")["rows"]}
    r1, r2, r3 = rows[1], rows[2], rows[3]
    assert (r2["subtype"], r2["class"]) == (t["subtype"], "closed_form") and r2["correct"] is True
    assert r2["num_turns"] == 3 and r2["cost_usd"] == 0.02 and r2["result_subtype"] == "success"
    assert (r2["input_tokens"], r2["output_tokens"], r2["is_error"], r2["has_result"]) == (60, 7, False, True)
    assert r2["duration_s"] == 2.5 and r2["api_duration_s"] == 1.5 and r2["wall_time_s"] == 4.5
    assert (r2["uncached_input_tokens"], r2["cache_creation_tokens"], r2["cache_read_tokens"]) == (10, 20, 30)
    assert (r2["thinking_tokens"], r2["total_tokens"]) == (5, 67)
    assert (r2["evaluable"], r2["not_evaluable_reason"]) == (True, "")
    assert (r1["evaluable"], r1["not_evaluable_reason"], r1["is_error"]) == (False, "rate_limited", True)
    # no result event: no usage, no error flag, no durations, no efficiency detail
    assert r3["has_result"] is False and r3["correct"] is False and r3["unparseable"] is False
    assert r3["input_tokens"] is None and r3["output_tokens"] is None and r3["is_error"] is None
    assert r3["num_turns"] is None and r3["duration_s"] is None and r3["api_duration_s"] is None
    assert r3["wall_time_s"] is None and r3["cost_usd"] is None and r3["result_subtype"] is None
    assert "total_tokens" not in r3 and "uncached_input_tokens" not in r3
    assert r3["evaluable"] is True and r3["not_evaluable_reason"] == ""


def test_score_dir_files_and_rates_skip_runs_that_are_not_evaluable(tmp_path):
    runs, t = _mixed_runs(tmp_path)
    score_cli.score_dir(runs, "pilot")
    scores = read_csv(runs / "scores.csv")
    assert [r["k_index"] for r in scores] == ["1", "2", "3"]
    assert scores[2]["input_tokens"] == "" and scores[2]["is_error"] == "" and scores[2]["uncached_input_tokens"] == ""
    assert scores[1]["api_duration_s"] == "1.5" and scores[1]["num_turns"] == "3"
    assert scores[0]["evaluable"] == "False" and scores[0]["not_evaluable_reason"] == "rate_limited"
    # k1 (not evaluable) comes first in file order and must not hide the runs after it
    rates = read_csv(runs / "rates.csv")
    assert len(rates) == 1
    r = rates[0]
    assert (r["task_id"], r["k"], r["n_correct"], r["rate"]) == (t["id"], "2", "1", "0.5")
    assert float(r["mean_total_tokens"]) == 67 and float(r["mean_duration_s"]) == 2.5  # k3 has no result
    assert float(r["mean_cost_usd_correct"]) == 0.02 and float(r["mean_thinking_tokens_correct"]) == 5


def test_score_dir_unknown_transcripts_and_blind_count(tmp_path):
    runs, t = _mixed_runs(tmp_path)
    _write_events(runs / "m1" / "A" / "low" / "NOPE-9-k1.jsonl", [_result_event()])
    res = score_cli.score_dir(runs, "pilot")
    assert res["unknown"] == ["m1/A/low/NOPE-9-k1.jsonl"] and res["n_blind"] == 0
    assert not (runs / "blind").exists()
    res = score_cli.score_dir(runs, "pilot", blind=True)
    assert res["n_blind"] == 1  # only the evaluable run with a result event
    assert (runs / "blind" / "packets.jsonl").is_file()


def test_score_dir_defaults_and_seed_reach_write_packets(tmp_path, monkeypatch):
    runs, _ = _mixed_runs(tmp_path)
    seen = []
    monkeypatch.setattr(score_cli, "write_packets", lambda entries, out, seed: seen.append((len(entries), out, seed)))
    score_cli.score_dir(runs, blind=True)
    score_cli.score_dir(runs, "pilot", True, 77)
    assert seen == [(1, runs / "blind", 20261024), (1, runs / "blind", 77)]
    score_cli.score_dir(runs)
    assert len(seen) == 2  # blind is off by default


def test_score_dir_passes_the_split_to_the_run_check(tmp_path):
    runs, t = _mixed_runs(tmp_path)
    (runs / "MANIFEST.json").write_text(json.dumps({"tasks": ["not-the-first-task"]}), encoding="utf-8")
    with pytest.raises(ValueError, match="v2 pilot order"):
        score_cli.score_dir(runs, "pilot")


def test_score_dir_writes_utf8_files_with_csv_newlines(tmp_path, io_spy):
    runs, _ = _mixed_runs(tmp_path)
    score_cli.score_dir(runs, "pilot")
    opens = [kw for kw in io_spy.kinds("open") if kw.get("newline") is not None or "newline" in kw]
    assert len(opens) == 2 and all(kw["newline"] == "" and kw["encoding"] == "utf-8" for kw in opens)
    assert all(kw.get("encoding") == "utf-8" for kw in io_spy.kinds("open") + io_spy.kinds("read_text"))
    assert b"\r\n" in (runs / "scores.csv").read_bytes()


def test_score_dir_traces_numbers_of_fit_tasks_even_without_a_schema_key(tmp_path, monkeypatch):
    import tsbench.tasks
    t = task(id="S-1", prompt="p")
    assert "answer_schema" not in t
    monkeypatch.setattr(tsbench.tasks, "load", lambda split, version="v2": [t])
    base = tmp_path / "runs" / "m1" / "B" / "low"
    tool = [{"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "u1", "name": "Bash",
                                                           "input": {}}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "u1",
                                                      "content": "Dq=1000.0 B=800.0"}]}}]
    _write_events(base / "S-1-k1.jsonl", [*tool, _result_event(result=jline())], cond="B")
    row = score_cli.score_dir(tmp_path / "runs", "pilot")["rows"][0]
    assert (row["n_reported"], row["n_traced"], row["n_tool_uses"], row["n_bash_calls"]) == (2, 2, 1, 1)


def test_score_dir_does_not_trace_the_numbers_of_other_answer_schemas(tmp_path):
    t = next(t for t in load("pilot") if t["answer_schema"] == "batch")
    _write_events(tmp_path / "runs" / "m1" / "A" / "low" / f"{t['id']}-k1.jsonl", [_result_event()])
    row = score_cli.score_dir(tmp_path / "runs", "pilot")["rows"][0]
    assert (row["n_reported"], row["n_traced"]) == (0, 0) and row["correct"] is False


# ---------- score_transcript ----------

def test_score_transcript_row_always_has_every_extra_column():
    sc, answer = score_cli.score_transcript(task(), _tr_with(_result_event(result=jline())))
    assert answer is not None and sc["correct"] is True
    for col in score_cli.EXTRA_SCORE_COLUMNS:
        assert math.isnan(sc[col]), col
    assert (sc["answer_source"], sc["rescued"], sc["rescue_stop_reason"]) == ("text_json", False, "")


def test_score_transcript_source_is_text_json_when_the_structured_output_is_unusable():
    res = _result_event(result=jline(), structured_output={"unrelated": 1})
    sc, _ = score_cli.score_transcript(task(), _tr_with(res))
    assert sc["answer_source"] == "text_json" and sc["correct"] is True
    ok = _result_event(result="prose", structured_output=ans())
    sc, _ = score_cli.score_transcript(task(), _tr_with(ok))
    assert sc["answer_source"] == "structured_output"
    both = _result_event(result=jline(1, 2), structured_output=ans())
    assert score_cli.score_transcript(task(), _tr_with(both))[0]["answer_source"] == "structured_output"


def test_score_transcript_without_an_answer_has_no_source():
    sc, answer = score_cli.score_transcript(task(), _tr_with(_result_event(result="no json at all")))
    assert answer is None and sc["unparseable"] is True
    assert (sc["answer_source"], sc["rescued"], sc["rescue_stop_reason"]) == ("none", False, "")
    sc, answer = score_cli.score_transcript(task(), extract.Transcript())
    assert answer is None and sc["answer_source"] == "none"


def test_score_transcript_batch_answer_drops_the_item_list():
    t = next(t for t in load("pilot") if t["answer_schema"] == "batch")
    sc, answer = score_cli.score_transcript(t, _tr_with(_result_event(structured_output={"values": []})))
    assert answer == {"values": []}
    assert "items" not in sc and sc["answer_source"] == "structured_output"
    assert math.isnan(sc["node_precision"])  # filled by the pairing scorer only


# ---------- tokens, summary ----------

def test_tokens_of_counts_numbers_only():
    assert score_cli.tokens_of({"input_tokens": 1, "cache_creation_input_tokens": 2, "cache_read_input_tokens": 3,
                                "output_tokens": 4}) == (6, 4)
    assert score_cli.tokens_of({"input_tokens": "9", "output_tokens": None}) == (0, 0)
    assert score_cli.tokens_of({"input_tokens": 1.9, "output_tokens": True}) == (1, 1)
    assert score_cli.tokens_of(None) == (0, 0) and score_cli.tokens_of([1]) == (0, 0)


def test_summary_lines_exact_text():
    rows = [
        {"model": "m1", "condition": "A", "effort": "low", "correct": True, "unparseable": False, "has_result": True,
         "rescued": True, "evaluable": True, "not_evaluable_reason": ""},
        {"model": "m1", "condition": "A", "effort": "low", "correct": False, "unparseable": True, "has_result": False,
         "rescued": False, "evaluable": True, "not_evaluable_reason": ""},
        {"model": "m1", "condition": "A", "effort": "low", "correct": True, "unparseable": False, "has_result": True,
         "evaluable": False, "not_evaluable_reason": "rate_limited"},
        {"model": "m1", "condition": "A", "effort": "low", "correct": True, "unparseable": False, "has_result": True,
         "evaluable": False, "not_evaluable_reason": "api_error"},
        {"model": "m1", "condition": "A", "effort": "low", "correct": True, "unparseable": False, "has_result": True,
         "evaluable": False, "not_evaluable_reason": "api_error"},
        {"model": "m0", "condition": "C", "effort": "high", "correct": True, "unparseable": False, "has_result": True,
         "not_evaluable_reason": ""},  # no `evaluable` key: counts as evaluable
    ]
    lines = score_cli.summary_lines({"rows": rows, "unknown": ["u"]})
    assert lines == [
        f"{'model':<22}{'cond':<6}{'effort':<8}{'correct':>9}{'n':>5}{'acc':>7}",
        f"{'m0':<22}{'C':<6}{'high':<8}{1:>9}{1:>5}{1.0:>7.2f}",
        f"{'m1':<22}{'A':<6}{'low':<8}{1:>9}{2:>5}{0.5:>7.2f}",
        "transcripts scored: 6",
        "unparseable: 1",
        "no result event: 1",
        "rescued answers (last StructuredOutput call after a limit): 1",
        "not evaluable (excluded from the rates): api_error 2, rate_limited 1",
        "unknown (task not in split): 1",
    ]
    assert score_cli.summary_lines({"rows": [], "unknown": []})[1:] == [
        "transcripts scored: 0", "unparseable: 0", "no result event: 0",
        "rescued answers (last StructuredOutput call after a limit): 0",
        "not evaluable (excluded from the rates): 0", "unknown (task not in split): 0"]


# ---------- main ----------

def test_main_passes_its_arguments_to_score_dir(tmp_path, monkeypatch, capsys):
    calls = []

    def fake(runs, split, blind, seed):
        calls.append((runs, split, blind, seed))
        return {"rows": [], "unknown": ["a", "b", "c", "d", "e", "f"], "n_blind": 0}

    monkeypatch.setattr(score_cli, "score_dir", fake)
    assert score_cli.main(["--runs", str(tmp_path)]) == 0
    assert calls == [(tmp_path, "pilot", False, 20261024)]
    out = capsys.readouterr().out
    assert out.endswith("unknown transcripts (first 5): a, b, c, d, e\n")
    assert "unknown (task not in split): 6\n" in out
    assert score_cli.main(["--runs", str(tmp_path), "--blind", "--blind-seed", "5", "--split", "confirmatory",
                           "--i-have-preregistered", "10.1234/x"]) == 0
    assert calls[1] == (tmp_path, "confirmatory", True, 5) and type(calls[1][3]) is int
    monkeypatch.setattr(score_cli, "score_dir", lambda *a: {"rows": [], "unknown": [], "n_blind": 0})
    capsys.readouterr()
    assert score_cli.main(["--runs", str(tmp_path)]) == 0
    assert "unknown transcripts" not in capsys.readouterr().out


def test_main_messages_and_exit_codes(tmp_path, capsys, monkeypatch):
    assert score_cli.main(["--runs", str(tmp_path / "nope")]) == 2
    assert capsys.readouterr().err == f"not a directory: {tmp_path / 'nope'}\n"
    assert score_cli.main(["--runs", str(tmp_path), "--split", "confirmatory"]) == 2
    assert capsys.readouterr().err == ("refusing to score the confirmatory split without --i-have-preregistered "
                                       "<DOI>\n")

    def refuse(*a):
        raise ValueError("bad runs")

    monkeypatch.setattr(score_cli, "score_dir", refuse)
    assert score_cli.main(["--runs", str(tmp_path)]) == 2
    assert capsys.readouterr().err == "refusing: bad runs\n"


def test_main_argument_parser(tmp_path, capsys):
    with pytest.raises(SystemExit) as e:
        score_cli.main([])  # --runs is required
    assert e.value.code == 2
    assert "--runs" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        score_cli.main(["--runs", str(tmp_path), "--split", "other"])
    assert "invalid choice: 'other'" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        score_cli.main(["--runs", str(tmp_path), "--blind-seed", "x"])
    assert "invalid int value" in capsys.readouterr().err
    with pytest.raises(SystemExit) as e:
        score_cli.main(["--help"])
    assert e.value.code == 0
    out = capsys.readouterr().out
    assert out.startswith("usage: tsbench score ")
    assert "--i-have-preregistered DOI" in out
    assert "Score a runs directory: scores.csv, rates.csv and an optional blinded grading set." in " ".join(out.split())


# ---------- transcript discovery and sidecars ----------

def test_find_transcripts_lists_files_of_the_run_layout_only(tmp_path):
    base = tmp_path / "m1" / "B" / "high"
    base.mkdir(parents=True)
    for name in ("T-1-k2.jsonl", "T-1-k10.jsonl", "T-1-k1.jsonl", "T-1-k1.meta.json", "notes.jsonl", "T-1-kx.jsonl"):
        (base / name).write_text("", encoding="utf-8")
    (base / "T-2-k1.jsonl").mkdir()  # a folder with a transcript name is not a transcript
    (tmp_path / "m1" / "B" / "T-3-k1.jsonl").write_text("", encoding="utf-8")  # one level too high
    found = score_cli.find_transcripts(tmp_path)
    assert [(p.name, m, c, e, t, k) for p, m, c, e, t, k in found] == [
        ("T-1-k1.jsonl", "m1", "B", "high", "T-1", 1), ("T-1-k10.jsonl", "m1", "B", "high", "T-1", 10),
        ("T-1-k2.jsonl", "m1", "B", "high", "T-1", 2)]
    assert all(p.parent == base for p, *_ in found)


def test_wall_time_needs_a_number_in_the_sidecar(tmp_path):
    t = tmp_path / "T-1-k1.jsonl"
    meta = tmp_path / "T-1-k1.meta.json"
    assert score_cli.wall_time(t) is None  # no sidecar
    for text, want in (('{"wall_time_s": 12.5}', 12.5), ('{"wall_time_s": 3}', 3), ('{"wall_time_s": "12"}', None),
                       ('{"wall_time_s": null}', None), ("{}", None), ("not json", None)):
        meta.write_text(text, encoding="utf-8")
        assert score_cli.wall_time(t) == want, text


def test_main_prints_the_summary_lines_one_per_line(tmp_path, monkeypatch, capsys):
    res = {"rows": [], "unknown": [], "n_blind": 0}
    monkeypatch.setattr(score_cli, "score_dir", lambda *a: res)
    assert score_cli.main(["--runs", str(tmp_path)]) == 0
    assert capsys.readouterr().out == "\n".join(score_cli.summary_lines(res)) + "\n"


def test_module_runs_as_a_script(tmp_path, monkeypatch, capsys):
    import runpy
    import warnings
    monkeypatch.setattr("sys.argv", ["score", "--runs", str(tmp_path / "missing")])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # the module is already imported: runpy says so
        with pytest.raises(SystemExit) as e:
            runpy.run_module("tsbench.score.score", run_name="__main__")
    assert e.value.code == 2
    assert capsys.readouterr().err == f"not a directory: {tmp_path / 'missing'}\n"


# ---------- counts and token fields ----------


def _repeated_call_runs(root):
    """One C run whose stream repeats the assistant event of its server call (same tool_use id) and one B run that
    repeats its Bash call; the result event has no output_tokens_details."""
    t = _closed_form()
    good = jline(t["reference"]["Dq"], t["reference"]["B"])
    usage = {"input_tokens": 10, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, "output_tokens": 7}
    for cond, name in (("C", "mcp__tanabesugano__ts_fit_spectrum"), ("B", "Bash")):
        call = {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "toolu_same", "name": name, "input": {"command": "x"}}]}}
        answer = {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "toolu_same", "content": "Dq=1"}]}}
        _write_events(root / "runs" / "m1" / cond / "medium" / f"{t['id']}-k1.jsonl",
                      [call, call, answer, _result_event(result=good, usage=usage)], cond=cond)
    return root / "runs", t


def test_a_repeated_tool_use_id_is_one_call(tmp_path):
    runs, t = _repeated_call_runs(tmp_path)
    rows = {r["condition"]: r for r in score_cli.score_dir(runs, "pilot")["rows"]}
    assert rows["C"]["n_mcp_calls"] == 1 and rows["C"]["n_tool_uses"] == 1
    assert rows["B"]["n_bash_calls"] == 1 and rows["B"]["n_tool_uses"] == 1


def test_thinking_tokens_are_empty_when_the_result_does_not_report_them(tmp_path):
    runs, t = _repeated_call_runs(tmp_path)
    score_cli.score_dir(runs, "pilot")
    rows = {r["condition"]: r for r in read_csv(runs / "scores.csv")}
    assert rows["C"]["thinking_tokens"] == "" and rows["B"]["thinking_tokens"] == ""
    assert rows["C"]["output_tokens"] == "7"


def test_thinking_tokens_reported_as_zero_stay_zero(tmp_path):
    t = _closed_form()
    good = jline(t["reference"]["Dq"], t["reference"]["B"])
    usage = {"input_tokens": 10, "output_tokens": 7, "output_tokens_details": {"thinking_tokens": 0}}
    _write_events(tmp_path / "runs" / "m1" / "A" / "medium" / f"{t['id']}-k1.jsonl",
                  [_result_event(result=good, usage=usage)])
    score_cli.score_dir(tmp_path / "runs", "pilot")
    assert read_csv(tmp_path / "runs" / "scores.csv")[0]["thinking_tokens"] == "0"


def test_a_huge_integer_answer_does_not_abort_the_run_folder(tmp_path):
    t = _closed_form()
    huge = '{"Dq": 1' + "0" * 400 + ', "B": 700, "C": null, "out_of_scope": false, "reason": "x"}'
    base = tmp_path / "runs" / "m1" / "A" / "medium"
    _write_events(base / f"{t['id']}-k1.jsonl", [_result_event(result=huge)])
    _write_events(base / f"{t['id']}-k2.jsonl", [_result_event(
        result="x", structured_output={"Dq": 10**400, "B": 700, "C": None, "out_of_scope": False, "reason": "x"})])
    _write_events(base / f"{t['id']}-k3.jsonl", [_result_event(result=jline(t["reference"]["Dq"],
                                                                           t["reference"]["B"]))])
    score_cli.score_dir(tmp_path / "runs", "pilot")
    rows = {r["k_index"]: r for r in read_csv(tmp_path / "runs" / "scores.csv")}
    assert rows["1"]["correct"] == "False" and rows["1"]["unparseable"] == "True"
    assert rows["2"]["correct"] == "False" and rows["3"]["correct"] == "True"


# ---------- one score row per transcript; run ids in scores.csv ----------

def _sidecar(path, **fields):
    path = pathlib.Path(path)
    path.with_name(path.name[: -len(".jsonl")] + ".meta.json").write_text(json.dumps(fields), encoding="utf-8")


def _sha(path):
    import hashlib
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def _rid(t, k):
    return f"m1/A/low/{t['id']}-k{k}"


def _plan(runs, t, run_ids):
    lines = [{"kind": "header", "plan_id": "plan-1"}] + [
        {"kind": "run", "run_id": i, "task_id": t["id"], "prompt": t["prompt"]} for i in run_ids]
    (runs / "plan.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines), encoding="utf-8")


def test_score_transcript_without_a_result_event_is_no_format_failure():
    sc, answer = score_cli.score_transcript(task(), _tr_with(None))
    assert answer is None and sc["correct"] is False and sc["unparseable"] is False
    sc, _ = score_cli.score_transcript(task(), _tr_with(_result_event(result="no json here")))
    assert sc["unparseable"] is True


def test_score_row_is_the_row_score_dir_writes(tmp_path):
    runs, t = _mixed_runs(tmp_path)
    written = {r["k_index"]: r for r in score_cli.score_dir(runs, "pilot")["rows"]}
    found = score_cli.find_transcripts(runs)
    assert len(found) == 3
    for path, model, cond, effort, tid, k in found:
        row, _answer = score_cli.score_row(t, extract.read_transcript(path), path)
        assert {c: score_cli._cell(row.get(c)) for c in score_cli.SCORE_COLUMNS} == \
            {c: score_cli._cell(written[k].get(c)) for c in score_cli.SCORE_COLUMNS}
        assert (row["model"], row["condition"], row["effort"], row["task_id"], row["k_index"]) == \
            (model, cond, effort, tid, k)


def test_scores_csv_rows_carry_run_id_plan_id_and_hashes(tmp_path):
    runs, t = _mixed_runs(tmp_path)
    base = runs / "m1" / "A" / "low"
    _sidecar(base / f"{t['id']}-k2.jsonl", wall_time_s=4.5, plan_id="plan-1", prompt_sha256="p" * 64)
    score_cli.score_dir(runs, "pilot")
    rows = {r["k_index"]: r for r in read_csv(runs / "scores.csv")}
    assert rows["2"]["run_id"] == _rid(t, 2)
    assert (rows["2"]["plan_id"], rows["2"]["prompt_sha256"]) == ("plan-1", "p" * 64)
    assert rows["2"]["transcript_sha256"] == _sha(base / f"{t['id']}-k2.jsonl")
    assert rows["1"]["run_id"] == _rid(t, 1) and rows["1"]["plan_id"] == "" and rows["1"]["prompt_sha256"] == ""


def test_score_dir_lists_planned_runs_without_a_transcript_and_transcripts_in_no_plan(tmp_path):
    runs, t = _mixed_runs(tmp_path)
    _plan(runs, t, [_rid(t, 1), _rid(t, 2), _rid(t, 4)])
    res = score_cli.score_dir(runs, "pilot")
    assert res["missing"] == [_rid(t, 4)] and res["unplanned"] == [_rid(t, 3)]
    text = "\n".join(score_cli.summary_lines(res))
    assert "planned, no transcript: 1" in text and "transcript in no plan: 1" in text


def test_score_dir_without_a_plan_reports_no_missing_and_no_unplanned_runs(tmp_path):
    runs, _t = _mixed_runs(tmp_path)
    res = score_cli.score_dir(runs, "pilot")
    assert res["missing"] == [] and res["unplanned"] == []
    text = "\n".join(score_cli.summary_lines(res))
    assert "planned, no transcript" not in text


def test_scores_drift_names_runs_added_and_changed_after_scoring(tmp_path):
    runs, t = _mixed_runs(tmp_path)
    ids = {t["id"]}
    score_cli.score_dir(runs, "pilot")
    assert score_cli.scores_drift(runs, ids) == {}
    base = runs / "m1" / "A" / "low"
    _write_events(base / f"{t['id']}-k4.jsonl", [_result_event(result="new")])           # added after scoring
    (base / f"{t['id']}-k1.jsonl").write_text("", encoding="utf-8")                      # overwritten
    (base / f"{t['id']}-k3.jsonl").unlink()                  # a row without a transcript is no drift
    drift = score_cli.scores_drift(runs, ids)
    assert drift == {"new": [_rid(t, 4)], "changed": [_rid(t, 1)]}


def test_scores_drift_reads_a_scores_table_without_run_ids_by_its_fields(tmp_path):
    runs, t = _mixed_runs(tmp_path)
    score_cli.score_dir(runs, "pilot")
    lines = (runs / "scores.csv").read_text(encoding="utf-8").splitlines()
    head = lines[0].split(",")
    keep = [i for i, c in enumerate(head) if c not in ("run_id", "plan_id", "prompt_sha256", "transcript_sha256")]
    old = []
    for ln in csv.reader(lines):
        old.append([ln[i] for i in keep])
    with open(runs / "scores.csv", "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows(old)
    assert score_cli.scores_drift(runs, {t["id"]}) == {}
    _write_events(runs / "m1" / "A" / "low" / f"{t['id']}-k4.jsonl", [_result_event(result="new")])
    assert score_cli.scores_drift(runs, {t["id"]}) == {"new": [_rid(t, 4)]}


def test_scores_drift_prefers_the_manifest_hashes_for_a_changed_transcript(tmp_path):
    runs, t = _mixed_runs(tmp_path)
    score_cli.score_dir(runs, "pilot")
    base = runs / "m1" / "A" / "low"
    (runs / "MANIFEST.json").write_text(json.dumps({"transcripts": {
        _rid(t, 1): _sha(base / f"{t['id']}-k1.jsonl"), _rid(t, 2): "0" * 64, _rid(t, 3): _sha(
            base / f"{t['id']}-k3.jsonl")}}), encoding="utf-8")
    assert score_cli.scores_drift(runs, {t["id"]}) == {"changed": [_rid(t, 2)]}
