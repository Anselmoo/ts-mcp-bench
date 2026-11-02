"""The provenance tracer (tsbench.core.trace): one JSON record per process with the command, the tsbench.* call edges
and the file events, each with the nearest tsbench caller and sha256. No environment value, no file content and no home
path enters a record.

Most tests run the traced code in a fresh interpreter: an audit hook cannot be removed again, so the pytest process
stays untraced except for the one start/stop test."""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from tsbench.core import resource
from tsbench.run import env as run_env

ENV_VAR = "TSBENCH_TRACE"
ENV_SECRET = "ENV-SENTINEL-91c2"
POPEN_SECRET = "ENV-SENTINEL-POPEN-44d0"
CONTENT_SECRET = "CONTENT-SENTINEL-7f3a"
HOME_SEGMENT = re.compile(r"/(?:home|Users)/[^/\s\"']+/")


@pytest.fixture
def trace():
    return importlib.import_module("tsbench.core.trace")


def sha(data: bytes | str) -> str:
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


def child_env(**extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k != ENV_VAR}
    env.update(extra)
    return env


def records(directory: Path) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(directory).glob("*.trace.json"))]


def python(code: str, *args, env: dict[str, str] | None = None, stdin: str | None = None, cwd: Path | None = None):
    return subprocess.run([sys.executable, "-c", textwrap.dedent(code), *map(str, args)], env=env or child_env(),
                          input=stdin, capture_output=True, text=True, timeout=300, cwd=cwd, encoding="utf-8")


def edges(record: dict) -> set[tuple[str, str | None]]:
    return {(c["function"], c["caller"]) for c in record["calls"]}


def events(record: dict, kind: str, suffix: str) -> list[dict]:
    return [e for e in record["files"] if e["event"] == kind and str(e.get("path", "")).endswith(suffix)]


# ---------------------------------------------------------------- one traced program, many checks
PROGRAM = """
    import os, pathlib, subprocess, sys
    from tsbench.core import trace
    root, tdir = pathlib.Path(sys.argv[1]), sys.argv[2]
    assert trace.start(tdir) is not None
    from tsbench.report import summary
    with open(root / "a.txt", encoding="utf-8") as f:
        f.read()
    with open(root / "a.txt", "w", encoding="utf-8") as f:
        f.write("new")
    with open(root / "b.tmp", "w", encoding="utf-8") as f:
        f.write("final")
    os.replace(root / "b.tmp", root / "b.txt")
    os.mkdir(root / "d")
    (root / "gone.txt").write_text("x", encoding="utf-8")
    os.remove(root / "gone.txt")
    fd = os.open(root / "d", os.O_RDONLY)  # tsbench fsyncs directories; the tracer must not choke on it
    os.fsync(fd)
    os.close(fd)
    with open(pathlib.Path.home() / "h.txt", encoding="utf-8") as f:
        f.read()
    subprocess.run([sys.executable, "-c", "pass"], env={"TSBENCH_TEST_SECRET": os.environ["POPEN_VALUE"]},
                   check=True)
    step = {"name": "score", "command": "tsbench score", "rc": 0, "log": "logs/score.log", "outputs": []}
    summary.context([step], root, root / "S.html", "m", when="w")
    def local_helper():
        return 1
    local_helper()
    print("done")
"""


@pytest.fixture(scope="module")
def traced(tmp_path_factory):
    root = tmp_path_factory.mktemp("traced")
    tdir = root / "trace"
    home = root / "home"
    home.mkdir()
    (home / "h.txt").write_text("home file", encoding="utf-8")
    (root / "a.txt").write_text("old", encoding="utf-8")
    probe = root / "sandbox-probe" / "sandbox_probe.json"
    probe.parent.mkdir()
    probe.write_text(json.dumps({"verdict": "pass", "note": CONTENT_SECRET}), encoding="utf-8")
    proc = python(PROGRAM, root, tdir,
                  env=child_env(HOME=str(home), TSBENCH_TEST_SECRET=ENV_SECRET, POPEN_VALUE=POPEN_SECRET))
    recs = records(tdir)
    text = "".join(p.read_text(encoding="utf-8") for p in tdir.glob("*.trace.json"))
    return {"root": root, "tdir": tdir, "home": home, "probe": probe, "proc": proc, "records": recs, "text": text}


