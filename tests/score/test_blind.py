"""Tests for src/tsbench/score/blind.py: redaction and the blinded grading packets."""
from __future__ import annotations

import json
import random

from tsbench.score import blind


def _entries(n=12, text="Dq=1000"):
    return [{"path": f"m/{'BC'[i % 2]}/medium/T-{i:02d}-k{i}.jsonl", "model": f"modèl-{i}", "condition": "BC"[i % 2],
             "effort": "medium", "k": i, "task_id": f"T-{i:02d}", "prompt": f"prompt {i}",
             "answer_text": f"{text} #{i}"} for i in range(n)]


def test_default_seed_is_the_pilot_seed():
    e = _entries()
    assert blind.make_packets(e) == blind.make_packets(e, 20261024)
    assert blind.make_packets(e) != blind.make_packets(e, 20261025)
    assert blind.make_packets(e, 7) == blind.make_packets(e, 7)


def test_packets_are_sorted_by_path_then_shuffled_with_the_seed_then_numbered():
    e = _entries()
    for seed in (7, 20261024):
        expected = sorted(e, key=lambda x: x["path"])
        random.Random(seed).shuffle(expected)
        packets, key = blind.make_packets(list(reversed(e)), seed)
        assert [p["task_id"] for p in packets] == [x["task_id"] for x in expected]
        assert [p["packet_id"] for p in packets] == [f"G{i:04d}" for i in range(1, 13)]
        assert [key[p["packet_id"]]["path"] for p in packets] == [x["path"] for x in expected]
        # the order does not depend on the order the entries came in
        assert blind.make_packets(e, seed) == (packets, key)
    assert packets[0]["packet_id"] == "G0001" and packets[-1]["packet_id"] == "G0012"


def test_key_holds_the_cell_and_packets_hold_no_cell():
    e = _entries(3)
    packets, key = blind.make_packets(e, 1)
    assert set(key) == {"G0001", "G0002", "G0003"}
    by_task = {p["task_id"]: p["packet_id"] for p in packets}
    for x in e:
        assert key[by_task[x["task_id"]]] == {k: x[k] for k in ("path", "model", "condition", "effort", "k")}
    for p in packets:
        assert set(p) == {"packet_id", "task_id", "prompt", "answer_text"}
    assert packets[0]["prompt"].startswith("prompt ")
    assert blind.make_packets([], 1) == ([], {})


def test_the_caller_list_is_not_reordered():
    e = _entries(5)
    before = [x["path"] for x in e]
    blind.make_packets(e, 3)
    assert [x["path"] for x in e] == before


def test_make_packets_redacts_the_answer_text():
    e = _entries(1, text="used mcp__tanabesugano__ts_fit_spectrum, Claude Haiku-5 and ts_fit")
    [p], _ = blind.make_packets(e, 1)
    assert p["answer_text"] == "used [redacted] [redacted] [redacted] and [redacted] #0"
    assert blind.REDACTED == "[redacted]"


def test_redact_each_cue():
    r = blind.redact
    assert r("mcp__a_b-c d") == "[redacted] d"
    assert r("run ts_fit_x now") == "run [redacted] now" and r("ts_Fit") == "ts_Fit" and r("fits_fit") == "fits_fit"
    assert r("Tool calls and tool_call, TOOL-CALLS") == "[redacted] and [redacted], [redacted]"
    assert r("BASH, Mcp, tanabesugano") == "[redacted], [redacted], [redacted]"
    assert r("bashful mcps") == "bashful mcps"      # whole words only
    assert r("Claude-3.5 anthropic Opus") == "[redacted] [redacted] [redacted]"
    assert r("claude") == "[redacted]" and r("haiku") == "[redacted]" and r("sonnet") == "[redacted]"
    assert r("nothing to see: Dq = 1000") == "nothing to see: Dq = 1000"


def test_redact_condition_b_cues_and_bare_tool_names():
    r = blind.redact
    got = r("Solved the d3 matrix with numpy.linalg.eigh and scipy.optimize.least_squares in Python; fit_spectrum "
            "agreed, compute_point too. A script and Matplotlib and SymPy.")
    for word in ("numpy", "scipy", "Python", "fit_spectrum", "compute_point", "script", "Matplotlib", "SymPy"):
        assert word not in got, word
    assert r("Dq = 1000 and B = 800") == "Dq = 1000 and B = 800"
    assert r("descriptions pythonic") == "descriptions pythonic"      # whole words only


def test_redact_every_bare_tool_name_of_the_ts_mcp_server():
    import json
    import pathlib
    fixture = pathlib.Path(blind.__file__).parents[1] / "run" / "fake_cli_fixtures" / "init_C.json"
    tools = json.loads(fixture.read_text(encoding="utf-8"))["tools"]
    bare = [t.split("__")[-1].removeprefix("ts_") for t in tools if t.startswith("mcp__tanabesugano__")]
    assert len(bare) > 15
    for name in bare:
        if name in ("explain", "nephelauxetic"):      # ordinary words: only the prefixed form is a cue
            continue
        assert blind.redact(f"the {name} agreed") == "the [redacted] agreed", name
    assert blind.redact("a web_app and an explanation") == "a web_app and an explanation"   # not a tool name
    assert blind.redact("Spin_Crossover_App") == "[redacted]"                                 # any case


