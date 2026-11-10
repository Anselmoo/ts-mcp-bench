# Results

Data and results of the confirmatory study, preregistered as 10.5281/zenodo.23889782. `SHA256SUMS` lists the sha256
of every file below this folder.

| Plan | Models | Runs | State |
|:-|:-|-:|:-|
| 1 (primary) | claude-haiku-5-5, claude-sonnet-5-5, claude-opus-5-5 | 1485 | complete, scored, primary family tested |
| 2a (secondary) | gemma-4-31b-it | 495 | complete, scored |
| 2b (secondary) | qwen3-30b-a3b-instruct-2507 | 495 | complete, scored |
| 2c (secondary) | qwen3.5-397b-a17b | 495 | complete, scored |

2970 evaluated runs in all. The secondary family (plans 2a, 2b and 2c) is tested together, in
`confirmatory/secondary-family/`.

## Layout

- `confirmatory/preregistration/` the published preregistration and sealed plans, and the Zenodo record metadata.
- `confirmatory/plans/` the clear plan of each run plan: every run record with its task prompt (sent to the claude CLI
  on stdin), system prompt, command line and answer schema; `SHA256SUMS`.
- `confirmatory/<plan>/` the run folder as written by `tsbench run`: one transcript (`.jsonl`) and one sidecar
  (`.meta.json`) per run, earlier attempts of retried runs (`.attemptN.`), one manifest per invocation
  (`MANIFEST.prev-*.json` for all but the last), the PNG/SVG files a run left in its working folder (`.artifacts/`),
  `README.md`, `run_set.json`, `run.log` (the runner's console output), `logs/`, `inputs/`, `system-prompts/`, the
  sandbox probe, `plan.sealed.json`, and the scored tables `scores.csv`, `rates.csv`, `metrics/` and, for plan 1, the
  primary family `hypotheses.json`. The `plan.sealed.json` of a run folder is the copy sealed again when the plan
  started; it differs from the copy in `preregistration/` only in `created_utc`, and the `plan_id` is the same.
- `confirmatory/secondary-family/hypotheses.json` the secondary family of plans 2a to 2c, as preregistered: H2 (C
  against B) for each of the three models with Holm over these three tests, H1 (C against A) and the McNemar tests
  without correction, and the efficiency ratios. Built with `tsbench stats hypotheses --family secondary` from the three
  `scores.csv` and `rates.csv` (complete layers k = 1 to 3, 55 tasks).
- `confirmatory/reports/` the reports, one self-contained page each: `all/` for all four plans and six models, and one
  folder per plan; each with `report.html.zip`, `dashboard.html` and `BUILD.md` (code and commands). A report holds
  every image of its runs and is stored zipped: `report.html.zip` holds the one file `report.html`. A file named
  `<name>.html.zip` is always one zipped HTML page; a plain `.zip` would hold a folder.
- `images/<plan>/` every image of the runs, one folder per run, with an index: files harvested from a run's working
  folder, images returned by a tool, and one image recovered from the shared sandbox temporary folder (its sha256
  equals the hash the run reported).
- `code-snippets/<plan>/` the code of every condition-B run that called Bash (`tsbench analyze snippets`): each Bash
  command exactly as executed (`step-NN.sh`) and each heredoc body (`step-NN-<target>.py` or `.txt`), machine paths
  replaced as below, with `index.csv` (run, step, kind, file, lines, sha256, tool_use_id, exit, is_error, target).
  Snippets of retried attempts are left out.
- `analysis/<plan>/` offline analyses of the published run folder: `strategy/` (solution strategy per run), `errors/`
  (failing tool steps and recovery), `provenance/` (where each answer number came from), `effort/` (thinking tokens,
  time, turns and the wall limit), each with its own README, and `paths/` (`tsbench score path`: one `.path.json` per
  run with the code that ran, in order, what it printed and which step printed each answer value; `paths.csv` one row
  per run).
- `sandbox-temp/` files the models wrote into the sandbox temporary folder during condition B, moved here from that
  folder: scripts, arrays and intermediate results (`files/`, 128 files). The folder was shared by every claude process
  of the operator's account, so a file is kept only when the transcript of a run names it and its last write falls in
  that run's time: all 128 files are from runs of plan 1. No transcript of plans 2a, 2b or 2c names a file in that
  folder. Empty files, caches, CLI folders and the files of other processes are left out. `index.csv` gives size, hash,
  time of the last write, the run, and the snapshot of the folder it was taken from (three snapshots: 4, 7 and 10
  November; a file a later run overwrote would keep each version, `files-earlier/`, and none was).

## Machine paths and names

Machine paths, the operator's session folder names and the operator's account name in transcripts and logs are
replaced by fixed placeholders: `<HOME>`, `<B_VENV>`, `<operator-session-folder>` (also for the session id in a CLI
state file name in a listing of /tmp), `<SANDBOX_TMP>` for the sandbox temporary folder (in two lines of one listing
of /tmp the folder name alone), and `<USER>` for the account name (owner and group columns of `ls -l`,
`pytest-of-<USER>`), in the style of the placeholders the runner writes into its manifests. `REDACTIONS.csv` lists
every changed run-folder file with its sha256 before and after and the count per placeholder; nothing else in a file
is changed. The `transcript_sha256` column of `scores.csv` and the manifest keep the hashes of the original
transcripts. Scoring the published transcripts again gives the same answers and verdicts. Code snippets and analyses
are built from the published run folders.

Left out of the run folders: the operator's wrapper scripts and their logs (`run.sh` of plans 2a to 2c; for plan 1
`resume_after_budget.sh`, `set_budget_after_layer1.sh`, `resume.log`, `set_budget.log`, which carry out the budget
change below), and lock and pid files.

