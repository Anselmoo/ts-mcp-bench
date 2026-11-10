# The pipeline: stages, files, commands

Each stage is one subpackage of `tsbench` and one command. A stage reads only the files written by the stages before
it; the layer rule is enforced by `tests/test_layers.py`:

    cli > release > analyze > figures, report > stats > run, score > plan > tasks, conditions > core

| Stage | Package | Command | Reads | Writes |
|---|---|---|---|---|
| task set | `tsbench.tasks` | `tsbench tasks generate`, `tsbench tasks verify` | the literature tables (`data/literature/`) and the class modules (`tasks/classes/`) | `data/tasks/tasks.jsonl`, `tasks.sha256`, `rubric.md` |
| conditions | `tsbench.conditions` | `tsbench env b-stack`, `tsbench env sandbox` | `data/conditions/` (`ts.json`, `b-stack.txt`), `data/prompts/`, `data/schemas/` | the B venv outside the repository; sandbox settings |
| plan | `tsbench.plan` | `tsbench plan build`, `plan validate`, `plan estimate` | task set, conditions | `plan.jsonl` (+ `plan.sha256`, `plan.md`); `plan.sealed.json` for a confirmatory plan |
| run | `tsbench.run` | `tsbench run` | the plan only | transcripts, sidecars, `MANIFEST.json`, `inputs/`, `README.md`, `run_set.json` |
| score | `tsbench.score` | `tsbench score`, `tsbench score path` | transcripts, task set | `scores.csv`, `rates.csv`; with `path`: `<task>-k<i>.path.json` and `paths.csv` in `--out` |
| stats | `tsbench.stats` | `tsbench metrics`, `tsbench stats hypotheses`, `tsbench stats power` | score tables | `metrics/*.csv`; `hypotheses.json` and `power.csv` (in the current directory unless `--out` names a file) |
| figures | `tsbench.figures` | `tsbench figures` | score tables, transcripts | figure files with `.source.csv` and `.json` provenance |
| report | `tsbench.report` | `tsbench report …`, `tsbench explain` | score tables, transcripts, plans | self-contained HTML pages |
| analyze | `tsbench.analyze` | `tsbench analyze snippets` | transcripts | `<run id>/step-NN.sh`, one file per heredoc, `index.csv` and `README.md` in `--out` |
| analyze | `tsbench.analyze` | `tsbench analyze strategy` | transcripts, task set, `scores.csv` | `runs.csv`, `by_group.csv` (strategy shares and accuracy) and `README.md` in `--out` |
| analyze | `tsbench.analyze` | `tsbench analyze errors` | transcripts, `scores.csv` | `runs.csv`, `steps.csv`, `exceptions.csv`, `by_group.csv` and `README.md` in `--out` |
| analyze | `tsbench.analyze` | `tsbench analyze provenance` | transcripts, task set, `scores.csv` | `numbers.csv`, `runs.csv`, `by_group.csv` and `README.md` in `--out` |
| analyze | `tsbench.analyze` | `tsbench analyze effort` | transcripts, sidecars, `scores.csv`, `metrics/consistency.csv` | `runs.csv`, `by_group.csv`, `timeouts.csv`, `tasks.csv` and `README.md` in `--out` |
| release | `tsbench.release` | `tsbench release gate` | the git tree | pass / fail |
| publish | `tools/build_results.py` | `uv run python tools/build_results.py --repo REPO --plan NAME --rules FILE --doi DOI [--source DIR]` | the scored verified copy of a finished plan, a file of path replacements outside the repository | `results/`: the run folder with machine paths replaced, `REDACTIONS.csv`, `images/`, `code-snippets/`, `analysis/`, `SHA256SUMS`; fails when the rescored copy differs or the text gate finds a hit |

`tsbench report render` is an alias of `tsbench report views`.

## One run set on disk