def test_redact_model_names_of_the_run_set():
    r = blind.redact
    text = "I am Qwen3 / Llama-3.3 / gpt-oss-120b / DeepSeek, qwen3.5-397b-a17b."
    assert r(text) == text      # nothing known about the run set: only the fixed cues apply
    got = r(text, models=["qwen3.5-397b-a17b", "gpt-oss-120b", "llama-3.3-70b", "deepseek-r1"])
    for word in ("Qwen", "Llama", "gpt", "DeepSeek", "397b"):
        assert word not in got, word
    assert r("Dq = 1000", models=["", "x"]) == "Dq = 1000"


def test_redact_family_names_of_the_real_gateway_ids():
    from tsbench.conditions import TEXT_ONLY_GATEWAY_MODELS
    r = blind.redact
    models = ["meta-llama-3.1-8b-instruct", "qwen3-coder-next", "deepseek-v4-flash-0731", "gpt-oss-120b"]
    got = r("I am Llama 3.1, a Qwen3 coder; DeepSeek V4 and gpt-oss agree.", models=models)
    for word in ("Llama", "Qwen", "DeepSeek", "gpt"):
        assert word not in got, word
    families = {"deepseek-v4-flash-0731": "DeepSeek", "meta-llama-3.1-8b-instruct": "Llama", "qwen3-coder-next": "Qwen",
                "qwen3-30b-a3b-instruct-2507": "Qwen", "qwen3.8-27b": "Qwen"}
    assert set(families) == set(TEXT_ONLY_GATEWAY_MODELS)
    for model, family in families.items():
        assert family not in r(f"I am {family} here", models=[model]), model
    # generic words of an id and ordinary words stay readable
    plain = "an instruct step, meta says hi, next flash"
    assert r(plain, models=models) == plain


def test_redact_keeps_the_ligand_field_term_nephelauxetic():
    r = blind.redact
    assert r("The nephelauxetic ratio beta = 0.8") == "The nephelauxetic ratio beta = 0.8"
    assert r("ts_nephelauxetic gave beta") == "[redacted] gave beta"


def test_make_packets_redacts_the_models_of_its_entries():
    e = _entries(2, text="Dq=1000 by Modèl-1")
    e[0]["model"], e[1]["model"] = "qwen3.5-397b", "gemma-3-27b"
    e[0]["answer_text"] = "I am Qwen3.5, not Gemma"
    e[1]["answer_text"] = "I am Gemma-3 not Qwen"
    packets, _ = blind.make_packets(e, 1)
    assert all("Qwen" not in p["answer_text"] and "Gemma" not in p["answer_text"] for p in packets)


def test_write_packets_files_and_content(tmp_path):
    e = _entries(4, text="café ñï")
    out = tmp_path / "deep" / "er" / "blind"
    pj, kj = blind.write_packets(e, out, 5)
    assert (pj, kj) == (out / "packets.jsonl", out / "key.json")
    packets, key = blind.make_packets(e, 5)
    text = pj.read_text(encoding="utf-8")
    assert text == "".join(json.dumps(p, ensure_ascii=False) + "\n" for p in packets)
    assert "café" in text and "\\u" not in text and text.endswith("\n")
    ktext = kj.read_text(encoding="utf-8")
    assert ktext == json.dumps({"seed": 5, "key": key}, indent=1, ensure_ascii=False)
    assert ktext.startswith('{\n "seed": 5,\n "key": {\n  "G0001": {') and "modèl-" in ktext and "\\u" not in ktext
    assert json.loads(ktext) == {"seed": 5, "key": key}
    blind.write_packets(e, out, 5)   # an existing folder is fine, and the files are overwritten
    assert pj.read_text(encoding="utf-8") == text


def test_write_packets_default_seed_is_recorded(tmp_path):
    e = _entries(3)
    _, kj = blind.write_packets(e, tmp_path / "b")
    assert json.loads(kj.read_text(encoding="utf-8"))["seed"] == 20261024
    pj = tmp_path / "b" / "packets.jsonl"
    assert [json.loads(x) for x in pj.read_text(encoding="utf-8").splitlines()] == blind.make_packets(e)[0]
    _, kj = blind.write_packets(e, str(tmp_path / "c"), 9)   # a plain string works as the folder
    assert json.loads(kj.read_text(encoding="utf-8"))["seed"] == 9


def test_write_packets_writes_utf8(tmp_path, io_spy):
    blind.write_packets(_entries(2), tmp_path / "b", 1)
    writes = io_spy.kinds("write_text")
    assert len(writes) == 2 and all(kw == {"encoding": "utf-8"} for kw in writes)
