"""tools/ci/mutation_report.py: one shard's mutmut results to JSON, all shards to one Markdown summary."""
import importlib.util
import json
import pathlib

import pytest

SPEC = importlib.util.spec_from_file_location(
    "mutation_report", pathlib.Path(__file__).resolve().parents[2] / "tools" / "ci" / "mutation_report.py")
mutation_report = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mutation_report)

RESULTS = """\
    tsbench.score.numeric.x_parse__mutmut_1: killed
    tsbench.score.numeric.x_parse__mutmut_2: killed
    tsbench.score.numeric.x_parse__mutmut_3: survived
    tsbench.score.extract.x_answer__mutmut_1: killed
    tsbench.score.extract.x_answer__mutmut_2: timeout
    tsbench.score.extract.x_answer__mutmut_3: no tests
    tsbench.score.extract.xǁParser.read__mutmut_1: not checked
"""


def test_shard_counts_scores_and_lists_survivors(tmp_path):
    results = tmp_path / "results.txt"
    results.write_text(RESULTS, encoding="utf-8")
    doc = mutation_report.shard("score", results)
    assert doc["counts"] == {"killed": 3, "survived": 1, "timeout": 1, "no tests": 1, "not checked": 1}
    assert doc["total"] == 7
    assert doc["score_pct"] == 75.0  # killed / (killed + survived)
    assert doc["survivors"] == [{"mutant": "tsbench.score.numeric.x_parse__mutmut_3",
                                 "module": "tsbench.score.numeric"}]
    assert doc["per_module"]["tsbench.score.extract"] == {"killed": 1, "timeout": 1, "no tests": 1, "not checked": 1}


def test_class_method_mutants_count_for_their_module(tmp_path):
    results = tmp_path / "results.txt"
    results.write_text("    tsbench.run.runner.xǁSession.close__mutmut_4: survived\n", encoding="utf-8")
    assert mutation_report.shard("run", results)["survivors"][0]["module"] == "tsbench.run.runner"


def test_merge_writes_one_table_and_flags_missing_shards(tmp_path):
    a = {"name": "score", "total": 6, "counts": {"killed": 3, "survived": 1, "no tests": 2}, "score_pct": 75.0,
         "survivors": [], "per_module": {}}
    (tmp_path / "score.json").write_text(json.dumps(a), encoding="utf-8")
    md = mutation_report.merge([tmp_path / "score.json"], expected=["score", "stats"])
    assert "| score | 6 | 3 | 1 | 2 | 75.0 % |" in md  # mutants without a covering test are shown, not scored
    assert "stats" in md and "no result" in md
    assert "**total**" in md


def test_score_of_an_empty_shard_is_not_a_division_by_zero(tmp_path):
    results = tmp_path / "results.txt"
    results.write_text("", encoding="utf-8")
    assert mutation_report.shard("empty", results)["score_pct"] is None


@pytest.mark.parametrize("only, names", [("", ["a", "b"]), ("b", ["b"]), ("a, b", ["a", "b"])])
def test_matrix_filter(only, names):
    shards = [{"name": "a", "source_paths": ["x"], "test_paths": ["y"]},
              {"name": "b", "source_paths": ["x"], "test_paths": ["y"]}]
    assert [m["name"] for m in mutation_report.matrix(shards, only)["include"]] == names


def test_matrix_rejects_an_unknown_shard():
    with pytest.raises(SystemExit):
        mutation_report.matrix([{"name": "a", "source_paths": ["x"], "test_paths": ["y"]}], "nope")