```
RUNS/                                   a run set: one `tsbench run` output folder
  README.md                             what was run, when, how many runs, cost, how to re-run
  run_set.json                          {"title": one line}: the name shown on pages and figures
  inputs/
    commands.sh                         the exact commands (key VALUES never written, only variable names)
    plan.jsonl                          the plan that was executed (sealed header only for a confirmatory plan)
    hashes.json                         task set, plan_id, prompts, answer schemas, sandbox settings, B stack, versions
  MANIFEST.json                         machine record of the run (versions, pins, counts, reported models)
  system-prompts/system-prompt-<sha16>.txt   the system prompt text of the plan, as the model got it
  <model>/<condition>/<effort>/<task>-k<i>.jsonl        one transcript per run (stream-json, verbatim)
  <model>/<condition>/<effort>/<task>-k<i>.meta.json    its sidecar (argv with placeholders, flags, cost, timing)
  scores.csv  rates.csv                 after `tsbench score --runs RUNS`
```

## The hash chain

`tasks.sha256` (task set) → `plan_id` (hash of the run records, which carry the task and prompt hashes) → transcripts
(named by run id, listed in `MANIFEST.json`) → `scores.csv` → figures (`.source.csv` + provenance `.json`). A change
anywhere upstream changes every hash below it.

## Seeing it without running a model

The demo run set (fake claude) is a small pilot run set made with `tsbench run --dry-run`: no key, no network, no
cost. `tests/demo_runs.py` builds it for the tests that need a run set, and `tools/render_mock.sh` builds it into
`OUT/runs` (default `OUT` is `mock-site`) and then draws every figure (`accuracy_by_model`, `accuracy_by_class`,
`literature_parity`, `efficiency`, `code_listing`) and renders every report page from it into `OUT/`. A figure without
data in the run set is skipped; with the demo run set that is `code_listing`. `tools/render_mock.sh --runs DIR`
renders a copy of `DIR` instead. No run data is stored in the repository.

`tsbench report full --runs DIR --out REPORT.html` builds one fact page: figures, tables and numbers, no paragraphs
and no interpretation. A sticky top bar holds six tabs and a theme switch (System,
Light, Dark; the choice is kept in the browser when it allows). Under the title, one line names the report version, the
task-set hash of the split and every code commit of the run sets; chips name the model, the endpoint, the split, the conditions, the effort, k, the
runs, their dates, the oracle and the commit. Each tab has a table of contents of three levels on the left (sections,
sub-sections, figures, tables and tasks); below 900 px it is a fold-out above the tab.

Every model of the run sets stands on the same pages, in one order on every page (`report.base.model_key`: Haiku,
Sonnet, Opus, then the others by id). There is one layout and one table of contents per tab. With several models the
tab Models opens its Overview with a table of the models (the endpoint, the runs, k, the share correct per condition
with interval, C − A and C − B with interval); every table has a column Model, a task or a published system has one row
that holds a line per model, and every figure is its all-models version on one scale: a band per model where the figure
can hold it (share, paired differences, outcome and error categories, error size, characters per tool), a bubble chart
of median output tokens against the share correct (one bubble per model and condition, area = runs), a heat map of the
classes per condition, and one panel per model for the subsets, the call paths, the transitions, the cost map, the
ledger and the spectra. The colour of a condition is the same on every page. The model chip counts the models and the
run chip adds up the runs. With one model the tables have no column Model and the figures are those of one run set.

The page is one file: it holds every image and every code block of the runs, whole, and the per-run figures, and may
reach 100 MB; the images and code of a run card are copied in when its class is opened. `--page-budget MB` limits what
the images and figures take; beyond it they are only linked to their file beside the page. `--publication`, implied
by the confirmatory split, refuses to write a page with a link to a local file (exit status 2).
`--images results/images` adds what a run left outside its folder, from `<run set>.index.csv`; a file that is not what
the index says stops the build.
`--redactions results/REDACTIONS.csv` is for a page built from the published copy of a run set, whose machine paths were
replaced: a transcript whose hash is the logged published one and whose logged original is the hash of the manifest
counts as matching, and the page says how many went through the replacement.

