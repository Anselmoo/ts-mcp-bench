"""Tests for src/tsbench/report/page.py: the share row and the DOI link."""
from __future__ import annotations

import pytest

from tsbench.core import intervals
from tsbench.report import base, page

COUNTS = {"correct": 6, "wrong": 6}


def test_a_share_row_has_the_task_clustered_bootstrap_interval():
    """Three tasks x k = 3 runs: the runs of a task agree, so the interval over runs would be far too narrow."""
    pairs = [(3, 3), (3, 3), (0, 3), (0, 3)]
    row = page.rate_row("C", "C", {"correct": 6, "wrong": 6}, 12, 12, pairs)
    lo, hi = intervals.cluster_bootstrap([3, 3, 0, 0], [3, 3, 3, 3])
    assert row["lo"] == pytest.approx(100 * lo) and row["hi"] == pytest.approx(100 * hi)
    p = 50.0
    wilson_lo = 100 * intervals.wilson(6, 12)[0]
    assert row["lo"] < wilson_lo < p < 100 - wilson_lo < row["hi"]       # clearly wider than Wilson over the runs
    assert "95 % interval" in row["tip"] and "tasks resampled" in row["tip"]


def test_a_share_row_without_evaluable_runs_has_no_interval():
    row = page.rate_row("A", "A", {}, 0, 3, [])
    assert row["p"] is None and row["lo"] is None and row["hi"] is None


def test_task_pairs_group_the_evaluable_runs_by_task():
    assert page.task_pairs([("t1", True), ("t2", False), ("t1", False), ("t1", True)]) == [(2, 3), (0, 1)]
    assert page.task_pairs([]) == []


def test_task_pairs_are_sorted_by_task_id_so_every_page_draws_the_same_bootstrap():
    runs = [("t9", True), ("t2", False), ("t9", True), ("t5", True), ("t2", True), ("t7", False), ("t1", False),
            ("t1", False), ("t5", False), ("t8", True), ("t3", True), ("t3", False)]
    shuffled = [runs[i] for i in (7, 3, 11, 0, 5, 9, 1, 10, 2, 8, 4, 6)]
    assert page.task_pairs(runs) == page.task_pairs(shuffled)
    assert page.share_interval(page.task_pairs(shuffled)) == page.share_interval(page.task_pairs(runs))
    rows = [{"task_id": t, "correct": "True" if ok else "False"} for t, ok in shuffled]
    s = base.share(rows)
    assert s is not None
    assert page.share_interval(page.task_pairs(shuffled)) == (100 * s["lo"], 100 * s["hi"])


def test_doi_href_encodes_the_characters_that_would_cut_the_url():
    assert page.doi_href("10.1021/acs.jchemed.2c00885") == "https://doi.org/10.1021/acs.jchemed.2c00885"
    assert page.doi_href("10.1000/abc#def?x=1%41") == "https://doi.org/10.1000/abc%23def%3Fx%3D1%2541"
    assert page.doi_href("10.1002/(SICI)1097-4555(199708)28:8<593::AID-JRS157>3.0.CO;2-#") == (
        "https://doi.org/10.1002/(SICI)1097-4555(199708)28:8%3C593::AID-JRS157%3E3.0.CO;2-%23")


def test_doi_href_is_a_template_global():
    assert page.ENV.from_string("{{ doi_href(d) }}").render(d="10.1/a#b") == "https://doi.org/10.1/a%23b"


def test_templates_round_a_half_up_through_the_fixed_filter():
    # a half rounds up in every template: 62.5 prints 63 and 37.5 prints 38
    assert page.ENV.from_string("{{ (100 * x) | fixed(0) }}–{{ y | fixed(0) }}").render(x=0.625, y=37.5) == "63–38"
    assert page.ENV.from_string("{{ x | fixed(1) }}").render(x=12.25) == "12.3"


def test_no_template_formats_a_number_with_a_half_to_even_format():
    names = [n for n in page.ENV.list_templates() if n.endswith(".j2")]
    hits = [n for n in names if "| format" in page._LOADER.get_source(page.ENV, n)[0].replace("|format", "| format")]
    assert hits == []