def test_the_traced_program_runs_unchanged_and_writes_one_record(traced):
    assert traced["proc"].returncode == 0, traced["proc"].stderr
    assert traced["proc"].stdout.strip() == "done"
    assert len(traced["records"]) == 1


def test_the_record_names_the_process_and_its_command(traced):
    (rec,) = traced["records"]
    assert rec["schema"] == "tsbench.trace/1"
    assert isinstance(rec["pid"], int) and rec["ppid"] == os.getpid()
    assert isinstance(rec["argv"], list) and isinstance(rec["command"], str) and rec["command"]
    assert isinstance(rec["start"], float) and rec["start"] <= rec["end"]
    assert "exit_code" in rec and "cwd" in rec


def test_calls_are_tsbench_functions_with_their_tsbench_caller(traced):
    (rec,) = traced["records"]
    got = edges(rec)
    assert ("tsbench.report.summary:context", None) in got
    assert ("tsbench.report.summary:_verdict", "tsbench.report.summary:context") in got
    assert ("tsbench.report.summary:_probe", "tsbench.report.summary:context") in got
    assert all(c["count"] >= 1 for c in rec["calls"])
    assert all(c["function"].startswith("tsbench.") for c in rec["calls"]), "only code under src/tsbench is traced"
    assert not any(c["function"].startswith("tsbench.core.trace") for c in rec["calls"]), "the tracer skips itself"
    assert "local_helper" not in traced["text"]


def test_a_read_has_its_sha256_at_read_and_at_process_end(traced):
    (rec,) = traced["records"]
    (read,) = [e for e in events(rec, "open", "/a.txt") if e["mode"].startswith("r")]
    assert read["sha256_at_read"] == sha("old")
    assert read["sha256_at_end"] == sha("new")


def test_a_write_has_its_sha256_at_process_end(traced):
    (rec,) = traced["records"]
    (write,) = [e for e in events(rec, "open", "/a.txt") if "w" in e["mode"]]
    assert write.get("sha256_at_read") is None
    assert write["sha256_at_end"] == sha("new")


def test_rename_and_replace_record_source_target_and_the_final_hash(traced):
    (rec,) = traced["records"]
    (move,) = events(rec, "rename", "/b.tmp")
    assert move["target"].endswith("/b.txt")
    assert move["sha256_at_end"] == sha("final")


def test_mkdir_remove_and_popen_are_recorded(traced):
    (rec,) = traced["records"]
    assert events(rec, "mkdir", "/d")
    assert events(rec, "remove", "/gone.txt")
    popens = [e for e in rec["files"] if e["event"] == "popen"]
    assert popens and "-c" in popens[0]["argv"]


def test_a_directory_opened_for_fsync_has_no_hash_and_does_not_break_the_record(traced):
    (rec,) = traced["records"]
    for e in events(rec, "open", "/d"):
        assert e.get("sha256_at_read") is None and e.get("sha256_at_end") is None


def test_file_events_carry_the_nearest_tsbench_caller(traced):
    (rec,) = traced["records"]
    (probe,) = events(rec, "open", "sandbox-probe/sandbox_probe.json")
    assert probe["caller"].startswith("tsbench.report.summary:_probe")
    assert probe["sha256_at_read"] == sha(traced["probe"].read_bytes())
    (plain,) = [e for e in events(rec, "open", "/a.txt") if e["mode"].startswith("r")]
    assert plain["caller"] is None, "a read from a non-tsbench frame has no tsbench caller"


