"""Exact rows of the doctor checks: env, B stack and the sandbox check (settings, a reusable record, the paid run).
Every outside call is a stand-in; nothing here starts claude or spends money."""

from __future__ import annotations

import argparse
import pathlib

import pytest

from tsbench.conditions import sandbox
from tsbench.core import keys
from tsbench.run import doctor, runner

REPO_ROOT = runner.REPO_ROOT


@pytest.fixture(autouse=True)
def no_host_key_file(monkeypatch):
    """The key file named by the host must not change the settings these tests render and hash."""
    monkeypatch.delenv("TSBENCH_KEY_FILE", raising=False)

GWDG_NONE = ("INFO", "env GWDG key (optional)",
             "neither GWDG_API_KEY nor GWDG_AI_API_KEY set (only needed for gateway smoke tests)")


# ------------------------------------------------------------------ env
@pytest.mark.parametrize("env,rows", [
    ({"TSMCP_ANTHROPIC_API_KEY": "x"}, [("OK", "env API key", "TSMCP_ANTHROPIC_API_KEY is set"), GWDG_NONE]),
    ({"ANTHROPIC_API_KEY": "x", "ANTHROPIC_BASE_URL": "u", "GWDG_AI_API_KEY": "g"},
     [("OK", "env API key", "ANTHROPIC_API_KEY is set"),
      ("WARN", "env ANTHROPIC_BASE_URL", "set; the runner drops it in direct mode (use --gateway to route through it)"),
      ("INFO", "env GWDG key (optional)", "GWDG_AI_API_KEY is set")]),
    ({"GWDG_API_KEY": "g", "GWDG_AI_API_KEY": "g"},
     [("FAIL", "env API key", "neither TSMCP_ANTHROPIC_API_KEY nor ANTHROPIC_API_KEY is set"),
      ("INFO", "env GWDG key (optional)", "GWDG_API_KEY is set")]),
])
def test_env_rows_direct(env, rows):
    assert doctor.check_env(env, gateway=False) == rows


def test_env_rows_gateway():
    assert doctor.check_env({}, gateway=True) == [
        ("FAIL", "env ANTHROPIC_BASE_URL", "NOT set (required with --gateway)"),
        ("FAIL", "env ANTHROPIC_AUTH_TOKEN", "NOT set (required with --gateway)"), GWDG_NONE]
    env = {"ANTHROPIC_BASE_URL": "u", "ANTHROPIC_AUTH_TOKEN": "t", "ANTHROPIC_API_KEY": "k"}
    assert doctor.check_env(env, gateway=True) == [
        ("OK", "env ANTHROPIC_BASE_URL", "set"), ("OK", "env ANTHROPIC_AUTH_TOKEN", "set"),
        ("WARN", "env ANTHROPIC_API_KEY", "set; unset it (the runner drops it in gateway mode anyway)"), GWDG_NONE]


# ------------------------------------------------------------------ B stack
def test_b_stack_row(monkeypatch):
    seen = []
    info = {"path": "/v", "bin": "/v/bin", "python": "3.14.7", "digest": "ab" * 32,
            "packages": {"numpy": "1", "scipy": "2", "sympy": "3", "matplotlib": "4"}}
    monkeypatch.setattr(doctor.b_stack, "b_venv_dir", lambda env, override, repo: seen.append((env, override, repo))
                        or "/v")
    monkeypatch.setattr(doctor.b_stack, "ensure_b_stack", lambda venv, **kw: info)
    env = {"A": "1"}
    assert doctor.check_b_stack(env, "/override") == [
        ("OK", "B stack", "/v python 3.14.7, numpy 1, scipy 2, sympy 3, matplotlib 4, no tanabesugano, no pip; "
                          "digest abababababab")]
    assert seen == [(env, "/override", REPO_ROOT)]


# ------------------------------------------------------------------ the sandbox check
def args(tmp_path, *flags):
    return doctor.parse_args([*flags, "--out", str(tmp_path)])


def real_home(env) -> str:
    """The real home the doctor renders the settings for: the HOME of the checked environment."""
    return str(pathlib.Path(env.get("HOME") or "~").expanduser())


