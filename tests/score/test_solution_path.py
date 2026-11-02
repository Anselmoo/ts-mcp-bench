"""Tests for src/tsbench/score/solution_path.py: steps, scripts, method tags, links from answer numbers to steps."""
from __future__ import annotations

import hashlib
import json

from tsbench.core import resource
from tsbench.core.schema import validate_instance
from tsbench.score import solution_path as sp


def _io_counter(monkeypatch, path):
    """Every way a file can be read: builtins.open, Path.read_bytes, Path.read_text, Path.open."""
    import builtins
    import pathlib
    seen = []
    path_cls = pathlib.Path
    real_open, real_rb, real_rt, real_po = builtins.open, path_cls.read_bytes, path_cls.read_text, path_cls.open

    def hit(f):
        if str(f) == str(path):
            seen.append(str(f))

    monkeypatch.setattr(builtins, "open", lambda f, *a, **k: (hit(f), real_open(f, *a, **k))[1])
    monkeypatch.setattr(pathlib.Path, "read_bytes", lambda s: (hit(s), real_rb(s))[1])
    monkeypatch.setattr(pathlib.Path, "read_text", lambda s, *a, **k: (hit(s), real_rt(s, *a, **k))[1])
    monkeypatch.setattr(pathlib.Path, "open", lambda s, *a, **k: (hit(s), real_po(s, *a, **k))[1])
    return seen

SCHEMA = json.loads(resource("schemas/solution_path.schema.json").read_text(encoding="utf-8"))

INTERP = ("import numpy as np\n"
          "tab = [18.5, 17.0, 16.0, 15.5]\n"
          "print('E =', round(float(np.interp(1.2, [0, 1, 2, 3], tab)), 2))\n")
EIGEN = ("import numpy as np\n"
         "H = np.array([[1.0, 0.2], [0.2, 3.0]])\n"
         "w = np.linalg.eigvalsh(H)\n"
         "dq, b = 2469.0 / 2, 1357.8 / 2\n"
         "print('Dq =', dq, 'B =', b)\n")


