"""Tests for tsbench.score.run_sets: generic discovery of run sets (folders with MANIFEST.json)."""
import json

from tsbench.score.run_sets import discover_run_sets


def test_discover_finds_nested_run_sets_with_titles(tmp_path):
    for rel in ("functional-test/qwen", "functional-test/gemma", "other/x/deep"):
        (tmp_path / rel).mkdir(parents=True)
        (tmp_path / rel / "MANIFEST.json").write_text("{}", encoding="utf-8")
    (tmp_path / "functional-test/qwen/run_set.json").write_text(json.dumps({"title": "Qwen, A/B/C, k = 1"}),
                                                                encoding="utf-8")
    (tmp_path / ".hidden/y").mkdir(parents=True)
    (tmp_path / ".hidden/y/MANIFEST.json").write_text("{}", encoding="utf-8")
    sets = discover_run_sets(tmp_path)
    assert [s.name for s in sets] == ["functional-test/gemma", "functional-test/qwen", "other/x/deep"]
    assert sets[1].title == "Qwen, A/B/C, k = 1" and sets[0].title == "functional-test/gemma"
    assert discover_run_sets(tmp_path / "functional-test" / "qwen")[0].name == "qwen"


def test_run_sets_in_takes_folders_in_order_and_falls_back_to_a_folder_without_manifest(tmp_path):
    from tsbench.score.run_sets import run_sets_in
    for rel in ("a/runs", "b/runs"):
        (tmp_path / rel).mkdir(parents=True)
        (tmp_path / rel / "MANIFEST.json").write_text("{}", encoding="utf-8")
    loose = tmp_path / "loose" / "m" / "A" / "medium"
    loose.mkdir(parents=True)
    (loose / "P-x-01-k1.jsonl").write_text("{}\n", encoding="utf-8")
    sets = run_sets_in([tmp_path / "a" / "runs", tmp_path / "b" / "runs", tmp_path / "loose", tmp_path / "a" / "runs",
                        tmp_path / "missing", tmp_path / "a"])
    assert [s.name for s in sets] == ["runs", "b/runs", "loose"]
    assert sets[2].path == tmp_path / "loose"


def _manifest(path):
    path.mkdir(parents=True, exist_ok=True)
    (path / "MANIFEST.json").write_text("{}", encoding="utf-8")
    return path


def test_discover_depth_limit_is_four_folders_below_the_root_inclusive(tmp_path):
    for rel in ("a/b/c/d", "a/b/c/d/e", "x"):
        _manifest(tmp_path / rel)
    assert [s.name for s in discover_run_sets(tmp_path)] == ["a/b/c/d", "x"]
    assert [s.name for s in discover_run_sets(tmp_path, max_depth=5)] == ["a/b/c/d", "a/b/c/d/e", "x"]
    assert [s.name for s in discover_run_sets(tmp_path, max_depth=0)] == []
    assert [s.name for s in discover_run_sets(tmp_path, max_depth=1)] == ["x"]


def test_discover_the_root_itself_is_named_after_its_folder(tmp_path):
    root = _manifest(tmp_path / "myruns")
    [rs] = discover_run_sets(root)
    assert (rs.name, rs.title, rs.path) == ("myruns", "myruns", root)
    [rs] = discover_run_sets(str(root))   # a plain string works as well
    assert rs.path == root
    (root / "run_set.json").write_text(json.dumps({"title": "T"}), encoding="utf-8")
    assert discover_run_sets(root)[0].title == "T" and discover_run_sets(root)[0].name == "myruns"


def test_discover_titles_fall_back_to_the_name_when_the_description_is_unusable(tmp_path):
    for i, text in enumerate(["{not json", json.dumps({"title": ""}), json.dumps({"other": 1}),
                              json.dumps({"title": None}), json.dumps({"title": 5})]):
        d = _manifest(tmp_path / f"s{i}")
        (d / "run_set.json").write_text(text, encoding="utf-8")
    titles = {s.name: s.title for s in discover_run_sets(tmp_path)}
    assert titles == {"s0": "s0", "s1": "s1", "s2": "s2", "s3": "s3", "s4": "5"}


def test_discover_reads_the_description_as_utf8(tmp_path, io_spy):
    d = _manifest(tmp_path / "s")
    (d / "run_set.json").write_text(json.dumps({"title": "Café"}, ensure_ascii=False), encoding="utf-8")
    assert discover_run_sets(tmp_path)[0].title == "Café"
    reads = io_spy.kinds("read_text")
    assert reads and all(kw == {"encoding": "utf-8"} for kw in reads)


def test_run_sets_in_lists_a_set_found_again_once_and_goes_on(tmp_path):
    from tsbench.score.run_sets import run_sets_in
    _manifest(tmp_path / "a" / "runs")
    _manifest(tmp_path / "a" / "zzz")
    sets = run_sets_in([tmp_path / "a" / "runs", tmp_path / "a"])
    assert [s.name for s in sets] == ["runs", "zzz"]    # runs was seen already; zzz comes after it in the folder


def test_run_sets_in_names_a_clash_after_the_folder_it_was_found_in(tmp_path):
    from tsbench.score.run_sets import RunSet, run_sets_in
    _manifest(tmp_path / "a" / "runs")
    _manifest(tmp_path / "b" / "runs")
    _manifest(tmp_path / "c" / "runs")
    (tmp_path / "c" / "runs" / "run_set.json").write_text(json.dumps({"title": "Own title"}), encoding="utf-8")
    sets = run_sets_in([tmp_path / "a" / "runs", tmp_path / "b", tmp_path / "c", tmp_path / "c" / "runs"])
    assert sets == [RunSet("runs", "runs", tmp_path / "a" / "runs"),
                    RunSet("b/runs", "b/runs", tmp_path / "b" / "runs"),      # no own title: the new name
                    RunSet("c/runs", "Own title", tmp_path / "c" / "runs")]   # an own title is kept


def test_run_sets_in_clash_of_a_folder_given_directly(tmp_path):
    from tsbench.score.run_sets import RunSet, run_sets_in
    _manifest(tmp_path / "a" / "runs")
    _manifest(tmp_path / "b" / "runs")
    sets = run_sets_in([tmp_path / "a" / "runs", tmp_path / "b" / "runs"])
    assert sets[1] == RunSet("b/runs", "b/runs", tmp_path / "b" / "runs")


def test_run_sets_in_folder_with_transcripts_only(tmp_path):
    from tsbench.score.run_sets import RunSet, run_sets_in
    loose = tmp_path / "loose"
    (loose / "m" / "A" / "medium").mkdir(parents=True)
    (loose / "m" / "A" / "medium" / "P-x-01-k1.jsonl").write_text("{}\n", encoding="utf-8")
    assert run_sets_in([loose]) == [RunSet("loose", "loose", loose)]
    empty = tmp_path / "empty"
    empty.mkdir()
    assert run_sets_in([empty, tmp_path / "missing"]) == []
    assert run_sets_in([]) == []