def test_no_environment_value_and_no_file_content_enter_the_record(traced):
    text = traced["text"]
    assert traced["records"], "the check is not vacuous"
    assert ENV_SECRET not in text and POPEN_SECRET not in text
    assert os.environ["PATH"] not in text
    assert CONTENT_SECRET not in text and "home file" not in text and '"final"' not in text


def test_home_paths_are_redacted(traced):
    (rec,) = traced["records"]
    assert str(traced["home"]) not in traced["text"]
    assert any(e.get("path") == "~/h.txt" for e in rec["files"])
    assert not HOME_SEGMENT.search(traced["text"]), "no /home/<name>/ or /Users/<name>/ in a record"


def test_interpreter_noise_and_the_trace_folder_itself_are_not_recorded(traced):
    (rec,) = traced["records"]
    for e in rec["files"]:
        path = str(e.get("path", ""))
        assert "__pycache__" not in path and not path.endswith(".pyc")
        assert not path.startswith(str(traced["tdir"])) and "trace.json" not in path


# ---------------------------------------------------------------- redaction
def test_redact_replaces_the_own_home_and_any_other_user_home(trace, monkeypatch, tmp_path):
    me = tmp_path / "me"
    monkeypatch.setenv("HOME", str(me))
    assert trace.redact(str(me / "a" / "b.txt")) == "~/a/b.txt"
    assert trace.redact(str(me)) == "~"
    assert trace.redact("/home/alice/x/y") == "~/x/y"
    assert trace.redact("/Users/bob/z") == "~/z"
    assert trace.redact("--out=/home/alice/run") == "--out=~/run"
    assert trace.redact("/tmp/x") == "/tmp/x"
    assert trace.redact("/home") == "/home"
    # a doubled slash names the same folder, so a file URI or `//home/x` is redacted, too
    assert trace.redact(f"file://{me}/a") == "file://~/a"
    assert trace.redact("file:///home/alice/x") == "file://~/x"
    assert "alice" not in trace.redact("//home/alice/x")
    assert trace.redact("/data/home/alice/x") == "/data/home/alice/x", "a home folder deeper in a path stays"


# ---------------------------------------------------------------- secret-like files
SECRET_PROGRAM = """
    import pathlib, sys
    from tsbench.core import trace
    root, tdir = pathlib.Path(sys.argv[1]), sys.argv[2]
    trace.start(tdir)
    for name in ("home/.config/tsbench/env", "keys/model.cfg", "proj/.env", "proj/.env.local", "proj/seed/s.json",
                 "proj/plain.txt"):
        with open(root / name, encoding="utf-8") as f:
            f.read()
"""


def test_secret_like_files_are_listed_without_a_hash(tmp_path):
    """The default key file, the key file named by TSBENCH_KEY_FILE, a .env file and a seed/ folder keep their path,
    but no hash of their content enters the record."""
    home = tmp_path / "home"
    files = {"home/.config/tsbench/env": "TEST_ONLY_KEY=made-up-0001", "keys/model.cfg": "TEST_ONLY_KEY=made-up-0005",
             "proj/.env": "A=made-up-0002", "proj/.env.local": "B=made-up-0003",
             "proj/seed/s.json": '{"seed": "made-up-0004"}', "proj/plain.txt": "plain"}
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text, encoding="utf-8")
    tdir = tmp_path / "t"
    key_file = str(tmp_path / "keys" / "model.cfg")
    proc = python(SECRET_PROGRAM, tmp_path, tdir, env=child_env(HOME=str(home), TSBENCH_KEY_FILE=key_file))
    assert proc.returncode == 0, proc.stderr
    (rec,) = records(tdir)
    text = "".join(p.read_text(encoding="utf-8") for p in tdir.glob("*.trace.json"))
    for name, content in files.items():
        (event,) = events(rec, "open", name.removeprefix("home/"))
        if name.endswith("plain.txt"):
            assert event["sha256_at_read"] == sha(content), "the check is not vacuous"
            continue
        assert event["sha256_at_read"] is None and event["sha256_at_end"] is None, name
        assert sha(content) not in text and "made-up" not in text