def _use(i, name, inp):
    return {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": i, "name": name, "input": inp}]}}


def _res(i, content, err=False):
    return {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": i, "content": content, "is_error": err}]}}


def _transcript(tmp_path, answer=None):
    answer = answer or {"Dq": 1234.5, "B": 678.9, "C": None, "out_of_scope": False, "reason": "fit", "n": 31}
    events = [
        {"type": "system", "subtype": "init", "tools": ["Bash", "StructuredOutput"]},
        _use("t0", "Bash", {"command": f"cat > interp.py <<'EOF'\n{INTERP}EOF\npython3 interp.py",
                            "description": "interpolate a table"}),
        _res("t0", "E = 16.7\n"),
        _use("t1", "Bash", {"command": f"cat > fit.py <<'EOF'\n{EIGEN}EOF\npython3 fit.py",
                            "description": "diagonalise"}),
        _res("t1", "Dq = 1234.5 B = 678.9\n"),
        _use("t2", "Bash", {"command": "sed -i 's/1.0/2.0/' fit.py && python3 fit.py", "description": "edit, rerun"}),
        _res("t2", "Exit code 1\nTraceback ...\n31\n", err=True),
        _use("t3", "StructuredOutput", answer),
        _res("t3", "ok"),
        {"type": "result", "subtype": "success", "result": "done", "structured_output": answer},
    ]
    path = tmp_path / "B" / "medium" / "P-numerical-01-k1.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    return path


def test_the_transcript_is_parsed_once(tmp_path, monkeypatch):
    import builtins
    t = _transcript(tmp_path)
    real, seen = builtins.open, []

    def counting(file, *a, **kw):
        if str(file) == str(t):
            seen.append(file)
        return real(file, *a, **kw)

    monkeypatch.setattr(builtins, "open", counting)
    path = sp.solution_path(t)
    assert len(seen) == 1 and path["summary"]["n_steps"] == 3


def test_a_parsed_transcript_is_not_read_again(tmp_path, monkeypatch):
    import builtins

    from tsbench.score.extract import read_transcript
    t = _transcript(tmp_path)
    tr = read_transcript(t)
    real, seen = builtins.open, []

    def counting(file, *a, **kw):
        if str(file) == str(t):
            seen.append(file)
        return real(file, *a, **kw)

    monkeypatch.setattr(builtins, "open", counting)
    path = sp.solution_path(t, tr=tr)
    assert seen == [] and path == sp.solution_path(t)


def test_the_path_validates_against_its_schema(tmp_path):
    path = sp.solution_path(_transcript(tmp_path))
    assert validate_instance(SCHEMA, path) == []
    assert path["format"] == "tsbench.solution_path/1"
    assert path["transcript_sha256"] == hashlib.sha256(_transcript(tmp_path / "x").read_bytes()).hexdigest()


def test_steps_hold_the_code_its_hash_and_stdout(tmp_path):
    steps = sp.solution_path(_transcript(tmp_path))["steps"]
    assert [s["index"] for s in steps] == [0, 1, 2]  # StructuredOutput is the answer channel, not a step
    first = steps[0]
    assert first["scripts"][0]["name"] == "interp.py"
    assert first["scripts"][0]["code"] == INTERP
    assert first["scripts"][0]["sha256"] == hashlib.sha256(INTERP.encode("utf-8")).hexdigest()
    assert first["stdout"] == "E = 16.7\n" and first["exit"] == 0 and not first["is_error"]
    assert first["description"] == "interpolate a table"


def test_methods_and_key_lines(tmp_path):
    steps = sp.solution_path(_transcript(tmp_path))["steps"]
    assert set(steps[0]["methods"]) == {"interpolation", "typed_table"}
    assert steps[1]["methods"] == ["eigen_solver"]
    lines = {(k["method"], k["line"]) for k in steps[1]["key_lines"]}
    assert ("eigen_solver", 3) in lines  # w = np.linalg.eigvalsh(H)
    assert any(k["text"].startswith("H = np.array") for k in steps[1]["key_lines"])  # the matrix itself
    first = {(k["method"], k["line"]) for k in steps[0]["key_lines"]}
    assert ("typed_table", 2) in first and ("interpolation", 3) in first  # typed-in numbers are shown as such


def test_a_one_dimensional_array_is_not_a_matrix():
    keys = sp._key_lines("x.py", "x = np.array([0.0, 0.5])\nM = np.zeros((3, 3))\nM[i, j] += 1\n")
    assert [(k["line"], k["method"]) for k in keys] == [(2, "matrix"), (3, "matrix")]


def test_a_rerun_points_to_the_step_that_wrote_the_script(tmp_path):
    steps = sp.solution_path(_transcript(tmp_path))["steps"]
    assert steps[1]["runs"] == [{"name": "fit.py", "written_in_step": 1}]
    assert steps[2]["scripts"] == [] and steps[2]["runs"] == [{"name": "fit.py", "written_in_step": 1}]
    assert steps[2]["edits_in_place"] is True and steps[2]["exit"] == 1 and steps[2]["is_error"] is True


def test_each_answer_number_links_to_the_step_that_printed_it(tmp_path):
    path = sp.solution_path(_transcript(tmp_path))
    values = {v["path"]: v for v in path["values"]}
    assert set(values) == {"Dq", "B", "n"}  # null and booleans are not numbers
    assert values["Dq"]["steps"] == [1] and values["Dq"]["source_step"] == 1 and not values["Dq"]["weak"]
    assert path["steps"][1]["produces"] == ["Dq", "B"]
    # a small integer is weak: printed by chance (here in a traceback); it never becomes a source
    assert values["n"]["weak"] and values["n"]["steps"] == [2] and values["n"]["source_step"] is None
    s = path["summary"]
    assert (s["n_steps"], s["n_scripts"], s["n_failed_steps"]) == (3, 2, 1)
    assert (s["n_values"], s["n_linked"], s["n_weak"]) == (3, 2, 1)
    assert s["source_steps"] == [1] and s["edits_in_place"] is True


def test_a_script_that_only_retypes_printed_numbers_is_not_their_source(tmp_path):
    copy = "import json\nprint(json.dumps({'Dq': 1234.5, 'B': 678.9}))\n"
    events = [_use("t0", "Bash", {"command": f"cat > fit.py <<'EOF'\n{EIGEN}EOF\npython3 fit.py"}),
              _res("t0", "Dq = 1234.5 B = 678.9\n"),
              _use("t1", "Bash", {"command": f"cat > final.py <<'EOF'\n{copy}EOF\npython3 final.py"}),
              _res("t1", '{"Dq": 1234.5, "B": 678.9}\n'),
              {"type": "result", "subtype": "success", "structured_output": {"Dq": 1234.5, "B": 678.9}}]
    path = tmp_path / "copy-k1.jsonl"
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    sol = sp.solution_path(path)
    values = {v["path"]: v for v in sol["values"]}
    assert values["Dq"]["steps"] == [0, 1] and values["Dq"]["source_step"] == 0
    assert values["Dq"]["typed_in_steps"] == [1]  # the number stands as a literal in final.py
    assert sol["steps"][0]["produces"] == ["Dq", "B"] and sol["steps"][1]["produces"] == []
    assert validate_instance(SCHEMA, sol) == []


def test_nested_answers_and_the_relative_tolerance(tmp_path):
    answer = {"points": [{"dq_over_b": 1.15, "term": "4T1g", "e_over_b": 16.71}], "reason": "r"}
    values = {v["path"]: v for v in sp.solution_path(_transcript(tmp_path, answer))["values"]}
    assert values["points[0].e_over_b"]["steps"] == [0]  # 16.7 printed, 16.71 reported: within 0.5 %
    assert values["points[0].dq_over_b"]["steps"] == []


def test_scanner_and_tolerance_are_the_ones_of_numeric_trace(tmp_path):
    from tsbench.score import numeric
    assert sp.numbers_in is numeric.numbers_in and sp.TRACE_RTOL == numeric.TRACE_RTOL
    # a printed thousands separator is read as in numeric.trace; compact JSON lists are not merged
    answer = {"Dq": 2033.6, "B": 109.47, "C": 761.0}
    events = [_use("t0", "Bash", {"command": "python3 a.py"}), _res("t0", "Dq = 2,033.6\n"),
              _use("t1", "Bash", {"command": "python3 b.py"}),
              _res("t1", '{"r":[-47.46219244517488,109.47128400050133,-61.86],"fit":[1850,761,3402]}\n'),
              {"type": "result", "subtype": "success", "structured_output": answer}]
    path = tmp_path / "list-k1.jsonl"
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    values = {v["path"]: v for v in sp.solution_path(path)["values"]}
    assert values["Dq"]["steps"] == [0] and values["B"]["steps"] == [1] and values["C"]["steps"] == [1]


def test_a_huge_integer_in_the_answer_is_skipped_not_an_overflow(tmp_path):
    answer = {"Dq": 10**400, "B": 678.9}
    events = [_use("t0", "Bash", {"command": "python3 a.py"}), _res("t0", "B = 678.9\n"),
              {"type": "result", "subtype": "success", "structured_output": answer}]
    path = tmp_path / "huge-k1.jsonl"
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    assert [v["path"] for v in sp.solution_path(path)["values"]] == ["B"]


def test_thinking_token_progress_lines_are_not_read(tmp_path):
    prog = {"type": "system", "subtype": "thinking_tokens", "estimated_tokens": 3}
    answer = {"Dq": 1234.5, "B": 678.9}
    events = [prog, _use("t0", "Bash", {"command": "python3 a.py"}), prog, _res("t0", "Dq = 1234.5 B = 678.9\n"),
              {"type": "result", "subtype": "success", "structured_output": answer}]
    path = tmp_path / "prog-k1.jsonl"
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    sol = sp.solution_path(path)
    assert [v["steps"] for v in sol["values"]] == [[0], [0]]


def test_a_transcript_without_tools_has_an_empty_path(tmp_path):
    p = tmp_path / "A-k1.jsonl"
    p.write_text(json.dumps({"type": "result", "subtype": "success", "result": "x"}) + "\n", encoding="utf-8")
    path = sp.solution_path(p)
    assert path["steps"] == [] and path["answer"] is None and path["values"] == []
    assert validate_instance(SCHEMA, path) == []


def test_main_writes_to_out_and_never_into_the_runs(tmp_path, io_spy):
    runs = tmp_path / "runs"
    _transcript(runs)
    before = sorted(p.relative_to(runs) for p in runs.rglob("*"))
    out = tmp_path / "out"
    assert sp.main(["--runs", str(runs), "--out", str(out)]) == 0
    assert sorted(p.relative_to(runs) for p in runs.rglob("*")) == before
    written = json.loads((out / "B" / "medium" / "P-numerical-01-k1.path.json").read_text(encoding="utf-8"))
    assert written["summary"]["source_steps"] == [1]
    rows = (out / "paths.csv").read_text(encoding="utf-8").splitlines()
    assert rows[0].startswith("transcript,n_steps,n_scripts") and len(rows) == 2
    assert all(kw.get("encoding") == "utf-8" for kw in io_spy.kinds("read_text") + io_spy.kinds("write_text"))


def test_the_transcript_is_read_once_and_hashed_from_that_read(tmp_path, monkeypatch):
    t = _transcript(tmp_path)
    reads = _io_counter(monkeypatch, t)
    got = sp.solution_path(t)
    assert len(reads) == 1
    assert got["transcript_sha256"] == hashlib.sha256(t.read_bytes()).hexdigest()


def test_a_non_finite_or_huge_answer_number_does_not_stop_the_path(tmp_path):
    t = _transcript(tmp_path)
    text = t.read_text(encoding="utf-8")
    t.write_text(text + json.dumps({"type": "result", "structured_output": {"Dq": 1}}).replace(
        '"Dq": 1', '"Dq": 1e400, "B": NaN, "C": -Infinity, "n": 1234.5') + "\n", encoding="utf-8")
    got = sp.solution_path(t)
    assert [v["path"] for v in got["values"]] == ["n"]


def test_an_unhashable_tool_use_id_does_not_stop_the_path(tmp_path):
    t = tmp_path / "x-k1.jsonl"
    t.write_text("\n".join(json.dumps(e) for e in [_use(["a"], "Bash", {"command": "ls"}), _res(["a"], "1")]) + "\n",
                 encoding="utf-8")
    assert len(sp.solution_path(t)["steps"]) == 1


def test_a_number_with_thousands_separators_is_one_value_in_the_step_output(tmp_path):
    t = tmp_path / "x-k1.jsonl"
    events = [_use("a", "Bash", {"command": "echo"}), _res("a", "area 2,033.6 cm"),
              {"type": "result", "structured_output": {"area": 2033.6}}]
    t.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    [v] = sp.solution_path(t)["values"]
    assert v["steps"] == [0]


FIT_TASK = {"id": "P-numerical-01", "answer_schema": "fit", "required": ["Dq", "B"]}
VALID = {"Dq": 1234.5, "B": 678.9, "C": None, "out_of_scope": False, "reason": "fit"}


def _write(tmp_path, events, name="B/medium/P-numerical-01-k1.jsonl"):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    return path


def test_the_answer_is_the_one_the_scorer_used_when_it_came_from_the_text_line(tmp_path):
    # no structured_output in the result event: the scorer reads the JSON line of the text (answer_source text_json)
    line = json.dumps(VALID)
    events = [_use("t0", "Bash", {"command": "python3 a.py"}), _res("t0", "Dq = 1234.5 B = 678.9\n"),
              {"type": "result", "subtype": "success", "result": f"Done.\n{line}"}]
    got = sp.solution_path(_write(tmp_path, events), task=FIT_TASK)
    assert got["answer"] == VALID
    assert got["summary"]["n_values"] == 2 and got["summary"]["n_linked"] == 2


def test_a_rescued_answer_is_the_last_valid_call_not_the_last_call(tmp_path):
    bad = {"Dq": "2044 cm-1", "B": 700.0, "C": None, "out_of_scope": False, "reason": "x"}
    events = [_use("t0", "Bash", {"command": "python3 a.py"}), _res("t0", "Dq = 1234.5 B = 678.9\n"),
              _use("s1", "StructuredOutput", VALID), _res("s1", "ok"),
              _use("s2", "StructuredOutput", bad), _res("s2", "Output does not match required schema", err=True),
              {"type": "result", "subtype": "error_max_turns", "is_error": True, "result": ""}]
    got = sp.solution_path(_write(tmp_path, events), task=FIT_TASK)
    assert got["answer"] == VALID and got["summary"]["n_linked"] == 2


def test_an_answer_the_scorer_rejects_is_no_answer_of_the_path(tmp_path):
    bad = {"Dq": "2044 cm-1", "B": 700.0, "C": None, "out_of_scope": False, "reason": "x"}
    events = [_use("s2", "StructuredOutput", bad), _res("s2", "bad", err=True),
              {"type": "result", "subtype": "error_max_structured_output_retries", "is_error": True, "result": ""}]
    assert sp.solution_path(_write(tmp_path, events), task=FIT_TASK)["answer"] is None


def test_main_looks_the_task_up_by_the_file_name(tmp_path):
    runs, out = tmp_path / "runs", tmp_path / "out"
    line = json.dumps(VALID)
    events = [_use("t0", "Bash", {"command": "python3 a.py"}), _res("t0", "Dq = 1234.5 B = 678.9\n"),
              {"type": "result", "subtype": "success", "result": line}]
    _write(runs, events)
    assert sp.main(["--runs", str(runs), "--out", str(out)]) == 0
    written = json.loads((out / "B" / "medium" / "P-numerical-01-k1.path.json").read_text(encoding="utf-8"))
    assert written["answer"] == VALID and written["summary"]["n_linked"] == 2
