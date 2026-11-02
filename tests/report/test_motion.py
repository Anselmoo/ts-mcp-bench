"""The motion of the report pages (templates/motion.js, window.TSMOTION) in headless Chrome.

The contract: motion never changes a figure. Every `figure .plot svg` is the same (Figura's random `jfs-clip-*` ids
numbered in order) under prefers-reduced-motion, after all staged motion has played, and right after TSMOTION.finish()
or a beforeprint event mid-motion (what Save SVG and printing call). Also the drill-down of the dashboard: a click on a
bar segment of a model card leaves only the runs it counts visible in the run table.

Pages: dashboard, comparison and literature of the demo run set (fake claude, as tools/render_mock.sh), the overview
of a functional test (tools/functional_test.sh) and a quality page, built from small inputs in tmp_path. Chrome is
driven over the DevTools protocol on its WebSocket. Without Chrome the module skips; TSBENCH_REQUIRE_CHROME=1 (CI)
makes a missing Chrome a failure. TSBENCH_CHROME names the executable."""
from __future__ import annotations

import contextlib
import itertools
import json
import os
import pathlib
import re
import shutil
import subprocess
import time

import pytest
from websockets.sync.client import connect

from tsbench.report import comparison, dashboard, functional, literature, quality

CHROMES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome")
PAGES = ("dashboard", "comparison", "literature", "functional", "quality")


def find_chrome() -> str | None:
    named = os.environ.get("TSBENCH_CHROME")
    if named:
        return named if os.access(named, os.X_OK) else None
    return next((p for p in map(shutil.which, CHROMES) if p), None)


# looked up at import: the autouse fixture of tests/conftest.py replaces shutil.which during every test
CHROME = find_chrome()
REQUIRED = os.environ.get("TSBENCH_REQUIRE_CHROME") == "1"
pytestmark = pytest.mark.skipif(CHROME is None and not REQUIRED,
                                reason="no Chrome or Chromium found (TSBENCH_CHROME or " + ", ".join(CHROMES) + ")")

# in-page helpers: the figures as markup; whether a d3 transition or a Web Animation is pending; the elements whose
# staged marks still wait (TSMOTION.waiting(): not yet seen, or in the lead before they move); a scroll that brings
# each figure into view and stays until its motion has started (a figure scrolled past before the page rendered a
# frame is never seen); quiet: 1 s with nothing moving and nothing waiting; stopAt: scroll the figures into view and
# run `stop` in the same turn as the first poll that finds motion under way, returning the figures right after it
# (null when nothing moved)
HELPERS = """
window.__svgs = () => Array.from(document.querySelectorAll("figure .plot svg"), s => s.outerHTML);
window.__moving = () => document.getAnimations().length > 0
  || Array.from(document.querySelectorAll("figure .plot svg *")).some(n => n.__transition);
window.__sleep = ms => new Promise(r => setTimeout(r, ms));
window.__waiting = () => window.TSMOTION ? TSMOTION.waiting() : [];
window.__seeAll = async () => {
  for (const f of document.querySelectorAll("figure")) {
    f.scrollIntoView({block: "center"});
    for (let t = 0; t < 500 && __waiting().some(el => el === f || f.contains(el) || el.contains(f)); t++) {
      await __sleep(20);
    }
  }
};
window.__quiet = async (limit = 300) => {
  for (let t = 0, calm = 0; t < limit; t++) {
    calm = __moving() || __waiting().length ? 0 : calm + 1;
    if (calm >= 10) return true;
    await __sleep(100);
  }
  return false;
};
window.__stopAt = async stop => {
  const start = __svgs().join("");
  for (const f of document.querySelectorAll("figure")) {
    f.scrollIntoView({block: "center"});
    for (let t = 0; t < 100; t++) {
      if (__moving() && __svgs().join("") !== start) { stop(); return __svgs(); }
      await __sleep(10);
    }
  }
  return null;
};
"""