`tsbench report full` and `tsbench report dashboard` read the pilot split unless `--split confirmatory` is given. A
confirmatory run set is refused without `--i-have-preregistered <DOI>`, and a run set that records another split than
the one asked for is refused too (exit status 2). A confirmatory page names the split and the DOI in its header and
shows the preregistered tests of each run set that holds `hypotheses.json` (`tsbench stats hypotheses`): the primary
family with its Holm p values, the H1 tests and the McNemar tests, without a multiplicity correction.

The dashboard and the full report read `scores.csv` as written. When a run set holds transcripts that have no row in it
(runs that landed after `tsbench score`) or whose transcript was overwritten since (its hash differs from the
manifest), a note names the count and says to run `tsbench score` again; the first kind is in no number. The figures
score such a run set in memory instead and say so in its notes. `tsbench report coverage` counts a repetition k once
per cell, even when several run sets hold it, and an evaluable copy of a run wins over a not-evaluable one. The report pages share their small rules (not-evaluable runs,
`True`/`TRUE`/`1` cells, medians, the share with its task-clustered bootstrap interval, the harness categories, the
pilot hash) in `tsbench/report/base.py`.

A view covers the tasks the model ran. A task with no evaluable run under a condition (all its runs ended in HTTP 429
or an API error, or the run stopped first) is left out of that condition: it adds nothing to k or n of the class
marks, the class intervals and the Classes table, and the UpSet figure leaves it out of every subset and says how many
tasks it left out. A condition with no evaluable run of any task is not drawn: the Classes figure, the task ledger and the
UpSet figure have no marker, column, row or set size for it, never a `0 of n`. A condition with runs in other classes but none in a class says `no run` there (Classes figure, task ledger head and tooltip, Classes table), never `0 of 0`. The run window, the counts and the flagged runs of a run set that was continued with `--resume`
are read from `MANIFEST.json` and every `MANIFEST.prev-*.json`. The cost of a model that is not a Claude model (a
gateway run) is the list price Claude Code assumes for an unknown model, not a real cost: the cost table says "no
real cost (gateway)" and the cost axis and the cost map are left out. `tsbench explain` names the answer source the
scorer found (`structured_output`, `rescued_tool_call` or `text_json`) and prints the answer it scored.

- Models: share correct per condition with n and 95 % interval, paired differences with interval, discordant counts
  and exact McNemar p (an exact p below 0.0005 reads `< 0.001`); outcome categories (`tsbench.score.taxonomy`, folded); size of the errors in units of the tolerance (a fit answer with a required value missing has no mark: the row says `n 30 of 35` and a data note counts them);
  tool use (the 12 most frequent call paths of B and C and one row for all other paths, so the runs add up; the text
  each tool returned); cost (medians, USD, every run across all measures).