# ---------------------------------------------------------------- switching on and off
def test_start_if_requested_does_nothing_without_the_variable(trace, monkeypatch, tmp_path):
    monkeypatch.delenv(ENV_VAR, raising=False)
    assert trace.start_if_requested() is None
    monkeypatch.setenv(ENV_VAR, "")
    assert trace.start_if_requested() is None


def test_start_and_stop_in_process_write_the_record_and_free_the_monitoring_slot(trace, monkeypatch, tmp_path):
    from tsbench.report import summary

    before = {i: sys.monitoring.get_tool(i) for i in range(6)}
    steps = tmp_path / "steps.jsonl"
    steps.write_text('{"name": "x", "rc": 0}\n', encoding="utf-8")
    monkeypatch.setenv(ENV_VAR, str(tmp_path / "t"))
    path = trace.start_if_requested()
    try:
        assert trace.start(tmp_path / "other") == path, "a second start keeps the running tracer"
        summary.load_steps(steps)
    finally:
        written = trace.stop()
    assert written == path and path.is_file() and path.name.endswith(".trace.json")
    assert {i: sys.monitoring.get_tool(i) for i in range(6)} == before
    assert trace.stop() is None
    rec = json.loads(path.read_text(encoding="utf-8"))
    assert ("tsbench.report.summary:load_steps", None) in edges(rec)
    (read,) = events(rec, "open", "/steps.jsonl")
    assert read["caller"].startswith("tsbench.report.summary:load_steps")
    assert read["sha256_at_read"] == sha(steps.read_bytes())
    assert not (tmp_path / "other").exists()


def test_the_cli_starts_the_tracer_from_the_variable_and_keeps_rc_and_output(tmp_path):
    tdir = tmp_path / "t"
    proc = subprocess.run([sys.executable, "-m", "tsbench", "tasks", "verify"], capture_output=True, text=True,
                          timeout=300, cwd=tmp_path, env=child_env(**{ENV_VAR: str(tdir)}), encoding="utf-8")
    untraced = subprocess.run([sys.executable, "-m", "tsbench", "tasks", "verify"], capture_output=True, text=True,
                              timeout=300, cwd=tmp_path, env=child_env(), encoding="utf-8")
    assert proc.returncode == untraced.returncode == 0
    assert proc.stdout == untraced.stdout
    (rec,) = records(tdir)
    assert "tasks verify" in rec["command"]
    assert any(c["function"] == "tsbench.tasks.verify:main" for c in rec["calls"])
    (read, *_) = events(rec, "open", "data/tasks/tasks.jsonl")
    assert read["sha256_at_read"] == sha(resource("tasks/tasks.jsonl").read_bytes())
    assert sorted(p.name for p in tmp_path.iterdir()) == ["t"], "tracing writes only into its own folder"


