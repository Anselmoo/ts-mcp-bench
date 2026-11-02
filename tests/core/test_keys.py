"""Tests for the key file setting (tsbench.core.keys): one variable names the file, tsbench never reads it."""
from __future__ import annotations

import pathlib

from tsbench.core import keys


def test_the_default_key_file_is_in_the_tsbench_config_folder():
    assert keys.KEY_FILE_VAR == "TSBENCH_KEY_FILE"
    assert keys.DEFAULT_KEY_FILE == "~/.config/tsbench/env"
    assert keys.key_file_setting({}) == "~/.config/tsbench/env"


def test_the_variable_overrides_the_default_and_a_blank_value_does_not():
    assert keys.key_file_setting({"TSBENCH_KEY_FILE": "/srv/keys/model.env"}) == "/srv/keys/model.env"
    assert keys.key_file_setting({"TSBENCH_KEY_FILE": "  "}) == "~/.config/tsbench/env"


def test_the_shell_form_names_the_variable_and_the_default():
    assert keys.SHELL_KEY_FILE == "${TSBENCH_KEY_FILE:-$HOME/.config/tsbench/env}"


def test_key_file_path_expands_the_home_of_the_given_environment():
    env = {"HOME": "/h/op"}
    assert keys.key_file_path(env) == pathlib.Path("/h/op/.config/tsbench/env")
    assert keys.key_file_path({**env, "TSBENCH_KEY_FILE": "~/k/env"}) == pathlib.Path("/h/op/k/env")
    assert keys.key_file_path({**env, "TSBENCH_KEY_FILE": "/srv/k/env"}) == pathlib.Path("/srv/k/env")


def test_key_dir_entries_give_the_tilde_form_and_the_path_in_the_real_home():
    home = pathlib.Path("/real/home")
    assert keys.key_dir_entries({}, home) == ["~/.config/tsbench", "/real/home/.config/tsbench"]
    assert keys.key_dir_entries({"TSBENCH_KEY_FILE": "~/sec/model.env"}, home) == ["~/sec", "/real/home/sec"]


def test_key_dir_entries_of_an_absolute_path_in_the_real_home_add_the_tilde_form():
    env = {"TSBENCH_KEY_FILE": "/real/home/sec/model.env"}
    assert keys.key_dir_entries(env, pathlib.Path("/real/home")) == ["~/sec", "/real/home/sec"]


def test_key_dir_entries_of_a_path_outside_the_home_are_that_path_only():
    env = {"TSBENCH_KEY_FILE": "/srv/keys/model.env"}
    assert keys.key_dir_entries(env, pathlib.Path("/real/home")) == ["/srv/keys"]


def test_a_key_file_straight_in_the_home_denies_the_real_home_only():
    # "~" itself would be the child's own isolated home; the real home is denied anyway
    for value in ("~/model.env", "/real/home/model.env"):
        assert keys.key_dir_entries({"TSBENCH_KEY_FILE": value}, pathlib.Path("/real/home")) == ["/real/home"]


def test_key_file_status_stats_the_file_and_never_reads_it(tmp_path, monkeypatch):
    secret = tmp_path / "env"
    secret.write_text("TEST_ONLY_KEY=made-up-0001\n", encoding="utf-8")
    reads = []
    real_read = pathlib.Path.read_text
    monkeypatch.setattr(pathlib.Path, "read_text", lambda self, *a, **k: reads.append(self) or real_read(self, *a, **k))
    monkeypatch.setattr(pathlib.Path, "read_bytes", lambda self: reads.append(self) or b"")
    assert keys.key_file_exists({"TSBENCH_KEY_FILE": str(secret)}) is True
    assert keys.key_file_exists({"TSBENCH_KEY_FILE": str(tmp_path / "missing")}) is False
    assert reads == []


def test_display_name_hides_the_home_folder():
    env = {"HOME": "/h/op", "TSBENCH_KEY_FILE": "/h/op/sec/env"}
    assert keys.display_name(env) == "~/sec/env"
    assert keys.display_name({"HOME": "/h/op"}) == "~/.config/tsbench/env"
    assert keys.display_name({"HOME": "/h/op", "TSBENCH_KEY_FILE": "/srv/k/env"}) == "/srv/k/env"


def test_a_symlinked_key_folder_also_denies_its_real_path(tmp_path):
    home, target = tmp_path / "home", tmp_path / "store" / "keys"
    target.mkdir(parents=True)
    (home / ".config").mkdir(parents=True)
    (home / ".config" / "tsbench").symlink_to(target)
    assert keys.key_dir_entries({}, home) == ["~/.config/tsbench", str(home / ".config" / "tsbench"), str(target)]


def test_a_symlinked_key_file_also_denies_the_folder_of_its_target(tmp_path):
    home, target = tmp_path / "home", tmp_path / "store" / "model.env"
    target.parent.mkdir(parents=True)
    target.write_text("", encoding="utf-8")
    (home / "sec").mkdir(parents=True)
    (home / "sec" / "model.env").symlink_to(target)
    env = {"TSBENCH_KEY_FILE": "~/sec/model.env"}
    assert keys.key_dir_entries(env, home) == ["~/sec", str(home / "sec"), str(target.parent)]


def test_a_key_folder_without_symlinks_adds_no_entry(tmp_path):
    home = tmp_path / "home"
    (home / ".config" / "tsbench").mkdir(parents=True)
    assert keys.key_dir_entries({}, home) == ["~/.config/tsbench", str(home / ".config" / "tsbench")]
