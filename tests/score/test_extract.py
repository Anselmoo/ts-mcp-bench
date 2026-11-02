"""Tests for src/tsbench/score/extract.py: transcript reading, answer extraction, rescue of an answer."""
from __future__ import annotations

import json

import pytest

from tsbench.score import extract


def _write(path, lines):
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


ANSWER = {"Dq": 1000.0, "B": 800.0, "C": None, "out_of_scope": False, "reason": "r"}


# ---------- flatten_text ----------

def test_flatten_text_cases():
    f = extract.flatten_text
    assert f(None) == "" and f("abc") == "abc"
    assert f(["a", {"text": "b"}, None]) == "a\nb\n"
    assert f({"text": "t", "content": "ignored"}) == "t"
    assert f({"content": ["x", "y"]}) == "x\ny"
    assert f({"content": {"text": "deep"}}) == "deep"
    assert f({"text": 5, "content": "c"}) == "c"  # a text that is not a string does not count
    assert f({"a": "é", "b": 1}) == '{"a": "é", "b": 1}'  # no content, no text: the JSON itself, not escaped
    assert f({"text": 5}) == '{"text": 5}'
    assert f(12) == "12" and f(True) == "True"
    assert f([]) == ""


def test_flatten_text_maps_an_image_block_to_a_marker():
    """The base64 payload of an image block is not text the tool printed; no digit runs may come out of it."""
    img = {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "iVBOR0123456789" * 50}}
    assert extract.flatten_text(img) == "[image]"
    assert extract.flatten_text([{"type": "text", "text": "plot"}, img]) == "plot\n[image]"
    assert extract.flatten_text({"content": [img]}) == "[image]"


def test_read_transcript_tool_result_with_image_has_no_payload_digits(tmp_path):
    img = {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "A12345678B" * 100}}
    ev = {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "t1", "content": [{"type": "text", "text": "saved"}, img]}]}}
    tr = extract.read_transcript(_write(tmp_path / "t.jsonl", [json.dumps(ev)]))
    assert tr.tool_results == [{"tool_use_id": "t1", "content": "saved\n[image]"}]


# ---------- huge integers ----------

def test_coerce_number_huge_integer_is_refused_not_an_overflow():
    with pytest.raises(ValueError, match="non-finite"):
        extract._coerce_number(10**400)
    with pytest.raises(ValueError, match="non-finite"):
        extract._coerce_number(-(10**400))


def test_final_answer_with_a_huge_integer_does_not_raise():
    text = '{"Dq": 1' + "0" * 400 + ', "B": 700, "C": null, "out_of_scope": false, "reason": "x"}'
    assert extract.final_answer(text) is None  # skipped like the same value as a string
    good = '{"Dq": 1000, "B": 700, "C": null, "out_of_scope": false, "reason": "x"}'
    earlier = extract.final_answer(good + "\n" + text)  # an earlier valid line is still found
    assert earlier is not None and earlier["Dq"] == 1000.0
    structured = {"Dq": 10**400, "B": 700, "C": None, "out_of_scope": False, "reason": "x"}
    fallback = extract.final_answer(good, structured)     # structured refused, text fallback
    assert fallback is not None and fallback["Dq"] == 1000.0
    assert extract.final_answer(None, structured) is None


def test_curve_answer_with_a_huge_integer_is_none():
    assert extract.curve_answer({"points": [{"dq_over_b": 10**400, "term": "a", "e_over_b": 1.0}]}) is None


# ---------- tool_use ids ----------

def _uses(path, ids):
    ev = [{"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": i, "name": "Bash", "input": {"command": f"echo {n}"}}]}}
          for n, i in enumerate(ids)]
    return _write(path, [json.dumps(e) for e in ev])


def test_read_transcript_unhashable_tool_use_id_does_not_raise(tmp_path):
    tr = extract.read_transcript(_uses(tmp_path / "t.jsonl", [["x"], {"a": 1}, "ok"]))
    assert [u["input"]["command"] for u in tr.tool_uses] == ["echo 0", "echo 1", "echo 2"]