- Tasks: one row per class (definition, n, oracle, tolerance, tasks solved per condition); the task ledger (the bar and number of a cell come from the runs on the side of its verdict, so a task marked not solved never shows the value of a correct run; a curve bar is the scorer's `curve_tol_ratio`, a pairing share is 0 when the ground term is wrong); one table
  per class with one row per pilot task (`id="task-<id>"`): given, asked, reference, source with DOI, tolerance, the
  prompt in a fold-out, and the answer of each condition with its outcome and a link to its run card. With k > 1 the answer is that of one run, the first on the side of the verdict, and the cell names it (`run k2`); the link opens that run's card.
- Published spectra: per system the bands, the source (DOI link and table), the published values, the oracle fit, the
  tolerance and each answer; the published value and each answer against the oracle fit.
- Code checks, with `--coverage COVERAGE.json` (`pytest.log` beside it) and `--mutation DIR [DIR ...]` (folders of
  `<shard>/<shard>.json` from `tools/ci/mutation.sh`, merged): tests, line coverage (and coverage.py's own total),
  mutation score; per folder, package, module and function; mutants per shard and module; surviving mutants with
  their changed lines, listed once per function. The module table and the table of surviving mutants show the first
  15 modules (and 3 functions per module); a last row adds up the rest, so each column matches the totals. A shard that counts more survivors than its JSON lists gets a row "shard NAME: N survivors not listed", so the table adds up to the survived count of the Mutation score row. A shard folder without its `<shard>.json` (still running, crashed or timed out) is not a result: a data note names it. A package without a mutation result shows as "not mutated", never as zero.
- Gallery and code: the Tanabe–Sugano diagrams made in the runs; the run cards, one closed block per class; the code of
  every B and C run, each in a closed block; the B solution path per run (answer number, the step that printed it, its
  code and its output, from `tsbench.score.solution_path`).
  Each transcript is parsed once per build: the scoring of a run set without scores.csv, the facts and the gallery
  read it through one reader (`score.artifacts.TranscriptCache`, which keeps up to 512 MiB of transcripts; a larger
  set is parsed again past that). A run without a tool call or image gets an empty `calls.json` in its
  `.code` folder, so the next build skips it. The solution path finds the numbers of a step's output with the scanner
  of the traced-number metric: a number with thousands separators (`2,033.6`) is one value, and values are absolute.
  NaN and infinite numbers in an answer are skipped.
- Method and platform: identity, protocol, statistics (with the class intervals), provenance of every figure and
  table (each file with its sha256 and the result of its check, for example "149 of 150 recorded hashes match" for the
  transcripts of every run set), exclusions and limits (`report/method.py`; the limits count the task-by-condition cells with fewer evaluable
  runs than the planned k, the runs missing for it and the rescued answers; the runs not started are those of the last invocation, and
  the stops of the earlier invocations are counted per reason in a row of their own); where the runs ran (values the records do not hold show as "not
  recorded"; the endpoint and the client version stand there, the effort in the run settings, each once), the run
  schedule (for a model that is not a Claude model it draws no cost: Claude Code prices it at Claude list prices; a
  run whose sidecar says `cost_unknown` has no cost and counts under "cost not recorded"), the files of the first run set with the hash chain, a table of the hash links of every run set
  that names the links that do not match, and the data notes.

Where each figure sits, its width and its caption are data in `report/full.py` (`TABS`, `PLACEMENT`): a figure is
960 px (full) or 464 px (half) wide and drawn 1:1 in a frame that scrolls sideways on a narrow screen, and its caption
is the one question it answers. The last section of a tab with figures, "All figures", links every figure of the tab.
`report/facts.py` and `report/method.py` read the run sets and the quality folders and return every number;
`report/svg/` turns them into static SVG (one module per chart family, pure functions, no script), styled by
`templates/svg.css` with the page tokens, so dark mode needs no second drawing. The dark tokens, also those of the
theme switch, apply on screen only: a printed page stays light. Coverage and mutation use a
green–orange scale. The page works without JavaScript: every tab is shown one below the other and every link is a
plain anchor. With the inline script one tab shows at a time; an address `#<tab>`, `#<tab>/<id>` or `#<id>` picks the
tab and opens the fold-outs around the target; the table of contents marks the current section; the run cards get
copies of their images and code. Without the script every model view is shown, each opened by a line "Model:
<name>". `tests/report/test_full.py` checks the page for one model and for two: the placement, the table of contents,
the widths, unique ids, every internal link, the views, the switch and the comparison, no text node outside tables, captions and code longer than 25 words, and no
"Figure N". `--no-gallery` leaves out the largest part. The single pages (`dashboard`, `comparison`, `literature`,
`coverage`, `gallery`, `quality`) are built from their own macros. Every share correct on the full report, the
dashboard, the comparison page and the literature page carries the same 95 % interval: the task-clustered bootstrap
(`core.intervals.cluster_bootstrap`, tasks sorted by id and resampled with their runs kept together). The live overview
chart of the gallery page is the exception: it filters runs in the browser and draws a run-level Wilson interval, which is
descriptive and treats the runs of a task as independent. `docs/methods.md` stays the maintainer reference and
is linked, never rendered.

## CI pipeline

`.gitlab-ci.yml` is a thin wrapper. All logic lives in `tools/ci/*.sh` (bash 3.2+, runs on macOS and Linux), and `.github/workflows/ci.yml` calls the same scripts.

**No real model call ever happens in CI.** Every `claude` interaction is the fake (`src/tsbench/run/fake_cli.py`, selected by `tsbench run --dry-run`). Tests that need a real `claude` or docker skip themselves. `guard_no_keys.sh` runs first in every script and fails the job if any of the six names in `conditions.sandbox.KEY_VARS` (`ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `TSMCP_ANTHROPIC_API_KEY`, `GWDG_API_KEY`, `GWDG_AI_API_KEY`, `LITELLM_MASTER_KEY`) is set (even empty); a test keeps the shell list equal to that tuple, so a stray CI/CD variable cannot cause a bill.

Image: `ghcr.io/astral-sh/uv:python3.13-bookworm-slim`. The venv is `.venv` at the repo root (the runner looks for `.venv/bin/tanabesugano-mcp`). The uv cache (`.cache/uv`) is cached by the hash of `pyproject.toml`.

The dev tools are optional extras in `pyproject.toml`, not runtime dependencies: `lint` (ruff, ty, pre-commit,
repo-release-tools), `mutation` (mutmut)
and `trace` (viztracer). CI installs only the `test` extra (`tools/ci/setup.sh`). `lint.sh` calls ruff through `uvx`, so
the `lint` extra is for local use. A full local set is `uv sync --extra test --extra lint --extra mutation --extra trace`.

### Jobs

| Job (stage) | Script | What it proves | Local run |
|---|---|---|---|
| `lint` (lint, allow_failure) | `lint.sh` | ruff findings (report-only), `bash -n` and `shellcheck` on `tools/*.sh` and `tools/ci/*.sh`. Missing tools are skipped. | `bash tools/ci/lint.sh` |
| `test` (test) | `test.sh` | `pytest tests` passes (without the browser test); JUnit XML and (if pytest-cov installs) coverage XML land in `build/ci/reports/`. | `bash tools/ci/setup.sh && bash tools/ci/test.sh` |
| `browser` (test) | `browser.sh` | `tests/report/test_motion.py` passes in headless Chrome: the motion of the report pages never changes a figure, and a bar segment of a dashboard model card shows exactly its runs. See [Browser test](#browser-test). JUnit XML in `build/ci/reports/junit-browser.xml`. | `bash tools/ci/browser.sh` |
| `e2e-dry` (e2e) | `e2e_dry.sh`, `check_e2e.py` | The full mocked pipeline works end to end: regenerated tasks reproduce `tasks.sha256` and `tasks.jsonl`; `plan build` + `plan validate` (pilot, 2 models, A,B,C, `--limit 3`, k=1); `tsbench run --plan --dry-run`; score; score report; `report views`; dashboard; `hypotheses --allow-incomplete`. Asserts the expected files and `MANIFEST` with 0 aborted. Artifacts (1 week): `report.html`, `views/`, MANIFEST, rates and scores CSV, plan. | `bash tools/ci/e2e_dry.sh` (output in `build/ci/e2e/`, override with `TSCI_E2E_DIR=build/ci/<name>`) |
| `readme-smoke` (e2e) | `readme_smoke.sh`, `readme_smoke.py` | README shell blocks whose first line is `# ci: dry` run in a temp copy of the repo (the `.venv` is symlinked in, API keys removed). Unmarked blocks are listed as skipped, never run. | `bash tools/ci/readme_smoke.sh [--json]` |
| `no-pilot` (gate) | `gate_no_pilot.sh` | No private material is tracked or in `git archive HEAD` (`tsbench release gate`): no `pilot/`, `seed/`, `analysis/` or `.claude/` folder, no `.env` file, no forbidden text, and none of the names in the CI variable `TSBENCH_GATE_DENY` (a secret on GitHub; a hit prints as `***`). Needs `git` in the image (the GitLab default installs it). | `bash tools/ci/gate_no_pilot.sh` |
| `confirmatory-guard` (gate) | `gate_confirmatory.sh` | `tsbench run --split confirmatory` without a preregistration DOI exits 2 and writes no MANIFEST. | `bash tools/ci/gate_confirmatory.sh` |
| `gitleaks` (gate) | `gitleaks.sh` | No secrets in the full git history (`gitleaks git --no-banner --redact`, falls back to `detect` on older versions). Uses the `zricethezav/gitleaks` image with `GIT_DEPTH=0`. | `bash tools/ci/gitleaks.sh` (needs `gitleaks` on PATH) |

The unit tests of the helpers are `tests/tools/test_*.py` and `tests/test_ci_pipeline.py` (pipeline structure, guard behaviour). The `test` job runs them with all other tests.

### Browser test

`tests/report/test_motion.py` checks what the string tests of the templates cannot: the JavaScript of the report
pages. It builds the dashboard, comparison and literature pages of a run set made with the fake claude, a
functional-test overview and a quality page in a temporary folder and opens each in headless Chrome. It drives Chrome over the DevTools protocol on
its WebSocket (`websockets`, in the `test` extra). No Playwright and no Node are needed.

- Every `figure .plot svg` has the same markup under `prefers-reduced-motion: reduce`, after all staged motion has
  played, and right after `TSMOTION.finish()` or a `beforeprint` event while motion runs. Save SVG and printing call
  these. Figura's random `jfs-clip-*` ids are numbered in order before the comparison.
- A click on a bar segment (`rect[data-k]`) of a dashboard model card leaves only the rows of `#runtable` with that
  model, condition and outcome visible. Their number is the count of the segment. "Show all runs" brings every row back.

Chrome comes from `TSBENCH_CHROME` or the first of `google-chrome`, `chromium` (and their other names) on `PATH`.
Without one the test skips with that reason. `browser.sh` sets `TSBENCH_REQUIRE_CHROME=1`, so in CI a missing Chrome
fails the job. The GitHub runner has `google-chrome`. On the GitLab image, `browser.sh` installs Debian's `chromium`
with `apt-get`. The `test` job leaves the file out, so it runs once.

### Marking README blocks

Put `# ci: dry` as the first line of a fenced `bash`/`sh` block to have it executed in CI. Only mark blocks that need no key, no network, no docker and write nothing outside the working copy.

### GitHub Actions mapping

| GitLab | GitHub Actions |
|---|---|
| `image: ghcr.io/astral-sh/uv:...` | `runs-on: ubuntu-latest` + `astral-sh/setup-uv` + `actions/setup-python` (3.13) |
| `cache: .cache/uv` | `setup-uv` with `enable-cache: true` |
| `script: bash tools/ci/setup.sh` etc. | `run: bash tools/ci/setup.sh` etc., unchanged |
| `artifacts: paths, expire_in: 1 week` | `actions/upload-artifact` with `retention-days: 7` |
| `artifacts:reports:junit` / coverage | upload the XML as an artifact or use a test-report action |
| `gitleaks` job with `GIT_DEPTH: 0` | `actions/checkout` with `fetch-depth: 0`, then `bash tools/ci/gitleaks.sh` (gitleaks binary or `gitleaks/gitleaks-action`) |
| `stages` | `jobs` with `needs:` |

### GitHub Actions workflows

`.github/workflows/ci.yml` runs the same jobs as `.gitlab-ci.yml` on every push to `main` and every pull request, with
the same scripts. Each job starts with `guard_no_keys.sh`, has a `timeout-minutes` of at most 60 and reads the
repository only (`permissions: contents: read`). The only secret is `TSBENCH_GATE_DENY`, which the `no-pilot` job reads.

`.github/workflows/mutation.yml` runs mutation testing with mutmut, report-only. It never runs on push or pull request:
a full run takes hours. It runs every Sunday at 02:17 UTC and on request (`workflow_dispatch`, input `only` for a comma
list of shards).

- **Shards.** `tools/ci/mutation_shards.json` lists the shards: source paths and the tests that cover them. Each shard
  is one matrix job (`tools/ci/mutation_report.py matrix`), and the jobs run in parallel.
- **Time limit.** A job on a GitHub-hosted runner stops after 6 hours. Each shard job has a timeout of 350 minutes. If
  a shard comes close to it, split it in the shard file, for example one module per shard.
- **Self-hosted runner.** The repository variable `MUTATION_RUNNER` sets a runner label, for example a self-hosted
  machine without the 6-hour limit (the job token still expires after 24 hours). `MUTATION_TIMEOUT_MINUTES` sets the
  timeout. Use a self-hosted runner only for this workflow, which never runs code from a fork.
- **Report.** `tools/ci/mutation.sh` runs one shard on a `git archive HEAD` copy and writes `<shard>.json` with every
  survivor and its diff. The `report` job merges all shards into one table in the job summary: score = killed /
  (killed + survived). Mutants that no selected test reaches are counted under *no test*: they are untested code, not
  a pass.
- **Test selection.** mutmut runs the tests inside `mutants/`, which has no `.venv`. The script links the copy's
  `.venv` there, because the sandbox probe tests need `<repo>/.venv/bin/python`. Only the tests that read the git
  checkout or the docs tree are deselected, each by its full test id.

Local run of one shard: `bash tools/ci/setup.sh && bash tools/ci/mutation.sh score "src/tsbench/score" "tests/score"`
(output in `build/ci/mutation/score/`).

`tsbench report quality` puts coverage and mutation score before and after a change on one page: line coverage per
package and per module from two coverage.py JSON reports (`coverage json`), and the mutation score per lane from
mutmut result files. Files named `test_*.py` and `conftest.py` are left out; `--renames` maps old module paths to new
ones. `uv run tsbench report quality --help` lists the inputs.

## Local git hooks

`.pre-commit-config.yaml` holds the local git hooks. Install them once per clone:

```bash
uv sync --extra test --extra lint
uv run pre-commit install --hook-type pre-commit --hook-type pre-push
```

Every hook is `repo: local` with `language: system`. Its entry is `uv run --frozen ...` or `bash tools/ci/...`, so
pre-commit and every tool it calls come from `uv.lock`; the config pins no `rev` and pre-commit builds no environment
of its own. `tests/test_hooks.py` checks this.

- **pre-commit:** `guard_no_keys.sh`; ruff check on the staged Python files; ty check on the staged Python files;
  gitleaks on the staged changes (`tools/ci/gitleaks_staged.sh`); `tsbench tasks verify` on every commit.
- **pre-push:** `rrt doctor` and `rrt eol`.

ty checks the staged files against `ty-baseline.json`, the findings the tree already had, so the hook fails on new
findings only. Refresh the baseline with `uv run --frozen ty check --baseline ty-baseline.json --update-baseline` only
when a finding is accepted. `uv run ty check` without `--baseline` still lists every finding.

gitleaks is a Go binary and not in `uv.lock`. Its hook runs when `gitleaks` is on PATH and prints a skip message
otherwise; the CI job `gitleaks` scans the full history either way. A `.gitleaksignore` names findings by commit
fingerprint, so `.gitattributes` keeps such a file out of `git archive`.

repo-release-tools (`rrt`) runs only its read-only checks. No hook calls `rrt tag`, `rrt release` or a real
`rrt bump`: tags and releases are not made by a hook.

Run every hook by hand with `uv run --frozen pre-commit run --all-files` (add `--hook-stage pre-push` for the push
hooks). `git commit --no-verify` skips them.
