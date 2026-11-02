"""Image harvest: *.png / *.svg of the run's cwd are copied to <stem>.artifacts/ and recorded in the sidecar."""
from __future__ import annotations

import hashlib
import json
import os

from tsbench.report import dashboard, harvested_images, images_html, render_dir
from tsbench.run import harvest, runner

HAIKU = "claude-haiku-5-5"
PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478"
                    "da63f8ffff3f0005fe02fea7d6e5ab0000000049454e44ae426082")


def test_harvest_copies_images_and_recomputes_sha(tmp_path):
    cwd, dest = tmp_path / "cwd", tmp_path / "x.artifacts"
    cwd.mkdir()
    (cwd / "diagram.png").write_bytes(PNG)
    (cwd / "plot.SVG").write_text("<svg/>", encoding="utf-8")
    (cwd / "notes.txt").write_text("not an image", encoding="utf-8")
    (cwd / ".hidden.png").write_bytes(PNG)
    got = runner.harvest_artifacts(cwd, dest)
    assert got == [{"name": "diagram.png", "sha256": hashlib.sha256(PNG).hexdigest()},
                   {"name": "plot.SVG", "sha256": hashlib.sha256(b"<svg/>").hexdigest()}]
    assert (dest / "diagram.png").read_bytes() == PNG and not (dest / "notes.txt").exists()


def test_harvest_never_follows_symlinks_and_skips_subdirs_and_big_files(tmp_path, monkeypatch):
    secret = tmp_path / "secret.png"
    secret.write_bytes(b"SECRET")
    cwd, dest = tmp_path / "cwd", tmp_path / "a"
    cwd.mkdir()
    os.symlink(secret, cwd / "link.png")
    os.symlink(tmp_path, cwd / "dir.png")
    (cwd / "sub").mkdir()
    (cwd / "sub" / "deep.png").write_bytes(PNG)
    (cwd / "d.png").mkdir()
    monkeypatch.setattr(harvest, "ARTIFACT_MAX_BYTES", 10)
    (cwd / "big.png").write_bytes(b"x" * 11)
    (cwd / "ok.png").write_bytes(b"x" * 10)
    got = runner.harvest_artifacts(cwd, dest)
    assert [g["name"] for g in got] == ["ok.png"]
    assert sorted(p.name for p in dest.iterdir()) == ["ok.png"]


def test_harvest_without_images_creates_nothing_and_missing_cwd_is_fine(tmp_path):
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    assert runner.harvest_artifacts(cwd, tmp_path / "d") == [] and not (tmp_path / "d").exists()
    assert runner.harvest_artifacts(tmp_path / "gone", tmp_path / "d") == []


def test_harvest_caps_the_number_of_files(tmp_path):
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    for i in range(runner.ARTIFACT_MAX_FILES + 5):
        (cwd / f"f{i:02d}.png").write_bytes(PNG)
    assert len(runner.harvest_artifacts(cwd, tmp_path / "d")) == runner.ARTIFACT_MAX_FILES


def test_image_sha_match():
    arts = [{"name": "a.png", "sha256": "ab" * 32}]
    assert runner.image_sha_match({"image_sha256": ("AB" * 32)}, arts) is True
    assert runner.image_sha_match({"image_sha256": "cd" * 32}, arts) is False
    assert runner.image_sha_match({"image_sha256": None}, arts) is None
    assert runner.image_sha_match({}, arts) is None and runner.image_sha_match(None, arts) is None


def dry_diagram_run(tmp_path):
    out = tmp_path / "runs"
    rc = runner.main(["--split", "pilot", "--models", HAIKU, "--conditions", "A", "--effort", "medium", "--k", "1",
                      "--budget-usd", "10", "--out", str(out), "--dry-run", "--limit", "44"])
    assert rc == 0
    return out


def test_dry_run_records_artifacts_and_sha_match_in_the_sidecar(tmp_path):
    out = dry_diagram_run(tmp_path)
    tp = out / HAIKU / "A" / "medium" / "P-diagram-01-k1.jsonl"
    meta = json.loads(tp.with_name("P-diagram-01-k1.meta.json").read_text(encoding="utf-8"))
    sha = hashlib.sha256(PNG).hexdigest()
    assert meta["artifacts"] == [{"name": "diagram.png", "sha256": sha}] and meta["image_sha_match"] is True
    assert (tp.with_name("P-diagram-01-k1.artifacts") / "diagram.png").read_bytes() == PNG
    other = json.loads((out / HAIKU / "A" / "medium" / "P-closed_form-01-k1.meta.json").read_text(encoding="utf-8"))
    assert other["artifacts"] == [] and other["image_sha_match"] is None
    assert not (out / HAIKU / "A" / "medium" / "P-closed_form-01-k1.artifacts").exists()