def test_children_are_traced_through_the_same_variable(tmp_path):
    tdir = tmp_path / "t"
    code = """
        import subprocess, sys
        from tsbench.core import trace
        assert trace.start_if_requested() is not None
        subprocess.run([sys.executable, "-m", "tsbench", "tasks", "verify"], check=True, capture_output=True)
    """
    proc = python(code, env=child_env(**{ENV_VAR: str(tdir)}), cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    recs = records(tdir)
    assert len(recs) == 2
    parent, child = sorted(recs, key=lambda r: r["start"])
    assert child["ppid"] == parent["pid"]
    assert any(e["event"] == "popen" and "tasks" in e["argv"] for e in parent["files"])
    assert any(c["function"] == "tsbench.tasks.verify:main" for c in child["calls"])


def test_the_fake_claude_traces_itself_from_the_variable(tmp_path):
    """fake_cli's `__main__` block starts the tracer before main(), so main itself is in the call list."""
    tdir = tmp_path / "t"
    proc = subprocess.run([sys.executable, "-m", "tsbench.run.fake_cli", "--model", "m", "--output-format",
                           "stream-json"], input="hello", capture_output=True, text=True, timeout=300, cwd=tmp_path,
                          env=child_env(**{ENV_VAR: str(tdir)}), encoding="utf-8")
    assert proc.returncode == 0, proc.stderr
    (rec,) = records(tdir)
    assert "fake_cli" in rec["command"]
    assert any(c["function"] == "tsbench.run.fake_cli:main" for c in rec["calls"])


def test_the_dry_run_child_environment_passes_the_variable_and_the_real_one_does_not(tmp_path):
    def child(parent: dict[str, str], dry_run: bool) -> dict[str, str]:
        return run_env.build_child_env(parent, home="/h", config_dir="/h/.claude", tmpdir="/tmp", repo=tmp_path,
                                       dry_run=dry_run, gateway=False)

    parent = {"PATH": "/usr/bin", ENV_VAR: str(tmp_path / "t")}
    assert child(parent, dry_run=True)[ENV_VAR] == str(tmp_path / "t")
    assert ENV_VAR not in child(parent, dry_run=False), "the real claude is not Python; its environment stays minimal"
    assert ENV_VAR not in child({"PATH": "/usr/bin"}, dry_run=True)


# ---------------------------------------------------------------- the callbacks, called directly
# The callbacks run inside sys.monitoring and the audit hook, where coverage does not see them. These tests
# call them on a made-up state, so nothing is installed in the pytest process.
FAKE_MODULE = """
def outer(callback):
    return callback()

def inner(function, *args):
    return function(*args)
"""


@pytest.fixture
def fake(trace, monkeypatch):
    """Functions compiled with a file name under src/tsbench, so the tracer takes them for tsbench code."""
    monkeypatch.setattr(trace, "_names", {})
    namespace: dict = {}
    exec(compile(FAKE_MODULE, os.path.join(trace._PACKAGE, "zz_fake.py"), "exec"), namespace)  # noqa: S102
    return namespace


@pytest.fixture
def state(trace, monkeypatch, tmp_path):
    import collections

    st = {"dir": str(tmp_path / "trace"), "calls": collections.Counter(), "files": []}
    monkeypatch.setattr(trace, "_state", st)
    monkeypatch.setattr(trace._local, "busy", False, raising=False)
    return st


def test_qualified_name_is_module_and_qualname_for_tsbench_code_only(trace, fake, monkeypatch):
    from tsbench.report import summary

    assert trace._qualified_name(summary.context.__code__) == "tsbench.report.summary:context"
    assert trace._qualified_name(resource.__code__) == "tsbench.core:resource", "__init__ is the package itself"
    assert trace._qualified_name(fake["outer"].__code__) == "tsbench.zz_fake:outer"
    assert trace._qualified_name(trace.redact.__code__) is None, "the tracer skips itself"
    assert trace._qualified_name(sha.__code__) is None, "test code is not tsbench code"
    assert trace._names[summary.context.__code__] == "tsbench.report.summary:context"
    assert trace._names[sha.__code__] is None, "a miss is cached, too"
    monkeypatch.setitem(trace._names, sha.__code__, "cached:name")
    assert trace._qualified_name(sha.__code__) == "cached:name"


def test_qualified_name_skips_non_python_files_under_the_package(trace, monkeypatch):
    monkeypatch.setattr(trace, "_names", {})
    code = compile("x = 1", os.path.join(trace._PACKAGE, "data", "x.txt"), "exec")
    assert trace._qualified_name(code) is None
    outside = compile("x = 1", trace._PACKAGE + "-other" + os.sep + "m.py", "exec")
    assert trace._qualified_name(outside) is None, "a sibling folder with the same prefix is not the package"


def test_nearest_walks_up_to_the_first_tsbench_frame(trace, fake):
    from types import SimpleNamespace

    def frame(code, back=None):
        return SimpleNamespace(f_code=code, f_back=back)

    top = frame(fake["outer"].__code__)
    middle = frame(fake["inner"].__code__, top)
    bottom = frame(sha.__code__, frame(edges.__code__, middle))
    assert trace._nearest(bottom) == "tsbench.zz_fake:inner"
    assert trace._nearest(top) == "tsbench.zz_fake:outer"
    assert trace._nearest(frame(sha.__code__)) is None
    assert trace._nearest(None) is None


def test_on_start_counts_the_edge_from_the_caller_two_frames_up(trace, fake, state):
    def probe():
        return trace._on_start(fake["inner"].__code__, 0)

    # frames: _on_start, probe (taken for the starting function), outer (its caller)
    assert fake["outer"](probe) is None
    assert fake["outer"](probe) is None
    assert state["calls"] == {("tsbench.zz_fake:inner", "tsbench.zz_fake:outer"): 2}
    assert trace._on_start(sha.__code__, 0) is sys.monitoring.DISABLE, "non-tsbench code is switched off"
    assert len(state["calls"]) == 1


def test_on_start_without_a_running_tracer_records_nothing(trace, fake, monkeypatch):
    monkeypatch.setattr(trace, "_state", None)
    assert trace._on_start(fake["inner"].__code__, 0) is None


def test_sha256_hashes_regular_files_only(trace, tmp_path, monkeypatch):
    big = tmp_path / "big.bin"
    data = os.urandom((1 << 20) * 2 + 17)  # more than one read chunk
    big.write_bytes(data)
    assert trace._sha256(str(big)) == sha(data)
    assert trace._sha256(str(tmp_path)) is None, "a folder"
    assert trace._sha256(str(tmp_path / "missing")) is None
    secret = tmp_path / "server.key"
    secret.write_text("k", encoding="utf-8")
    assert trace._sha256(str(secret)) is None
    for name in (".netrc", "a.pem", ".env.prod", "seed/x", "seed/sub/x", ".config/tsbench/env"):
        assert trace._SECRET.search(f"/p/{name}"), name
    for name in ("key.txt", "envelope", "seeds/x", "myseed/x", "a.pem.txt", ".config/tsbench/env.txt"):
        assert not trace._SECRET.search(f"/p/{name}"), name
    monkeypatch.setenv("TSBENCH_KEY_FILE", str(tmp_path / "model.cfg"))
    assert trace._is_secret(str(tmp_path / "model.cfg")) and not trace._is_secret(str(tmp_path / "other.cfg"))
    monkeypatch.setenv("TSBENCH_KEY_FILE", "")
    assert not trace._is_secret(str(tmp_path / "model.cfg"))

    def broken(_path):
        raise OSError("unreadable")

    monkeypatch.setattr(trace.os.path, "isfile", broken)
    assert trace._sha256(str(big)) is None, "an OSError gives no hash, not a crash"


def test_is_noise_drops_interpreter_files_and_the_trace_folder(trace, tmp_path):
    tdir = str(tmp_path / "trace")
    for path in (sys.prefix + "/lib/x.txt", sys.base_prefix + "/y.txt", tdir + "/1.trace.json", "/proc/self/stat",
                 "/dev/null", "/sys/x", "/w/__pycache__/m.txt", "/w/m.pyc", "/w/m.so", "/w/m.py"):
        assert trace._is_noise(path, tdir), path
    for path in ("/w/data.json", "/w/m.pyx", "/w/report.html"):
        assert not trace._is_noise(path, tdir), path


def test_open_mode_reads_text_modes_and_os_open_flags(trace):
    assert trace._open_mode("rb", None) == "rb"
    assert trace._open_mode("w", os.O_RDONLY) == "w", "a text mode wins over flags"
    assert trace._open_mode(None, None) == "r"
    assert trace._open_mode(None, "x") == "r"
    assert trace._open_mode(None, os.O_RDONLY) == "r"
    assert trace._open_mode(None, os.O_RDONLY | os.O_APPEND) == "r"
    assert trace._open_mode(None, os.O_WRONLY | os.O_CREAT) == "w"
    assert trace._open_mode(None, os.O_WRONLY | os.O_APPEND) == "a"
    assert trace._open_mode(None, os.O_RDWR) == "r+"
    assert trace._open_mode(None, os.O_RDWR | os.O_APPEND) == "r+"


def test_path_of_is_absolute_and_none_for_a_descriptor(trace, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert trace._path_of("a/b.txt") == str(tmp_path / "a" / "b.txt")
    assert trace._path_of(b"/x/y") == "/x/y"
    assert trace._path_of(Path("/x/z")) == "/x/z"
    assert trace._path_of(3) is None
    assert trace._path_of(None) is None


def test_on_audit_records_open_rename_remove_mkdir_with_the_caller(trace, fake, request, tmp_path):
    src = tmp_path / "in.txt"
    src.write_text("abc", encoding="utf-8")
    # the state comes after the write: once an in-process test has installed the real audit hook, it records, too
    state = request.getfixturevalue("state")
    fake["inner"](trace._on_audit, "open", (str(src), "r", 0))
    fake["inner"](trace._on_audit, "open", (str(src), None, os.O_WRONLY | os.O_APPEND))
    fake["inner"](trace._on_audit, "open", (str(src), "x"))
    fake["inner"](trace._on_audit, "os.rename", (str(src), str(tmp_path / "out.txt"), None, None))
    fake["inner"](trace._on_audit, "os.remove", (str(src), None))
    fake["inner"](trace._on_audit, "os.mkdir", (str(tmp_path / "d"), 0o777, None))
    trace._on_audit("os.remove", (str(tmp_path / "plain"), None))
    read, append, create, move, remove, mkdir, plain = state["files"]
    assert read == {"event": "open", "path": str(src), "caller": "tsbench.zz_fake:inner", "mode": "r",
                    "sha256_at_read": sha("abc")}
    assert append["mode"] == "a" and append["sha256_at_read"] is None
    assert create["mode"] == "x" and create["sha256_at_read"] is None
    assert move == {"event": "rename", "path": str(src), "caller": "tsbench.zz_fake:inner", "sha256_at_read": None,
                    "target": str(tmp_path / "out.txt")}
    assert remove == {"event": "remove", "path": str(src), "caller": "tsbench.zz_fake:inner", "sha256_at_read": None}
    assert mkdir["event"] == "mkdir" and mkdir["path"] == str(tmp_path / "d")
    assert plain["caller"] is None
    assert trace._local.busy is False


def test_on_audit_records_popen_with_redacted_argv(trace, state, monkeypatch):
    monkeypatch.setenv("HOME", "/home/me")
    trace._on_audit("subprocess.Popen", ("/home/me/bin/tool", ["tool", b"--in=/home/me/x", 7, Path("/opt/y")],
                                         None, None))
    trace._on_audit("subprocess.Popen", ("sh", "echo hi", None, None))
    trace._on_audit("subprocess.Popen", (None, ("a", "b"), None, None))
    first, shell, nameless = state["files"]
    assert first == {"event": "popen", "path": "~/bin/tool", "argv": ["tool", "--in=~/x", "/opt/y"], "caller": None}
    assert shell["argv"] == ["echo hi"] and shell["path"] == "sh"
    assert nameless["path"] is None and nameless["argv"] == ["a", "b"]


def test_on_audit_ignores_other_events_noise_descriptors_and_reentry(trace, state, tmp_path):
    trace._on_audit("os.listdir", (str(tmp_path),))
    trace._on_audit("open", (5, "r", 0))
    trace._on_audit("open", (state["dir"] + "/x.trace.json", "w", 0))
    trace._on_audit("open", ("/w/m.pyc", "rb", 0))
    trace._on_audit("os.rename", (str(tmp_path / "a"), 4, None, None))
    trace._local.busy = True
    trace._on_audit("os.remove", (str(tmp_path / "a"), None))
    assert trace._local.busy is True, "a nested event leaves the outer flag alone"
    trace._local.busy = False
    assert state["files"] == []


def test_on_audit_never_raises_and_clears_the_busy_flag(trace, state):
    trace._on_audit("subprocess.Popen", ("only-one-arg",))
    trace._on_audit("open", ())
    assert state["files"] == [] and trace._local.busy is False


def test_on_audit_without_a_running_tracer_does_nothing(trace, monkeypatch, tmp_path):
    monkeypatch.setattr(trace, "_state", None)
    monkeypatch.setattr(trace._local, "busy", False, raising=False)
    trace._on_audit("open", (str(tmp_path / "x"), "r", 0))
    assert trace._local.busy is False


def test_free_tool_id_takes_the_first_free_slot_or_none(trace, monkeypatch):
    taken: set[int] = set()
    monkeypatch.setattr(sys.monitoring, "get_tool", lambda tool: "busy" if tool in taken else None)
    assert trace._free_tool_id() == 3
    taken.add(3)
    assert trace._free_tool_id() == 4
    taken.add(4)
    assert trace._free_tool_id() == sys.monitoring.PROFILER_ID
    taken.add(sys.monitoring.PROFILER_ID)
    assert trace._free_tool_id() == sys.monitoring.OPTIMIZER_ID
    taken.add(sys.monitoring.OPTIMIZER_ID)
    assert trace._free_tool_id() is None


def test_finish_adds_the_end_hash_once_per_path_and_redacts(trace, monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / "a.txt").write_text("A", encoding="utf-8")
    (tmp_path / "b.txt").write_text("B", encoding="utf-8")
    hashed: list[str] = []
    real = trace._sha256
    monkeypatch.setattr(trace, "_sha256", lambda p: hashed.append(p) or real(p))
    files = [
        {"event": "open", "path": str(tmp_path / "a.txt")},
        {"event": "open", "path": str(tmp_path / "a.txt")},
        {"event": "rename", "path": str(tmp_path / "gone.tmp"), "target": str(tmp_path / "b.txt")},
        {"event": "popen", "path": "/bin/x", "argv": []},
    ]
    out = trace._finish(files)
    assert out is files
    assert [e.get("sha256_at_end") for e in out] == [sha("A"), sha("A"), sha("B"), None]
    assert "sha256_at_end" not in out[3]
    assert hashed == [str(tmp_path / "a.txt"), str(tmp_path / "b.txt")]
    assert out[0]["path"] == "~/a.txt" and out[2]["path"] == "~/gone.tmp" and out[2]["target"] == "~/b.txt"


def test_without_a_free_monitoring_slot_only_file_events_are_traced(trace, monkeypatch, tmp_path):
    monkeypatch.setattr(trace, "_free_tool_id", lambda: None)
    monkeypatch.setattr(sys, "argv", ["/venv/bin/tsbench", "score", "/home/alice/run"])
    before = {i: sys.monitoring.get_tool(i) for i in range(6)}
    path = trace.start(tmp_path / "t")
    try:
        assert {i: sys.monitoring.get_tool(i) for i in range(6)} == before, "no slot is taken"
        (tmp_path / "f.txt").write_text("x", encoding="utf-8")
    finally:
        assert trace.stop(exit_code=3) == path
    rec = json.loads(path.read_text(encoding="utf-8"))
    assert rec["argv"] == ["tsbench", "score", "~/run"] and rec["command"] == "tsbench score '~/run'"
    assert rec["exit_code"] == 3 and rec["calls"] == []
    assert events(rec, "open", "/f.txt")
    assert not path.with_name(path.name + ".tmp").exists()