class Browser:
    """One headless Chrome with one tab, driven over the DevTools protocol (CDP) on its browser WebSocket."""

    def __init__(self, exe: str, profile: pathlib.Path):
        args = [exe, "--headless=new", "--remote-debugging-port=0", f"--user-data-dir={profile}", "--no-first-run",
                "--no-default-browser-check", "--disable-gpu", "--disable-dev-shm-usage", "--window-size=1280,900"]
        if os.geteuid() == 0:
            args.append("--no-sandbox")  # root in a CI container
        self.proc = subprocess.Popen([*args, "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        port_file = profile / "DevToolsActivePort"
        deadline = time.monotonic() + 30
        while not (port_file.is_file() and len(port_file.read_text(encoding="utf-8").split()) >= 2):
            if self.proc.poll() is not None or time.monotonic() > deadline:
                self.proc.kill()
                raise RuntimeError(f"{exe} did not open its DevTools port")
            time.sleep(0.05)
        port, path = port_file.read_text(encoding="utf-8").split()[:2]
        self.stack = contextlib.ExitStack()
        self.ws = self.stack.enter_context(connect(f"ws://127.0.0.1:{port}{path}", max_size=None, open_timeout=30))
        self.ids = itertools.count(1)
        target = self.send("Target.createTarget", url="about:blank")["targetId"]
        self.session = self.send("Target.attachToTarget", targetId=target, flatten=True)["sessionId"]

    def send(self, method: str, session: str | None = None, **params) -> dict:
        n = next(self.ids)
        self.ws.send(json.dumps({"id": n, "method": method, "params": params,
                                 **({"sessionId": session} if session else {})}))
        while True:  # events and other replies are dropped
            reply = json.loads(self.ws.recv(timeout=60))
            if reply.get("id") == n:
                if "error" in reply:
                    raise RuntimeError(f"{method}: {reply['error']}")
                return reply["result"]

    def js(self, expression: str):
        r = self.send("Runtime.evaluate", self.session, expression=expression, awaitPromise=True,
                      returnByValue=True)
        if "exceptionDetails" in r:
            raise AssertionError(f"{expression[:60]}: {r['exceptionDetails']}")
        return r["result"].get("value")

    def open(self, path: pathlib.Path, *, reduced: bool) -> None:
        """Load `path` with prefers-reduced-motion set to reduce or no-preference; returns once it has loaded."""
        self.send("Emulation.setEmulatedMedia", self.session,
                  features=[{"name": "prefers-reduced-motion", "value": "reduce" if reduced else "no-preference"}])
        url = path.as_uri()
        self.send("Page.navigate", self.session, url=url)
        deadline = time.monotonic() + 30
        while self.js(f"location.href === {json.dumps(url)} && document.readyState === 'complete'") is not True:
            assert time.monotonic() < deadline, f"{path.name} did not load"
            time.sleep(0.05)
        self.js(HELPERS)
        assert self.js("document.querySelectorAll('figure .err').length") == 0, f"{path.name}: a figure failed"
        assert self.js("TSMOTION.ok") is (not reduced)

    def close(self) -> None:
        self.stack.close()
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def normalised(svgs: list[str]) -> list[str]:
    """Figura's clip-path ids are random per drawing: number them in order of first appearance."""
    def numbered(svg: str) -> str:
        ids: dict[str, str] = {}
        return re.sub(r"jfs-clip-[0-9a-z]+", lambda m: ids.setdefault(m[0], f"jfs-clip-{len(ids)}"), svg)

    return [numbered(s) for s in svgs]


def _trace(pid: int, start: float, end: float, files: list[tuple[str, str, str]]) -> dict:
    """A trace record of one process in the format of tsbench.core.trace: files are (path, mode, sha256)."""
    return {"schema": "tsbench.trace/1", "pid": pid, "ppid": 1, "argv": ["tsbench"], "command": "tsbench", "cwd": "/w",
            "start": start, "end": end, "exit_code": 0,
            "files": [{"event": "open", "path": p, "mode": m, "caller": "tsbench.x:f",
                       "sha256_at_read": sha if m == "r" else None, "sha256_at_end": sha} for p, m, sha in files],
            "calls": [{"function": "tsbench.m:f", "caller": None, "count": 1}]}


def functional_folder(root: pathlib.Path) -> pathlib.Path:
    """steps.jsonl and trace/ of three steps that hand a plan and a transcript on, plus their scores."""
    plan, transcript, scores = root / "plan" / "plan.jsonl", root / "runs" / "t-k1.jsonl", root / "runs" / "scores.csv"
    h_plan, h_transcript, h_scores = "a1" * 32, "b2" * 32, "c3" * 32
    traces = {"plan-build": [_trace(10, 100.0, 101.0, [("~/tasks.jsonl", "r", "d4" * 32), (str(plan), "w", h_plan)])],
              "run": [_trace(20, 102.0, 105.0, [(str(plan), "r", h_plan), (str(transcript), "w", h_transcript)]),
                      _trace(21, 103.0, 104.5, [(str(plan), "r", h_plan)])],
              "score": [_trace(30, 106.0, 106.5, [(str(transcript), "r", h_transcript), (str(scores), "w", h_scores)])]}
    steps = []
    for name, records in traces.items():
        (root / "trace" / name).mkdir(parents=True)
        for rec in records:
            (root / "trace" / name / f"{rec['pid']}.trace.json").write_text(json.dumps(rec), encoding="utf-8")
        steps.append({"name": name, "command": f"tsbench {name}", "rc": 0, "log": f"logs/{name}.log", "outputs": []})
    (root / "steps.jsonl").write_text("".join(json.dumps(s) + "\n" for s in steps), encoding="utf-8")
    scores.parent.mkdir(parents=True)
    scores.write_text("model,condition,task_id,correct,evaluable,failure_category\n"
                      "m,A,t1,True,True,\nm,B,t1,False,True,wrong_value\nm,C,t1,,0,rate_limited\n", encoding="utf-8")
    return root / "steps.jsonl"


def coverage_report(path: pathlib.Path, files: dict[str, tuple[int, int]]) -> pathlib.Path:
    """A coverage.py JSON report (format 3): file -> (covered lines, statements)."""
    out = {name: {"summary": {"covered_lines": c, "num_statements": n, "percent_covered": 100.0 * c / n}}
           for name, (c, n) in files.items()}
    c, n = sum(v[0] for v in files.values()), sum(v[1] for v in files.values())
    path.write_text(json.dumps({"meta": {"format": 3, "timestamp": "2026-10-30T12:00:00"}, "files": out,
                                "totals": {"covered_lines": c, "num_statements": n,
                                           "percent_covered": 100.0 * c / n}}), encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def pages(tmp_path_factory, demo_runs_root) -> dict[str, pathlib.Path]:
    root = tmp_path_factory.mktemp("pages")
    shutil.copytree(demo_runs_root, root / "runs")
    out = {name: root / f"{name}.html" for name in PAGES}
    mp = pytest.MonkeyPatch()
    mp.setenv("SOURCE_DATE_EPOCH", "0")
    try:
        assert dashboard.main(["--runs", str(root / "runs"), "--out", str(out["dashboard"]),
                               "--title", "Demo run set (fake claude)"]) == 0
        for name, mod in (("comparison", comparison), ("literature", literature)):
            assert mod.main(["--runs", str(root / "runs"), "--out", str(out[name])]) == 0
        steps = functional_folder(root / "functional-test")
        assert functional.main(["--steps", str(steps), "--mode", "fake claude", "--out", str(out["functional"])]) == 0
        x, y, z = "src/tsbench/a/x.py", "src/tsbench/b/y.py", "src/tsbench/c/z.py"
        before = coverage_report(root / "before.json", {x: (80, 100), y: (50, 100), z: (10, 10)})
        after = coverage_report(root / "after.json", {x: (69, 100), y: (90, 100), z: (10, 10)})
        assert quality.main(["--coverage-before", str(before), "--coverage-after", str(after),
                             "--out", str(out["quality"])]) == 0
    finally:
        mp.undo()
    return out


@pytest.fixture(scope="module")
def browser(tmp_path_factory):
    if CHROME is None:
        pytest.fail("TSBENCH_REQUIRE_CHROME=1 but no Chrome or Chromium was found")
    b = Browser(CHROME, tmp_path_factory.mktemp("chrome-profile"))
    yield b
    b.close()


@pytest.fixture(scope="module")
def drawn(browser, pages) -> dict[str, list[str]]:
    """Each page's figures as drawn without motion (prefers-reduced-motion: reduce)."""
    out = {}
    for name, path in pages.items():
        browser.open(path, reduced=True)
        out[name] = normalised(browser.js("__svgs()"))
        assert out[name], f"{name}: no figure drawn"
    return out


@pytest.mark.parametrize("name", PAGES)
def test_figures_after_all_motion_are_the_drawn_figures(browser, pages, drawn, name):
    browser.open(pages[name], reduced=False)
    staged = normalised(browser.js("__svgs()"))
    assert staged != drawn[name], "nothing was staged: the check would be empty"
    browser.js("__seeAll()")
    assert browser.js("__quiet()"), "motion did not come to rest"
    assert normalised(browser.js("__svgs()")) == drawn[name]


def test_a_figure_still_waiting_to_be_seen_is_not_at_rest(browser, pages):
    """Motion has not come to rest while a staged figure waits to be seen: nothing moves yet, but its marks are still
    at their start. TSMOTION.waiting() names those figures; scrolled into view, each one starts and leaves the list."""
    browser.open(pages["dashboard"], reduced=False)
    waiting = browser.js("TSMOTION.waiting().length")
    assert waiting > 0, "every figure was already in view: the check would be empty"
    assert browser.js("__quiet(20)") is False
    browser.js("__seeAll()")
    assert browser.js("TSMOTION.waiting().length") == 0
    assert browser.js("__quiet()")


@pytest.mark.parametrize("stop", ["TSMOTION.finish()", "window.dispatchEvent(new Event('beforeprint'))"],
                         ids=["finish", "beforeprint"])
@pytest.mark.parametrize("name", PAGES)
def test_figures_stopped_mid_motion_are_the_drawn_figures(browser, pages, drawn, name, stop):
    browser.open(pages[name], reduced=False)
    now = browser.js(f"__stopAt(() => {stop})")
    assert now is not None, "no motion was running: the check would be empty"
    assert normalised(now) == drawn[name]
    assert browser.js("__quiet()")
    assert normalised(browser.js("__svgs()")) == drawn[name], "a transition changed a figure after the stop"


def test_a_bar_segment_of_a_model_card_shows_exactly_its_runs(browser, pages):
    browser.open(pages["dashboard"], reduced=True)
    clicks = browser.js("""(() => {
      const rows = Array.from(document.querySelectorAll("#runtable tbody tr")), out = [];
      let got = null;
      document.addEventListener("tsb:segment", e => { got = e.detail; });
      for (const rect of document.querySelectorAll(".mcard rect[data-k]")) {
        got = null;
        rect.dispatchEvent(new MouseEvent("click", {bubbles: true}));
        out.push({card: rect.closest(".mcard").dataset.model, k: rect.dataset.k,
                  count: rect.querySelector("title").textContent, detail: got,
                  bar: !document.getElementById("drill").hidden,
                  rows: rows.map(r => ({model: r.dataset.model, cond: r.dataset.cond,
                                        k: (r.className.match(/\\bo-(\\w+)/) || [])[1], shown: !r.hidden}))});
      }
      document.querySelector("#drill button").click();
      return {clicks: out, restored: rows.every(r => !r.hidden)};
    })()""")
    assert clicks["clicks"], "no bar segment of a model card can be clicked"
    for c in clicks["clicks"]:
        d = c["detail"]
        assert d is not None and d["model"] == c["card"] and d["k"] == c["k"], c
        assert c["bar"], "the drill-down note is hidden"
        want = [r for r in c["rows"] if (r["model"], r["cond"], r["k"]) == (d["model"], d["cond"], d["k"])]
        shown = [r for r in c["rows"] if r["shown"]]
        assert shown == want, f"{d}: other rows are visible"
        if c["k"] != "notrun":  # planned runs that never ran have no row
            assert len(shown) == int(c["count"].rsplit(": ", 1)[1]), f"{d}: the segment counts {c['count']}"
    assert clicks["restored"], "Show all runs did not bring every row back"