def test_views_and_dashboard_embed_the_image_as_a_data_uri(tmp_path):
    out = dry_diagram_run(tmp_path)
    render_dir(out, "pilot")
    view = (out / "views" / HAIKU / "A" / "medium" / "P-diagram-01-k1.html").read_text(encoding="utf-8")
    assert "data:image/png;base64," in view and "matches a harvested file" in view
    plain = (out / "views" / HAIKU / "A" / "medium" / "P-closed_form-01-k1.html").read_text(encoding="utf-8")
    assert "data:image" not in plain
    dash = tmp_path / "report.html"
    data = dashboard.collect([out], dash, dashboard.load_pilot_tasks())
    html = dashboard.build_html(data)
    assert "Images saved by the models" in html and "data:image/png;base64," in html


def test_svg_is_embedded_through_img_never_inlined(tmp_path):
    tp = tmp_path / "r-k1.jsonl"
    folder = tmp_path / "r-k1.artifacts"
    folder.mkdir()
    evil = b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>"
    (folder / "d.svg").write_bytes(evil)
    meta = {"artifacts": [{"name": "d.svg", "sha256": hashlib.sha256(evil).hexdigest()},
                          {"name": "../escape.png", "sha256": "0" * 64}]}
    imgs = harvested_images(tp, meta)
    assert [i["name"] for i in imgs] == ["d.svg"] and imgs[0]["sha_ok"]
    html = images_html(imgs)
    assert html.count("<img ") == 1 and "<script" not in html and "data:image/svg+xml;base64," in html
    (folder / "d.svg").write_bytes(b"changed")
    assert harvested_images(tp, meta)[0]["sha_ok"] is False


# ------------------------------------------------------------------ exact values and the races
def test_harvest_skips_a_fifo_that_looks_like_an_image(tmp_path):
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    os.mkfifo(cwd / "pipe.png")
    (cwd / "ok.png").write_bytes(PNG)
    got = harvest.harvest_artifacts(cwd, tmp_path / "d")
    assert [g["name"] for g in got] == ["ok.png"] and sorted(p.name for p in (tmp_path / "d").iterdir()) == ["ok.png"]


def test_harvest_opens_read_only_without_following_symlinks_or_blocking(tmp_path, monkeypatch):
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    (cwd / "a.png").write_bytes(PNG)
    flags = []
    real_open = os.open

    def spy(path, fl, *a, **kw):
        flags.append(fl)
        return real_open(path, fl, *a, **kw)

    monkeypatch.setattr(harvest.os, "open", spy)
    assert len(harvest.harvest_artifacts(cwd, tmp_path / "d")) == 1
    assert flags == [os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK]


def test_harvest_survives_a_swap_between_lstat_and_open_and_goes_on(tmp_path, monkeypatch):
    """A symlink put in place after lstat is refused by O_NOFOLLOW; the next file is still taken."""
    secret = tmp_path / "secret.bin"
    secret.write_bytes(b"SECRET")
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    os.symlink(secret, cwd / "a-swapped.png")
    (cwd / "b.png").write_bytes(PNG)
    real_lstat = os.lstat
    monkeypatch.setattr(harvest.os, "lstat", lambda p: real_lstat(secret) if str(p).endswith("a-swapped.png")
                        else real_lstat(p))
    got = harvest.harvest_artifacts(cwd, tmp_path / "d")
    assert got == [{"name": "b.png", "sha256": hashlib.sha256(PNG).hexdigest()}]
    assert not (tmp_path / "d" / "a-swapped.png").exists()


def test_harvest_skips_a_file_that_grew_past_the_limit_after_lstat_and_goes_on(tmp_path, monkeypatch):
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    (cwd / "a-grown.png").write_bytes(b"x" * 11)
    (cwd / "b.png").write_bytes(b"y" * 10)
    monkeypatch.setattr(harvest, "ARTIFACT_MAX_BYTES", 10)
    real_lstat = os.lstat

    class Small:
        st_mode = real_lstat(cwd / "b.png").st_mode
        st_size = 3

    monkeypatch.setattr(harvest.os, "lstat", lambda p: Small if str(p).endswith("a-grown.png") else real_lstat(p))
    got = harvest.harvest_artifacts(cwd, tmp_path / "d")
    assert got == [{"name": "b.png", "sha256": hashlib.sha256(b"y" * 10).hexdigest()}]


def test_harvest_keeps_the_whole_file_at_the_size_limit_and_creates_nested_dest(tmp_path, monkeypatch):
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.setattr(harvest, "ARTIFACT_MAX_BYTES", 64)
    data = bytes(range(64))
    (cwd / "full.png").write_bytes(data)
    (cwd / "second.svg").write_bytes(b"<svg/>")
    dest = tmp_path / "deep" / "er" / "run.artifacts"
    got = harvest.harvest_artifacts(cwd, dest)
    assert got == [{"name": "full.png", "sha256": hashlib.sha256(data).hexdigest()},
                   {"name": "second.svg", "sha256": hashlib.sha256(b"<svg/>").hexdigest()}]
    assert (dest / "full.png").read_bytes() == data  # not cut one byte short