## Deviation from the preregistration

Plan 1 budget guard raised from USD 125. Decided on 2026-11-03 at 473 of 1485 runs, before any score was computed,
on cost grounds only; the amount, USD 155, followed by a fixed rule from the cost of the first layer (3 x cost x 1.1).
The guard stopped plan 1 at run 1463 (USD 125.18); the remaining 22 runs completed with the new guard. Booked total
USD 128.52.

## Operational events

- Plan 2a: one resume attempt recorded `git_dirty` yes (commit unchanged): untracked data folders were in the
  checkout. It executed no run.
- Plan 2c: on 2026-11-07 the claude CLI on the machine's PATH was updated from the pinned 2.1.316 to 2.1.319. The next
  resume stopped before any run, because the runner checks the pinned environment (exit 2). Plan 2c resumed on
  2026-11-08 with the pinned 2.1.316 first on PATH; every run of all four plans ran with 2.1.316.
- Plan 1 `hypotheses.json` was computed again on 2026-11-07 (with the efficiency ratios); the run data are unchanged.
- The CLI writes `[claude-code:unrecognized_model]` to stderr in every gateway run (plans 2a to 2c): it does not know
  the model names of the gateway. All these runs are evaluable.

## Limitations of the recorded data

- The runner deletes each run's working folder after the run and keeps its top-level PNG/SVG files and the last 2000
  characters of the CLI's stderr. One image a run saved in a subfolder is lost; its reported sha256 is in the answer.
- In condition B the sandbox temporary folder was shared by all runs; a run could list files of other runs there, and
  two runs listed the host's /tmp (names of other programs' temporary files). These listings are kept as recorded, with
  the replacements above. The files that matter are in `sandbox-temp/` (see Layout); the code of every run is in
  `code-snippets/`.
- The runner's temporary home and claude configuration folders are deleted after each invocation, so CLI-side logs
  (for example the MCP server's stderr) are not kept; tool calls and results are in the transcripts.
- Runs that reached the 15-minute wall limit count as wrong and their cost is not booked: 28 in plan 1, 2 in plan 2a,
  16 in plan 2b, 1 in plan 2c (`analysis/<plan>/effort/timeouts.csv`).
- Not-evaluable attempts (HTTP 429, the gateway's daily cap) were retried and replaced by a new run; the attempt is
  kept. Plan 1: 0. Plan 2a: 7, all of one run (condition C). Plan 2b: 32, of two runs (A 21, B 11). Plan 2c: 35, of
  three runs (A 13, B 22). Every quota stop ended in one such attempt; each plan was resumed until complete. All
  evaluated runs are complete: 495 of 495 per plan and model.
- Tool use (sidecar flags, `analysis/<plan>/effort/runs.csv`): condition-B runs that called no tool and answered
  directly (`b_no_tool_use`): plan 1 158 of 495 (haiku 29, sonnet 77, opus 52 of 165 each), 2a 48, 2b 131, 2c 137 of
  165. Condition-C runs without an MCP call (`c_no_mcp_call`): plan 1 85 (haiku 13, sonnet 33, opus 39), 2a 8, 2b 19,
  2c 5; in 2b two C runs had only failing MCP calls (`c_all_mcp_errors`). In every such run the tool was offered.
- Answers that name an image which does not exist: in plan 2b, 6 diagram answers of condition C; in plan 2c, 13
  diagram answers of condition A (no tools at all) and 3 of condition C. Neither condition has a tool that writes a
  file, so no such file exists, and the reported hashes are not of any image (for example the sha256 of empty input or
  patterns such as a1b2c3...). Images are never scored.