def settings_row(**kw) -> tuple:
    """`kw`: how the doctor renders the settings it hashes (`b_venv`, `parent_env`)."""
    home = real_home(kw.get("parent_env") or {})
    sb = sandbox.render_settings(REPO_ROOT, home, **kw)["sandbox"]
    return ("OK", "sandbox settings", f"valid, sha256 {sandbox.settings_sha256(REPO_ROOT, home, **kw)[:12]}, "
            f"{len(sb['filesystem']['denyRead'])} denyRead / {len(sb['filesystem'].get('allowRead', []))} "
            "allowRead paths")


@pytest.fixture
def known_claude(monkeypatch):
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: "9.9 (Claude Code)")


@pytest.fixture
def digest(monkeypatch):
    """b_venv_dir and digest_if_present stand-ins; returns the calls they saw."""
    calls = []
    monkeypatch.setattr(doctor.b_stack, "b_venv_dir",
                        lambda env, override, repo: calls.append((env, override, repo)) or "/venv")
    monkeypatch.setattr(doctor.b_stack, "digest_if_present", lambda venv: calls.append(venv) or "cd" * 32)
    return calls


def record(passed, reasons=()):
    return {"passed": passed, "cost_usd": 0.0123, "reasons": list(reasons), "claude_version": "9.9 (Claude Code)",
            "markers": {"CTRL1": [0], "NET": [1]}}


def test_sandbox_check_reuses_a_record(monkeypatch, tmp_path, known_claude, digest):
    seen = []
    rec = record(True)

    def load(out, cv, settings_hash, b_digest, *, auth):
        seen.append((out, cv, settings_hash, b_digest, auth))
        return rec

    monkeypatch.setattr(doctor.sandbox, "load_reusable_probe", load)
    env = {"HOME": "/h"}
    rows = doctor.check_sandbox(env, args(tmp_path, "--gateway", "--b-venv", "/bv"), tmp_path, key_ok=True)
    skw = {"b_venv": "/venv", "parent_env": env}  # the settings are hashed for the venv that b_venv_dir returned
    assert rows == [settings_row(**skw),
                    ("OK", "sandbox probe", f"reusable passing record in {tmp_path.name}/sandbox_probe.json "
                                            "(claude 9.9 (Claude Code))"),
                    *doctor._marker_rows(rec)]
    want = sandbox.settings_sha256(REPO_ROOT, "/h", b_venv="/venv", parent_env=env)
    assert seen == [(tmp_path, "9.9 (Claude Code)", want, "cd" * 32, "gateway")]
    assert digest[:2] == [(env, "/bv", REPO_ROOT), "/venv"]


def test_sandbox_check_looks_up_the_probe_of_the_given_b_venv(monkeypatch, tmp_path, known_claude):
    """The probe record is keyed by the settings hash of the session, which renders them for the --b-venv."""
    seen = []

    def load(out, cv, settings_hash, b_digest, *, auth):
        seen.append(settings_hash)
        return None

    monkeypatch.setattr(doctor.sandbox, "load_reusable_probe", load)
    monkeypatch.setattr(doctor.b_stack, "digest_if_present", lambda venv: "cd" * 32)
    venv = tmp_path / "other-venv-B"
    venv.mkdir()
    env = {"HOME": "/h"}
    doctor.check_sandbox(env, args(tmp_path, "--b-venv", str(venv)), tmp_path, key_ok=True)
    assert seen == [sandbox.settings_sha256(REPO_ROOT, "/h", b_venv=venv, parent_env=env)]
    assert seen != [sandbox.settings_sha256(REPO_ROOT)]


def test_sandbox_check_asks_for_the_direct_record_without_gateway(monkeypatch, tmp_path, known_claude, digest):
    seen = []
    monkeypatch.setattr(doctor.sandbox, "load_reusable_probe", lambda *a, auth: seen.append(auth))
    doctor.check_sandbox({}, args(tmp_path), tmp_path, key_ok=True)
    assert seen == ["direct"]


def test_sandbox_check_without_a_paid_run(monkeypatch, tmp_path, known_claude, digest):
    monkeypatch.setattr(doctor.sandbox, "load_reusable_probe", lambda *a, **k: None)
    rows = doctor.check_sandbox({}, args(tmp_path), tmp_path, key_ok=True)
    assert rows == [settings_row(),
                    ("WARN", "sandbox probe", f"no reusable passing sandbox_probe.json in {tmp_path}; the runner will "
                                              "run the paid probe (one small model call) unless you make the record "
                                              "now with: tsbench doctor --probe --out DIR")]