def test_read_transcript_unhashable_tool_result_id_does_not_raise(tmp_path):
    ev = {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": ["x"], "content": "out"}]}}
    tr = extract.read_transcript(_write(tmp_path / "t.jsonl", [json.dumps(ev)]))
    assert tr.tool_results == [{"tool_use_id": ["x"], "content": "out"}]


def test_read_transcript_empty_or_missing_ids_never_merge_calls(tmp_path):
    tr = extract.read_transcript(_uses(tmp_path / "t.jsonl", ["", "", None, None, "a", "a"]))
    assert [u["input"]["command"] for u in tr.tool_uses] == ["echo 0", "echo 1", "echo 2", "echo 3", "echo 4"]


# ---------- progress lines ----------

def test_read_transcript_drops_thinking_token_progress_lines(tmp_path):
    progress = {"type": "system", "subtype": "thinking_tokens", "tokens": 12}
    keep = {"type": "system", "subtype": "hook", "x": 1}
    res = {"type": "result", "result": "R"}
    p = _write(tmp_path / "t.jsonl", [json.dumps(e) for e in (progress, keep, progress, res)])
    tr = extract.read_transcript(p)
    assert tr.events == [keep, res] and tr.n_bad_lines == 0 and tr.result_text == "R"


def test_read_transcript_counts_a_truncated_progress_line_as_bad(tmp_path):
    """A killed run can end in the middle of a progress line: that is a bad line, not a dropped progress line."""
    full = json.dumps({"type": "system", "subtype": "thinking_tokens", "uuid": "96b4aeca-0a1e"})
    p = tmp_path / "t.jsonl"
    p.write_text(full + "\n" + json.dumps({"type": "result", "result": "R"}) + "\n" + full[:-12], encoding="utf-8")
    tr = extract.read_transcript(p)
    assert tr.n_bad_lines == 1 and tr.result_text == "R" and len(tr.events) == 1
    assert extract.is_progress_line(full) and not extract.is_progress_line(full[:-12])


# ---------- _blocks and read_transcript ----------

def test_blocks_of_an_event():
    assert extract._blocks({"message": {"content": "plain"}}) == [{"type": "text", "text": "plain"}]
    assert extract._blocks({"message": {"content": [{"type": "x"}]}}) == [{"type": "x"}]
    assert extract._blocks({"message": {"content": 5}}) == []
    assert extract._blocks({"message": "text"}) == []
    assert extract._blocks({}) == []


def test_read_transcript_string_content_is_assistant_text(tmp_path):
    p = _write(tmp_path / "t.jsonl", [
        json.dumps({"type": "assistant", "message": {"content": "hello"}}),
        json.dumps({"type": "user", "message": {"content": "not a tool result"}}),
    ])
    tr = extract.read_transcript(p)
    assert tr.assistant_texts == ["hello"] and tr.tool_results == [] and tr.tool_uses == []


def test_read_transcript_counts_every_bad_line_and_keeps_going(tmp_path):
    good = {"type": "assistant", "message": {"content": [{"type": "text", "text": "late"}]}}
    p = _write(tmp_path / "t.jsonl", [
        "{broken", "", "   ", "[1, 2]", '"just a string"', "{also broken", json.dumps(good),
        "{trailing garbage", json.dumps({"type": "result", "result": "R"})])
    tr = extract.read_transcript(p)
    assert tr.n_bad_lines == 5  # two broken, a list, a string, one more broken
    assert tr.assistant_texts == ["late"] and tr.result_text == "R"
    assert len(tr.events) == 2


def test_read_transcript_first_init_only_and_type_checks(tmp_path):
    init1 = {"type": "system", "subtype": "init", "model": "first"}
    init2 = {"type": "system", "subtype": "init", "model": "second"}
    other = {"type": "system", "subtype": "hook", "model": "no"}
    p = _write(tmp_path / "t.jsonl", [json.dumps(e) for e in (other, init1, init2)])
    tr = extract.read_transcript(p)
    assert tr.init == init1
    # a system event of another subtype is not the init; an init subtype of a non-system event neither
    p2 = _write(tmp_path / "u.jsonl", [json.dumps(other), json.dumps({"type": "user", "subtype": "init"})])
    assert extract.read_transcript(p2).init is None
    # a non-system event must never become the init, even when tr.init is still empty
    p3 = _write(tmp_path / "v.jsonl", [json.dumps({"type": "assistant", "subtype": "init", "message": {}})])
    assert extract.read_transcript(p3).init is None


def test_read_transcript_blocks(tmp_path):
    ev = [
        {"type": "assistant", "message": {"content": [
            "a bare string block", {"type": "text", "text": "one"}, {"type": "text", "text": 5},
            {"type": "text"}, {"type": "tool_use", "id": "u1", "name": "Bash", "input": {"command": "ls"}},
            {"type": "tool_use", "id": "u2"}, {"type": "thinking", "text": "hmm"}]}},
        {"type": "user", "message": {"content": [
            "bare", {"type": "text", "text": "not a result"},
            {"type": "tool_result", "tool_use_id": "u1", "content": "out"},
            {"type": "tool_result", "tool_use_id": "u2"}]}},
    ]
    tr = extract.read_transcript(_write(tmp_path / "t.jsonl", [json.dumps(e) for e in ev]))
    assert tr.assistant_texts == ["one"]
    assert tr.tool_uses == [{"name": "Bash", "input": {"command": "ls"}, "id": "u1"},
                            {"name": "", "input": None, "id": "u2"}]
    assert tr.tool_results == [{"tool_use_id": "u1", "content": "out"}, {"tool_use_id": "u2", "content": ""}]


def test_read_transcript_is_lenient_about_bytes_and_encoding(tmp_path, io_spy):
    p = tmp_path / "t.jsonl"
    good = json.dumps({"type": "result", "result": "é"}, ensure_ascii=False)
    p.write_bytes(b'{"type": "assistant", "message": {"content": "caf\xe9 \xff"}}\n' + good.encode("utf-8") + b"\n")
    tr = extract.read_transcript(p)
    assert tr.assistant_texts == ["caf� �"]  # undecodable bytes become U+FFFD, the read goes on
    assert tr.result_text == "é"
    [kw] = io_spy.kinds("open")
    assert kw == {"encoding": "utf-8", "errors": "replace"}


# ---------- numbers and answers ----------

@pytest.mark.parametrize("value,msg", [
    (True, "bool is not a number"), ("abc", "not a number: 'abc'"), ([1], r"not a number: \[1\]"),
    (float("inf"), "non-finite"), (float("nan"), "non-finite"), ("1e999", "non-finite"),
])
def test_coerce_number_refusals_say_why(value, msg):
    with pytest.raises(ValueError, match=f"^{msg}$"):
        extract._coerce_number(value)


def test_coerce_number_values():
    c = extract._coerce_number
    assert c(None) is None and c(3) == 3.0 and type(c(3)) is float
    assert c(" 8.5e2 ") == 850.0 and c("-.5") == -0.5 and c("+7") == 7.0
    assert c(0) == 0.0 and c(False if False else 0.0) == 0.0


def test_strip_decor():
    s = extract._strip_decor
    assert s('  {"a": 1}  ') == '{"a": 1}'
    assert s('```json{"a": 1}```') == '{"a": 1}'
    assert s('```JSON {"a": 1}') == '{"a": 1}'
    assert s('```{"a": 1}```') == '{"a": 1}'
    assert s('`{"a": 1}`') == '{"a": 1}'
    assert s('```jso{"a": 1}') == 'jso{"a": 1}'  # not the language tag: kept
    assert s('```{"json": 1}') == '{"json": 1}'
    assert s("```") == "" and s("") == ""
    assert s('{"a": 1}X') == '{"a": 1}X' and s('X{"a": 1}') == 'X{"a": 1}'  # only backticks are decoration


def test_final_answer_keeps_looking_after_lines_that_are_no_answer():
    good = json.dumps({"Dq": 1, "B": 2, "C": None, "out_of_scope": False, "reason": "why"})
    for tail in ("{broken json", '{"Dq": 1}', '["not", "an", "object"]', "{}", '{"Dq": "x", "B": 1, "out_of_scope": 1}',
                 "", "prose", "```"):
        got = extract.final_answer(good + "\n" + tail)
        assert got is not None and got["Dq"] == 1.0 and got["reason"] == "why", tail
    assert extract.final_answer('["a"]\n{"Dq": 1}\n{broken') is None


def test_final_answer_reason_and_scope_are_taken_from_the_json():
    a = extract.final_answer('{"Dq": 1, "B": 2, "out_of_scope": true, "reason": "because"}')
    assert a == {"Dq": 1.0, "B": 2.0, "C": None, "out_of_scope": True, "reason": "because"}
    no_reason = extract.final_answer('{"Dq": 1, "B": 2, "out_of_scope": false}')
    assert no_reason is not None and no_reason["reason"] is None
    s = extract.final_answer("", {"Dq": 1, "B": 2, "out_of_scope": False})
    assert s == {"Dq": 1.0, "B": 2.0, "C": None, "out_of_scope": False, "reason": None}


# ---------- curve answers ----------

def test_curve_answer_shapes():
    ok = {"points": [{"dq_over_b": "1", "term": "T", "e_over_b": 2}, {"dq_over_b": 3, "e_over_b": 4.5, "term": 7}],
          "reason": "r"}
    assert extract.curve_answer(ok) == {"points": [{"dq_over_b": 1.0, "term": "T", "e_over_b": 2.0},
                                                   {"dq_over_b": 3.0, "term": "", "e_over_b": 4.5}], "reason": "r"}
    assert extract.curve_answer({"points": []}) == {"points": [], "reason": None}
    for bad in (None, [], {"points": "x"}, {"points": [1]}, {"points": [{"dq_over_b": "a", "e_over_b": 1}]},
                {"points": [{"dq_over_b": None, "e_over_b": 1}]}, {"points": [{"dq_over_b": 1, "e_over_b": None}]},
                {"points": [{"dq_over_b": 1}]}, {"points": [{"dq_over_b": 1, "e_over_b": True}]}):
        assert extract.curve_answer(bad) is None, bad


# ---------- rescue ----------

def test_rescue_stop_reason():
    T = extract.Transcript
    assert extract.rescue_stop_reason(T()) == "no_result"
    assert extract.rescue_stop_reason(T(result={"structured_output": {"a": 1}, "subtype": "error_max_turns"})) is None
    for sub in extract.RESCUE_SUBTYPES:
        assert extract.rescue_stop_reason(T(result={"subtype": sub})) == sub
        assert extract.rescue_stop_reason(T(result={"subtype": sub, "structured_output": "no dict"})) == sub
    assert extract.RESCUE_SUBTYPES == ("error_max_turns", "error_max_budget_usd")
    assert extract.rescue_stop_reason(T(result={"subtype": "success"})) is None
    assert extract.rescue_stop_reason(T(result={})) is None


def test_rescue_structured_output_takes_the_last_valid_call_of_the_named_schema(tmp_path, io_spy):
    extract._schema.cache_clear()  # the schema is read once per process; this test checks how that read opens it
    use = lambda name, inp, i=0: {"name": name, "input": inp, "id": f"u{i}"}  # noqa: E731
    tr = extract.Transcript(tool_uses=[use("StructuredOutput", ANSWER, 1), use("Bash", {"x": 1}, 2),
                                       use("StructuredOutput", {"Dq": "bad"}, 3), use("StructuredOutput", "text", 4)])
    assert extract.rescue_structured_output(tr) == ANSWER  # default schema is fit
    assert extract.rescue_structured_output(tr, "fit") == ANSWER
    assert extract.rescue_structured_output(tr, "batch") is None  # a fit answer is no batch answer
    assert extract.rescue_structured_output(extract.Transcript()) is None
    assert extract.STRUCTURED_TOOL == "StructuredOutput"
    assert io_spy.kinds("read_text") and all(kw.get("encoding") == "utf-8" for kw in io_spy.kinds("read_text"))


def test_read_transcript_hashes_the_file_bytes_of_its_one_read(tmp_path):
    import hashlib
    p = tmp_path / "t.jsonl"
    p.write_bytes(b'{"type": "result", "result": "a\xe2\x80\xa8b"}\r\n\xff\n')
    tr = extract.read_transcript(p)
    assert tr.sha256 == hashlib.sha256(p.read_bytes()).hexdigest()
    assert tr.result_text == "a b"      # U+2028 inside a line does not split it