def test_sandbox_check_without_a_key(monkeypatch, tmp_path, known_claude, digest):
    monkeypatch.setattr(doctor.sandbox, "load_reusable_probe", lambda *a, **k: None)
    rows = doctor.check_sandbox({}, args(tmp_path, "--probe"), tmp_path, key_ok=False)
    assert rows == [settings_row(), ("FAIL", "sandbox probe", "needs credentials (see env checks above); not run")]


class Session:
    closed = False

    def close(self):
        self.closed = True


@pytest.mark.parametrize("passed,status,word", [(True, "OK", "PASS"), (False, "FAIL", "FAIL")])
def test_sandbox_check_with_a_paid_run(monkeypatch, tmp_path, capsys, known_claude, digest, passed, status, word):
    monkeypatch.setattr(doctor.sandbox, "load_reusable_probe", lambda *a, **k: None)
    session, seen = Session(), {}
    rec = record(passed, reasons=["r1", "r2"] if not passed else ())

    def create(**kw):
        seen["create"] = kw
        return session

    def run(sess, out, *, model):
        seen["run"] = (sess, out, model)
        return rec

    monkeypatch.setattr(doctor.runner.Session, "create", create)
    monkeypatch.setattr(doctor.sandbox_probe, "run_probe", run)
    env = {"X": "1"}
    rows = doctor.check_sandbox(env, args(tmp_path, "--probe", "--b-venv", "/bv"), tmp_path, key_ok=True)
    reasons = [("FAIL", "sandbox probe reason", r) for r in rec["reasons"]]
    assert rows == [settings_row(),
                    (status, "sandbox probe", f"{word}; cost USD 0.0123; record {tmp_path / 'sandbox_probe.json'}"),
                    *reasons, *doctor._marker_rows(rec)]
    assert seen == {"create": {"dry_run": False, "gateway": False, "parent_env": env, "repo": REPO_ROOT,
                               "b_venv": "/bv", "create_b": False},
                    "run": (session, tmp_path, sandbox.PROBE_MODEL)}
    assert session.closed
    assert capsys.readouterr().out == (
        "running the paid sandbox probe (one small call to claude-haiku-5-5, cap USD 0.10) ...\n")


class Stdout:
    """sys.stdout stand-in: records each write and each flush, in order."""

    def __init__(self):
        self.events = []

    def write(self, text):
        self.events.append(text)
        return len(text)

    def flush(self):
        self.events.append("<flush>")


def test_sandbox_check_flushes_the_paid_run_notice_before_the_probe(monkeypatch, tmp_path, known_claude, digest):
    monkeypatch.setattr(doctor.sandbox, "load_reusable_probe", lambda *a, **k: None)
    out = Stdout()
    monkeypatch.setattr("sys.stdout", out)
    monkeypatch.setattr(doctor.runner.Session, "create", lambda **kw: Session())
    monkeypatch.setattr(doctor.sandbox_probe, "run_probe",
                        lambda sess, o, **kw: out.events.append("<probe>") or record(True))
    doctor.check_sandbox({}, args(tmp_path, "--probe"), tmp_path, key_ok=True)
    text = "".join(e for e in out.events if e not in ("<flush>", "<probe>"))
    assert text == "running the paid sandbox probe (one small call to claude-haiku-5-5, cap USD 0.10) ...\n"
    assert out.events[-2:] == ["<flush>", "<probe>"]


def test_paid_run_accepts_a_namespace_without_b_venv(monkeypatch, tmp_path, capsys, known_claude, digest):
    monkeypatch.setattr(doctor.sandbox, "load_reusable_probe", lambda *a, **k: None)
    created = []
    monkeypatch.setattr(doctor.runner.Session, "create", lambda **kw: created.append(kw) or Session())
    monkeypatch.setattr(doctor.sandbox_probe, "run_probe", lambda sess, out, **kw: record(True))
    ns = argparse.Namespace(gateway=False, probe=True, model=None, out=str(tmp_path))
    rows = doctor.check_sandbox({}, ns, tmp_path, key_ok=True)
    assert created == [{"dry_run": False, "gateway": False, "parent_env": {}, "repo": REPO_ROOT, "b_venv": None,
                        "create_b": False}]
    assert rows[1] == ("OK", "sandbox probe", f"PASS; cost USD 0.0123; record {tmp_path / 'sandbox_probe.json'}")


def test_sandbox_check_accepts_a_namespace_without_b_venv(monkeypatch, tmp_path, digest):
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: None)
    env = {"A": "1"}
    ns = argparse.Namespace(gateway=False, probe=False, model=None, out=str(tmp_path))
    rows = doctor.check_sandbox(env, ns, tmp_path, key_ok=True)
    assert digest[:2] == [(env, None, REPO_ROOT), "/venv"]
    assert rows == [settings_row(), ("WARN", "sandbox probe", "claude not found; a probe cannot be reused or run")]


def test_sandbox_check_asks_claude_with_the_given_env(monkeypatch, tmp_path, digest):
    seen = []
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: seen.append(env))
    env = {"PATH": "/only/here"}
    rows = doctor.check_sandbox(env, args(tmp_path), tmp_path, key_ok=True)
    assert seen == [env]
    assert rows == [settings_row(), ("WARN", "sandbox probe", "claude not found; a probe cannot be reused or run")]


def test_sandbox_check_passes_no_digest_for_a_broken_b_venv_path(monkeypatch, tmp_path, known_claude):
    def broken(env, override, repo):
        raise doctor.b_stack.BStackError("bad path")

    seen = []
    monkeypatch.setattr(doctor.b_stack, "b_venv_dir", broken)
    monkeypatch.setattr(doctor.sandbox, "load_reusable_probe",
                        lambda out, cv, settings_hash, b_digest, *, auth: seen.append(b_digest))
    rows = doctor.check_sandbox({}, args(tmp_path), tmp_path, key_ok=True)
    assert seen == [None]
    assert rows[1][:2] == ("WARN", "sandbox probe")


def test_sandbox_settings_without_a_network_block(monkeypatch, tmp_path):
    home = str(tmp_path / "home")
    monkeypatch.setattr(doctor.sandbox, "render_settings",
                        lambda repo, *a, **k: {"sandbox": {"enabled": True,
                                                           "filesystem": {"denyRead": [
                                                               str(REPO_ROOT), home,
                                                               *keys.key_dir_entries({}, home)]}}})
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: None)
    rows = doctor.check_sandbox({"HOME": home}, args(tmp_path), tmp_path, key_ok=True)
    assert rows[0] == ("FAIL", "sandbox settings", "network.allowedDomains is not empty")


def test_sandbox_settings_with_the_default_home(monkeypatch, tmp_path):
    home = str(pathlib.Path("~").expanduser())
    deny = [str(REPO_ROOT), home, *keys.key_dir_entries({}, home)]
    monkeypatch.setattr(doctor.sandbox, "render_settings",
                        lambda repo, *a, **k: {"sandbox": {"enabled": True, "network": {"allowedDomains": []},
                                                           "filesystem": {"denyRead": deny}}})
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: None)
    rows = doctor.check_sandbox({}, args(tmp_path), tmp_path, key_ok=True)
    assert rows[0][:2] == ("OK", "sandbox settings")
    assert rows[0][2].endswith(f"{len(deny)} denyRead / 0 allowRead paths")


@pytest.mark.parametrize("sb", [
    {"enabled": True, "network": {"allowedDomains": []}},
    {"enabled": True, "network": {"allowedDomains": []}, "filesystem": {}},
], ids=["no filesystem block", "no denyRead list"])
def test_sandbox_settings_without_a_deny_list_name_every_missing_path(monkeypatch, tmp_path, sb):
    monkeypatch.setattr(doctor.sandbox, "render_settings", lambda repo, *a, **k: {"sandbox": sb})
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: None)
    rows = doctor.check_sandbox({"HOME": str(tmp_path / "home")}, args(tmp_path), tmp_path, key_ok=True)
    assert rows[0] == ("FAIL", "sandbox settings",
                       "repo path missing from denyRead; the real home is missing from denyRead; "
                       "the key file folder is missing from denyRead")


def test_sandbox_settings_without_home_need_the_expanded_home(monkeypatch, tmp_path):
    # with HOME unset only the expanded "~" counts; a relative entry that merely contains "~" does not
    monkeypatch.setattr(doctor.sandbox, "render_settings",
                        lambda repo, *a, **k: {"sandbox": {"enabled": True, "network": {"allowedDomains": []},
                                                           "filesystem": {"denyRead": [str(REPO_ROOT), "XX~XX"]}}})
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: None)
    rows = doctor.check_sandbox({}, args(tmp_path), tmp_path, key_ok=True)
    assert rows[0] == ("FAIL", "sandbox settings",
                       "the real home is missing from denyRead; the key file folder is missing from denyRead")
