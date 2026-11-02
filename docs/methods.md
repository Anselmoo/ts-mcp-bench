# Methods: task set, answers, runs, plan and metrics

This page fixes the interfaces shared by the task generator, the runner, the scorer and the statistics. A change
here changes every consumer, so it needs a reason. The stages and their files are in `pipeline.md`; the task classes,
oracles and tolerances per class are in `src/tsbench/data/tasks/rubric.md`.

Contents: 1 task set, 2 answer format, 3 runs, 4 run plan, 5 descriptive metrics, 6 run views and confirmatory
secrecy.

## 1. Task set

Task record file: `src/tsbench/data/tasks/tasks.jsonl`, one JSON object per line. It is task set **v2** (seed
`20261025`; 50 pilot and 55 confirmatory tasks in 14 classes). It is the only task set of this repository.
`load(split)` returns it, and the scorer refuses a run folder whose manifest hash or order, or whose `plan.jsonl`
prompts, do not belong to it.

| Field | Type | Meaning |
|---|---|---|
| `id` | str | `<split-prefix>-<class>-<nn>`, e.g. `P-closed_form-01`, `C-numerical-01`. Unique. |
| `split` | `"pilot"` \| `"confirmatory"` | Disjoint sets. No model sees `confirmatory` before preregistration. |
| `class` | `"closed_form"` \| `"experimental"` \| `"numerical"` \| `"numerical_hard"` \| `"racah_c"` \| `"tetrahedral"` \| `"out_of_scope"` \| `"crossover"` \| `"curve"` \| `"literature_all"` \| `"batch"` \| `"pairing"` \| `"diagram"` \| `"literature_new"` | The task class. `experimental` and `literature_new` have no confirmatory tasks (counts below). |
| `subtype` | str \| null | `"d3"` … `"d8"`, `"d4_crossover"` / `"d6_low_spin"` (numerical_hard: d4, d5, d6 × `crossover` \| `low_spin`), `"charge_transfer"`, `"jahn_teller"`. |
| `d_count` | int \| null | Electron count *as stated in the prompt* (for tetrahedral: the Td count). |
| `geometry` | `"Oh"` \| `"Td"` \| null | |
| `system` | str \| null | Literature system name (class `experimental`), else null. |
| `bands_cm1` | list[float] | Bands given in the prompt, ascending, rounded to 10 cm⁻¹ (synthetic) or as published (experimental). Empty for `crossover` and `curve`. |
| `prompt` | str | The user message. It states the situation, the bands and what to determine. It never names a tool and never contains the reference. |
| `required` | list[str] | Parameters that must be within tolerance: `["Dq","B"]`, `["Dq","B","C"]`, `["Dq"]` (crossover), or `[]` (out of scope, curve). |
| `reference` | `{"Dq": float\|null, "B": float\|null, "C": float\|null}` | cm⁻¹. Computed, never typed by hand. `crossover`: only `Dq` (B and C are inputs, in `params`). `curve`: all null (see `reference_curve`). |
| `tolerance` | `{"Dq": float, "B": float, "C": float\|null}` | **Relative** tolerance (0.02 = 2 %). `curve`: `{"Dq": null, "B": null, "C": null, "curve_abs": 0.3, "curve_rel": 0.03}`. |
| `oracle` | `"closed_form"` \| `"forward_model"` \| `"none"` | Where `reference` came from. (`crossover` and `curve` are `forward_model`: `crossover_dq` and `compute_point` of `tanabesugano`.) |
| `expect_out_of_scope` | bool | true: the correct answer names the model's limit and gives no Dq/B. |
| `answer_schema` | `"fit"` \| `"curve"` \| `"batch"` \| `"pairing"` \| `"diagram"` | Which schema in `src/tsbench/data/schemas/` the answer is enforced and scored with. `curve`, `batch`, `pairing` and `diagram` for the classes of that name, `fit` for all others (including `literature_all`). For `batch` the reference is `{"values": [{"input", "result"}, ...]}` and the tolerance `{"item_rel": 0.02, ...}`; for `pairing` it is `{"nodes": [...], "edges": [...]}` (details in `rubric.md`). |
| `params` | object \| null | The task-defining inputs that are not the reference: numerical_hard `{c_over_b, mode}`; crossover `{B, C}`; curve `{B, C, dq_over_b: [x1, x2, x3]}`; else null. |
| `reference_curve` | list \| null | curve only: nine `{dq_over_b, term, e_over_b}` points, three per Dq/B, ascending in energy within a Dq/B. |

Tolerances:
- Synthetic fit classes (`closed_form`, `numerical`, `numerical_hard`, `racah_c`, `tetrahedral`, `crossover`): Dq 0.02, B 0.05, C 0.10.
- `experimental`: Dq 0.05, B 0.10, C null.
- `curve`: every one of the nine E/B values within 3 % relative or 0.3 E/B absolute.

Counts (pilot / confirmatory), from `COUNTS` in `src/tsbench/tasks/common.py`, 50 / 55 in all:

| Class | Pilot | Confirmatory |
|---|---|---|
| closed_form | 2 | 0 |
| experimental | 2 | 0 |
| numerical | 3 | 6 |
| numerical_hard | 3 | 6 |
| racah_c | 3 | 5 |
| tetrahedral | 3 | 3 |
| out_of_scope | 3 | 4 |
| crossover | 3 | 4 |
| curve | 3 | 4 |
| literature_all | 10 | 18 |
| batch | 3 | 0 |
| pairing | 1 | 0 |
| diagram | 5 | 5 |
| literature_new | 6 | 0 |

Notes on the counts:
- `closed_form`, `batch` and `pairing` are drawn in their own streams, pilot first, and then left out of the
  confirmatory split (`CONF_DROPPED`).
- `literature_all`: 33 table systems minus 3 excluded for a fit at a bound; one third (per d-count) goes to the pilot;
  2 confirmatory systems that a pilot task of another class uses are removed, so no confirmatory system is a pilot
  system or appears twice. `build_tasks` asserts the number.
- `experimental`: the 4 confirmatory rows were all pilot or `literature_all` systems, so none is confirmatory.
- `literature_new` is pilot-only. It comes from `src/tsbench/data/literature/literature-spectra-2.csv`: 8 systems minus
  2 excluded (fit at the C/B bound).
- The file lists each split round-robin over the classes, skipping classes that are used up.

`tasks.sha256` has three lines, in `sha256sum` format:
```
<hex>  tasks.jsonl
<hex>  pilot
<hex>  confirmatory
```
The `pilot` and `confirmatory` hashes are taken over the canonical serialisation of that subset's records:
`json.dumps(rec, sort_keys=True, ensure_ascii=False)` joined with `"\n"`, plus a trailing `"\n"`, in file order.

Loading: `tsbench.tasks.load(split)` returns that split's records. It is the **only** sanctioned reader. Nothing prints
confirmatory records.

## 2. Answer format

Enforced by `--json-schema` and `src/tsbench/data/prompts/neutral.txt`, parsed by `src/tsbench/score/extract.py`.

There are five answer schemas, chosen per task record by `answer_schema`:
- `fit` (`src/tsbench/data/schemas/fit.schema.json`, byte-identical to `answer.schema.json`): every class but `curve`,
  `batch`, `pairing` and `diagram`.
- `batch`, `pairing` and `diagram`: structured output only, scored by `src/tsbench/score/batch_score.py`,
  `pairing_score.py` and `diagram_score.py`. Their answers and scores are described in `rubric.md`.
- `curve` (`src/tsbench/data/schemas/curve.schema.json`):
  ```
  {"points": [{"dq_over_b": <number>, "term": "<string>", "e_over_b": <number>}, ...], "reason": "<string>"}
  ```

The rest of this section describes `fit`. A `curve` answer is read from `structured_output` only (no text fallback). It
is correct iff the points, grouped by the task's Dq/B values (|difference| ≤ 0.01), number exactly three per Dq/B and
nine in all, and, with each group sorted by `e_over_b` and compared with `reference_curve` in ascending order, every
value is within `curve_abs` absolute or `curve_rel` relative (same 1e-12 slack as below). Term labels are
informational. The score row has `curve_max_rel_err` (largest relative error, empty when malformed),
`curve_tol_ratio` (the largest over the points of the error in units of the nearer of the two tolerances, so an answer
is correct iff it is at most 1; empty when malformed) and empty `dq/b/c`, `abs_err_*`, `rel_err_*` columns. Curve runs use `src/tsbench/data/prompts/neutral_curve.txt` as system
prompt, because `neutral.txt` asks for the `fit` line. Batch, pairing and diagram runs use `neutral_batch.txt`,
`neutral_pairing.txt` and `neutral_diagram.txt`. A `crossover` answer is a `fit` answer with the crossover Dq in `Dq`.

Every system prompt is the same in A, B and C; the conditions differ only in their tools. Line 3 of each prompt is one
sentence that allows the model to use whatever tools it has. The sentence names no tool and asks for none, so in A it
has no effect. Whether a model then uses Bash in B or the MCP server in C is part of the result: the
report shows the share of runs with a tool call beside the accuracy.

Every run passes `--json-schema <compact JSON of the schema of its task record>`, so Claude Code adds a built-in
`StructuredOutput` tool and the model delivers the answer by calling it. The result event then carries
`structured_output` (the answer object) and `result` holds the same JSON as text. The `fit` schema requires `Dq`, `B`,
`C` (number or null), `out_of_scope` (boolean) and `reason` (string), no other keys. Its sha256 (of the compact text)
is pinned in the run plan: the header's `pins.answer_schemas` holds the hash of every schema
(`pins.answer_schema_sha256` is the `fit` one), and each run record has `answer_schema` (the name),
`answer_schema_sha256` and `answer_format`. The runner takes `--json-schema` from the record and aborts if the planned
hash differs from the schema file.
- The scorer prefers `result["structured_output"]` when it is a dict with the keys `Dq`, `B`, `out_of_scope` and valid
  numbers; otherwise it falls back to the line rule below.
- Cost of the mechanism: it adds one model turn per run. The code does not test whether a gateway model supports
  `--json-schema`.

The prompt still asks for the final message to end with exactly one line of JSON (fallback channel), with energies in cm⁻¹:
```
{"Dq": <number|null>, "B": <number|null>, "C": <number|null>, "out_of_scope": <true|false>, "reason": "<short string>"}
```
- The fallback extractor reads the **last** line of the `result` event's `result` text that parses as a JSON object with
  the keys `Dq`, `B`, `out_of_scope`. `C` and `reason` are optional.
- The extractor tolerates code fences, and numbers given as strings.
- If no line parses, the outcome is `unparseable`: wrong, and counted separately.

Correctness (`src/tsbench/score/numeric.py`):
- `expect_out_of_scope == true`: correct iff `out_of_scope is true` and `Dq` and `B` are null.
- Otherwise: correct iff `out_of_scope is false` and, for every key in `required`,
  `|answer − ref| / |ref| ≤ tolerance[key]`. For tetrahedral tasks, `Dq` is compared by absolute value.
- A parameter that is not in `required` (e.g. `C` on a `closed_form` task) is reported with its error, but it never
  affects correctness.
- A transcript without a result event is incorrect (`has_result = false`, not `unparseable`). A result with
  `is_error = true` (`error_max_turns`, `error_max_budget_usd`, …) is incorrect, and its `result_subtype` is kept, so
  infrastructure limits stay separable from wrong answers.
- Scoring with `--split pilot` counts transcripts of tasks outside the split as `unknown` and never scores them.

## 3. Runs

### 3.1 Command, files and stream events

Command (the runner is `src/tsbench/run/runner.py`):
```
tsbench run --split pilot --models claude-haiku-5-5[,…] --conditions A,B,C \
  --effort medium --k 2 --budget-usd 10 --out runs [--dry-run] [--resume] [--limit N] [--gateway]
  [--i-have-preregistered <DOI>]    # required for --split confirmatory, else exit 2; a non-DOI value is refused too
```
- `--limit N` takes the first N tasks of the split, in file order.
- Transcript path: `<out>/<model>/<cond>/<effort>/<task_id>-k<i>.jsonl`, with `i = 1..k`. It is the raw stream-json
  stdout, one event per line, unmodified.
- Sidecar: `<same path minus .jsonl>.meta.json`, holding argv (the prompt elided), exit code, wall time, stderr tail,
  sandbox method, and flags. `permission_denials` is set when the result lists a denied call. In condition B,
  `b_no_tool_use` is set only when no Bash call ran: a call that a denial names (by `tool_use_id`) did not run.
- Manifest: `<out>/MANIFEST.json`.
- Scores: `<out>/scores.csv` (one row per transcript) and `<out>/rates.csv` (one row per model × condition × effort ×
  task, `rate` = correct/k; `k` counts evaluable runs only, see 3.4).

Stream-json events used. Real samples captured with no API key (zero cost) are in `src/tsbench/run/fake_cli_fixtures/`:
- `{"type":"system","subtype":"init","tools":[…],"mcp_servers":[{"name","status"}],"model":…,"claude_code_version":…}`:
  the first event that is not some other `system` subtype. With a key set, `claude` emits `system/ui_invalidate` before
  it. Anything other than `system` before init aborts the cell. A run killed before init costs 0, because init
  precedes the first API request.
- `{"type":"assistant","message":{"content":[{"type":"text","text"}|{"type":"tool_use","id","name","input"}]}}`
- `{"type":"user","message":{"content":[{"type":"tool_result","tool_use_id","content"}]}}`
- `{"type":"result","subtype":…,"is_error":bool,"result":str,"total_cost_usd":float,"usage":{…},"num_turns":int,"permission_denials":[…]}`:
  the last line.

`StructuredOutput` is an **output channel** present in every condition, not a capability. `check_init` requires it in
`tools` (its absence means `--json-schema` did not take effect, a mismatch) and ignores it for the rules below;
`compute_flags`, `n_tool_uses`, `n_mcp_calls`, `n_bash_calls` and `tool_use.py` do not count its calls.
A `tool_use` id that the stream repeats is one call. `thinking_tokens` is empty in `scores.csv` when the result event
does not report them; a reported 0 stays 0.
`--allowedTools` does not need to name it. The flags live only in `conditions.Condition.flags` and `STRUCTURED_TOOL`.

Expected init per condition (besides `StructuredOutput`):
- A: `tools == []`, `mcp_servers == []`.
- B: `tools == ["Bash"]`, `mcp_servers == []`; its python is the fixed venv-B stack (3.2).
- C: every tool starts with `mcp__tanabesugano__`, there is at least one tool, and
  `mcp_servers == [{"name":"tanabesugano","status":"connected",…}]`.

In every condition, `model` must equal the requested full model ID. Any mismatch aborts the cell.

### 3.2 Condition B: the fixed scientific stack

Code: `src/tsbench/conditions/b_stack.py`; pins: `src/tsbench/data/conditions/b-stack.txt`.

B's only tool is `Bash`, so its `python3` is the code interpreter the model gets. That interpreter is a **dedicated
virtualenv outside the repository**, not whatever `python3` the host has:
- Location: `~/.cache/tsbench/venv-B` (`$XDG_CACHE_HOME/tsbench/venv-B`), override `--b-venv DIR` or
  `TSBENCH_B_VENV`; a path inside the repository is refused. Same persistence convention as the matplotlib cache
  (`TSBENCH_MPLCONFIGDIR`).
- Content: exactly the `==` pins of `b-stack.txt` (numpy, scipy, sympy, matplotlib and their dependency closure; python
  minor as the repository `.venv`, 3.14). `tanabesugano` is never in it, and there is no pip: the venv is made with
  `python -m venv --without-pip` and filled from outside with
  `uv pip install --python <venv>/bin/python -r src/tsbench/data/conditions/b-stack.txt`. `tsbench env b-stack`
  creates it (idempotent) or repairs wrong pins; `--check` only validates.
- Validity (`ensure_b_stack`): installed versions equal the pins, the python minor matches, `import tanabesugano`
  FAILS, and numpy, scipy, sympy and matplotlib import. A venv with `tanabesugano` in it is an error and is not
  repaired.
- Stack digest: sha256 over the pin file and the sorted `name==version` listing of what is installed
  (importlib.metadata, run by the venv's python). The whole text of `b-stack.txt`, comments included, is part of the
  digest: an edit changes the digest of every plan built after it, and resuming an older plan reports pin drift.
- Runner: for condition B only, `<venv-B>/bin` is put FIRST on the child `PATH`. venv-B is the single virtualenv any
  child sees (see 3.3 for how the PATH is built).
- Sandbox probe: `PROBE_NUMPY` (`python3 -c "import numpy, scipy, sympy, matplotlib"` with the B `PATH`) must
  **succeed** (rc 0). `PROBE_IMPORT` (`import tanabesugano`) and `PROBE_PIP` (no pip in the venv, no network) must
  still **fail**. The full marker list is in 3.3. A probe record is reused only for the same claude version, settings
  hash, stack digest, probe script hash **and** auth mode. The probe model is `PROBE_MODEL` on the direct API. With
  `--gateway` it is the first of `gwdg-qwen3.5-397b`, `gwdg-qwen3-coder-next` that the plan has, else the first plan
  model by name; the order of `--models` never decides it. A probe that printed no marker at all (the model did not
  run the script) and went wrong in no other way is not evaluable (`passed: null`, `not_evaluable: "no_markers"`), like
  an API error: condition B does not run and `--resume` probes again.
- Recording: `MANIFEST.json` has `b_stack` = `{path: "<B_VENV>", bin: "<B_VENV>/bin", python, packages: {name: version},
  digest}` (`null` when B is not requested); the real location is never written. The plan header pins
  `b_stack_sha256`, every B run record carries the same `b_stack_sha256` (`schema_version` 4), `plan validate` checks
  the two agree, and a different digest at run time is pin drift (confirmatory aborts, the pilot records it in
  `pin_drift`). `plan build` with B and no valid stack: warning for the pilot, error for confirmatory.

### 3.3 Isolation

**Child PATH, built from scratch.** The parent's `PATH` is never inherited (`child_path` in `src/tsbench/run/env.py`).
A and C get `/usr/bin:/bin` plus the *resolved* directory of the `claude` binary (`os.path.realpath`; for a script
install, `#!/usr/bin/env node`, also the resolved directory of the interpreter). B gets `<venv-B>/bin` first, then the
same. The symlink's directory (e.g. `/usr/local/bin`) is never used. The run aborts if any `tanabesugano*`
executable is on the child PATH. The manifest records the literal PATH per condition as `child_path`
(`{"A": "/usr/bin:/bin:<resolved claude directory>", "B": "<B_VENV>/bin:/usr/bin:/bin:…", …}`), host
paths as placeholders.

**Sandbox filesystem (B).** `denyRead` holds the repository, the main checkout when the repository is a linked git
working tree, the **whole real home**, the folder of the key file (`TSBENCH_KEY_FILE`, default
`~/.config/tsbench/env`) and `~/.cache/pip` (both as `~` and spelled out in the real home), the harness's own `sys.prefix`
and its site-packages, and the site-packages of venv-B's base interpreter. `allowRead` re-opens only venv-B, its base
interpreter (the `home =` line of `pyvenv.cfg`, as written and resolved; B's `python3` reads its stdlib there) and the
matplotlib cache. Claude Code applies the narrower rule when read rules overlap (`code.claude.com/docs/en/sandboxing`,
"Configure sandboxing"), so these stay readable inside the denied home while an exact deny inside them
(site-packages) still holds. The run's temp dirs (`TMPDIR`, cwd, isolated `HOME`, `CLAUDE_CONFIG_DIR`) must lie
outside the real home; the run refuses otherwise. The network allow-list stays empty. The settings file is hashed
(`sandbox_settings_sha256` in the plan pins, the probe record and the manifest); it depends on the repository, home
and venv-B locations, so it differs between hosts. `plan build`, `run` and `doctor` hash the settings for the `--b-venv`
directory they are given, as the runner renders them. The code is `src/tsbench/conditions/sandbox.py`.

**Probe markers.** One script, one Bash call; every forbidden command has its output sent to `/dev/null`, only
`PROBE_<NAME> rc=<n>` lines are printed, and each path is tested by its own command (a marker printed several times
must have every rc right). The script names no host path: the repository and the real home reach it as
`$TSPROBE_REPO` and `$TSPROBE_RH` in the probe's environment only.

| Marker | Must | What it runs |
|---|---|---|
| CTRL1, CTRL2 | 0 | `echo`; `python3 -c "print(2+3)"` |
| PATHS | 0 | `$TSPROBE_REPO` and `$TSPROBE_RH` reached Bash and the real home is not `$HOME` (else the path markers below are vacuous) |
| KEYENV | 0 | `[ -z "${ANTHROPIC_API_KEY-}${ANTHROPIC_AUTH_TOKEN-}${TSMCP_ANTHROPIC_API_KEY-}${GWDG_API_KEY-}${GWDG_AI_API_KEY-}${LITELLM_MASTER_KEY-}" ]`: no model credential in B's environment; prints the rc only, never a value |
| NUMPY | 0 | `python3 -c "import numpy, scipy, sympy, matplotlib"` |
| HEREDOC | 0 | write a script with a heredoc and run it |
| IMPORT | ≠0 | `python3 -c "import tanabesugano"` |
| PIP | ≠0 | `python3 -m pip download --no-deps tanabesugano==2.0.0` |
| NET | ≠0 | `curl https://pypi.org/simple/tanabesugano/` |
| VENV | ≠0 | `<repo>/.venv/bin/python -c "import tanabesugano"` |
| READ | ≠0 | `cat <repo>/src/tsbench/data/tasks/tasks.jsonl` |
| TSBIN | ≠0 | `command -v tanabesugano`; `command -v tanabesugano-mcp` (one each) |
| HOMECACHE | ≠0 | `ls <real home>/.cache/uv`; `ls <real home>/.local` (those that exist) |
| HOMESECRETS | ≠0 | `ls <real home>/.ssh`; `cat` of `.config/gh/hosts.yml`, `.zsh_history`, `.bash_history` (those that exist; output to `/dev/null`) |
| LOCALHOST | ≠0 | `curl -m 5 http://127.0.0.1:4000/` (the LiteLLM port; meaningful only while something listens there: the record has `localhost_listening`) |
| APIHOST | ≠0 | `curl -m 5 https://api.anthropic.com`; `curl -m 5 https://chat-ai.academiccloud.de` (B itself must not reach the model APIs) |
| DNS | ≠0 | `python3 -c "import socket; socket.gethostbyname('example.org')"` |

Not probed (stated, not claimed): other Unix sockets, and `tsbench` package data installed outside the repository (the
harness site-packages are denied). The probe record holds `probe_script_sha256` (this host's script),
`probe_script_template_sha256` (every candidate path; the same on every host, pinned in the plan header as
`sandbox_probe_script_sha256`), `home_paths_tested` (relative names), `localhost_listening`, `auth_mode`
(direct/gateway: KEYENV tests a different variable in each), `child_path` and `transcript` relative to `--out`. A
record from an older probe script is never reused.

If KEYENV fails, B does not run. Two mitigations are documented by Claude Code and are deliberately not enabled by
default, so that the probe measures the configuration as it is: `sandbox.credentials.envVars` with `mode: "deny"`
(unsets the listed variables before each sandboxed command; `code.claude.com/docs/en/settings-reference#sandbox-credentials`)
and `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1` (strips credentials from every subprocess Claude Code starts;
`code.claude.com/docs/en/env-vars`). Enabling either changes the settings hash or the child env.

**Records hold no host identity.** Everything the runner and the probe write (`MANIFEST.json`, `*.meta.json`,
`sandbox_probe.json`) passes through the runner's `Session.record`, which replaces host paths by placeholders, longest
first: `<OUT>` (the `--out` dir), `<CFG>` (rendered settings and `ts.json`), `<ISO_HOME>` (the isolated HOME of the
run), `<B_VENV>`, `<REPO>`, `<CLAUDE>` (the `claude` binary), `<PYTHON>` (the fake's interpreter, dry runs),
`<B_BASE_PYTHON>`, `<TMP>`, `<HOME>` (the real home). `argv` therefore reads
`<CLAUDE> … --system-prompt-file <OUT>/system-prompts/system-prompt-<sha16>.txt … --settings
<CFG>/sandbox-settings.json`; the report shows the system prompt from the plan record, and for a sealed plan (no run records) from that file. `args.out`/`args.plan` are repo-relative when inside
the repository. `host` is the declared `TSBENCH_HOST_LABEL` (`host_source: "label"`), else
`sha256(hostname + salt)[:12]` with salt `TSBENCH_HOST_SALT` or the `plan_id`; `gethostname()` is never written. `USER`
and `LOGNAME` of every child are the constant `tsbench`. `tools/ci/check_e2e.py` fails the dry e2e on any
`/(Users|home)/<name>/` or the hostname in those records. Raw transcripts are not rewritten: what a model prints there
is what it saw (residual: B can still learn the login name through `id -un`; a dedicated run user removes it).

### 3.4 Limits, rate limits and rescue

1. **Rescue.** A run with no usable `structured_output` in its result event (`subtype` `error_max_turns` or
   `error_max_budget_usd`, or no result event at all) is scored on the LAST `StructuredOutput` tool call of its
   transcript whose input validates against the run's answer schema (`src/tsbench/data/schemas/<name>.schema.json`,
   checked with the validator of `src/tsbench/plan`); an invalid call is skipped. The answer is scored like any other.
   `scores.csv` has `answer_source` (`structured_output` | `rescued_tool_call` | `text_json` | `none`), `rescued`
   (bool) and `rescue_stop_reason` (the subtype, or `no_result`); `result_subtype` keeps the stop. There is no new path
   to "correct" in the taxonomy: a rescued answer is categorised by its content (a wrong one is `wrong_dq`, …, not
   `budget`), and analyses separate it with the `rescued` column. `tsbench report comparison` shows the number of
   rescued answers per set.
2. **HTTP 429.** (a) When a run ends in an `is_error` result with HTTP 429 (`is_rate_limited`), the runner waits and
   runs the SAME run again: 60, 120, 240, 480 s, each plus up to 25 % jitter, at most 4 retries.
   `TSBENCH_429_MAX_RETRIES` overrides the count, `0` turns it off. A 429 whose text says the cap is used up (`limit
   exhausted`, or a daily or monthly `limit reached`), or that asks for a wait longer than the longest backoff step, is
   not retried: the invocation stops at
   once with `stop.scope` `daily`, `monthly` or `unknown` and exits with 75. Each 429 attempt's transcript is kept as
   `<stem>.attempt<N>.jsonl` (not read by the scorer), with its images folder as `<stem>.attempt<N>.artifacts/` and its
   sidecar as `<stem>.attempt<N>.meta.json`; the transcript at the normal path is the last attempt. The
   sidecar has `retries: [{at, wait_s, status}]`, one entry per wait. (b) `compute_flags` gives a 429 result only the
   flag `rate_limited`, never `b_no_tool_use` or `c_no_mcp_call`. (c) The scorer marks a 429 run, and any other
   `is_error` result from the API with no model answer (a 5xx, `terminal_reason: api_error`), as not evaluable:
   `scores.csv` has `evaluable=False` and `not_evaluable_reason` `rate_limited` or `api_error`. Such runs are left out
   of `rates.csv` (`k` and `n_correct` count evaluable runs; a cell with none has no row) and of `summary_lines`. Turn
   limits, budget stops and timeouts stay evaluable (and wrong). Every report page and `tsbench explain` use this one
   rule (`tsbench.score.score.not_evaluable_reason`, called through `tsbench.report.base.not_evaluable`): a 429 as a
   number, as the string `"429"` or as `(429)` in the text, a 5xx, `terminal_reason: api_error` and `API Error:` text
   all end as "not evaluable: rate limit or API error", never as an evaluable failed run. (d) A context overflow is
   no infrastructure failure: an error result with HTTP status 400 or 413 (in `api_error_status`, or as `API Error:
   400` in the text, or no status at all) whose text says the context window or the request size was exceeded
   (`ContextWindowExceededError`, "maximum context length", "prompt is too long", "request too large", ...). The run's
   own prompt and tool output grew too large, so it is evaluable and wrong: `scores.csv` has `context_overflow=True`,
   the taxonomy category is `context_overflow`, and `--resume` keeps it as done (`runner.is_api_error` is false for
   it, also at zero cost). The rule is `tsbench.core.api_errors.is_context_overflow`, shared by the scorer and the
   runner. Only infrastructure errors stay not evaluable (HTTP 401, 403, 404, 408, 429 and 5xx); an HTTP 400 without
   overflow text stays `api_error`.
3. **No per-call budget.** `claude` gets no `--max-budget-usd` by default (a per-call cap can cut off a legitimate
   answer). `--budget-usd` is a run-set guard only: the runner never STARTS a run once the spent total reaches it, and
   never cuts a running call. `--per-call-usd X` adds `--max-budget-usd X` (limited to the rest of the budget) for
   whoever wants a cap; without a cap a run with no result event books 0 and carries `cost_unknown`. Plan headers say
   `per_call_cap: null`, `argv_template` has no `--max-budget-usd`. `tsbench plan estimate` estimates the cost; its
   budget line compares the plan budget with the expected total and the sum of p90s. With `--gateway` the price
   Claude Code prints is an estimate (the list price it assumes for an unknown model), so it is kept in `estimated_cost_usd` of the manifest and
   never counts against `--budget-usd`; `total_cost_usd` stays 0 and `--per-call-usd` is not passed on. A run set that
   the budget stopped exits with 75, like a quota stop, so a script does not take a cut matrix for a finished one.
4. **Turns per condition.** `conditions.MAX_TURNS = {A: 15, B: 40, C: 25}` is the single source; the plan record's
   `max_turns` and `--max-turns` come from it.
5. **Text-only gateway models.** For condition C with `--gateway` and a model in
   `conditions.TEXT_ONLY_GATEWAY_MODELS` (`deepseek-v4-flash-0731`, `meta-llama-3.1-8b-instruct`, `qwen3-coder-next`,
   `qwen3-30b-a3b-instruct-2507`, `qwen3.8-27b`; the endpoint's `/v1/models` lists input `["text"]` for them),
   the call gets `--disallowedTools mcp__tanabesugano__ts_plot_png mcp__tanabesugano__ts_emit_png`, because these
   models cannot read an image result. Through the LiteLLM proxy of `contrib/gateway` the model is
   the `gwdg-*` alias (`gwdg-llama-3.1-8b`, `gwdg-qwen3-coder-next`, `gwdg-qwen3-30b-a3b-instruct`,
   `gwdg-qwen3.8-27b`); `conditions.GATEWAY_ALIASES` maps each alias to its native id, so the rule applies to both
   names. The run record has `disallowed_tools`; `check_init` takes the
   list and requires those tools to be absent from the init tool list, and accepts the list without them (the rule
   for C above is unchanged).

### 3.5 Resume

A transcript counts as done if its last event is `type == "result"`, unless `is_error` is true **and**
`total_cost_usd == 0`. That case is an infrastructure failure that never reached a model, and it is re-run. An API
error is re-run too. A run that hit the wall limit (`WALL_TIMEOUT_S`) has no result event, but its sidecar says
`timed_out`: it is an outcome and counts as done (with the cost the sidecar booked), so a resume does not sample it
again. A run that was killed or crashed before its result event is not done. A run whose transcript ends in a result
but has no sidecar (the invocation stopped between the two writes) is done too: `--resume` rebuilds its sidecar from
the transcript (`sidecar_rebuilt: true`; flags, cost, init check, reported model and images from the events; exit code,
wall time and start time are not known and stay empty) and skips the run. The transcript is split at the
newline only, and only its tail is read to find the last event.

On resume the spent total is rebuilt from the money on disk before the first run starts: the cost of every finished
transcript, plus the money of every attempt that is not finished, at the normal path or set aside as
`<stem>.attempt<N>.jsonl`. That is the reported cost of a paid API error other than HTTP 429, or, for an attempt
without a result event, the charge its sidecar booked (with `--per-call-usd` the per-call cap, also for an attempt
that aborted its cell on the init event). An HTTP 429 counts 0: its price, if any, is an estimate. The sidecar of an
init-aborted attempt also stays at the normal path, with a copy beside the set-aside transcript; it is counted once,
and dropped before the cell runs again. The budget guard and `total_cost_usd` therefore never fall below what earlier
invocations spent.

`--resume` also compares each finished run with the plan record: the sidecar's `prompt_sha256`, `system_prompt_sha256`,
`max_turns` and `disallowed_tools` must equal the record's. On the first difference the invocation stops with exit 2
and changes nothing in the folder, so a finished run never stays in a folder under another prompt, turn limit or tool
block. The answer schema, the argv and the settings are not compared with the sidecars. A sidecar without one of
these fields is not compared on that field. The manifest lists the sha256 of every finished transcript, also when
the invocation stops early on the budget, the quota or API errors.

Runs that ended in an API error other than HTTP 429 (an expired token, a model id the gateway does not serve, a 5xx
outage), or without a result event (a hung call that hit the wall limit), are counted in a row. After 3 in a row
(`TSBENCH_API_ERROR_STOP_AFTER`, 0 = never) the invocation stops with `stop.reason == "api_errors"`, books the rest as
`not_run_api_errors` and exits with 75. `--resume` runs the unrun rest and the runs that ended in an API error again.
A hung call is not run again: its sidecar says `timed_out`, so it stays an outcome (see above). An answer resets the
count, a 429 neither adds to it nor resets it. An invocation in which no run produced an answer also exits with 75.

One invocation writes into a run folder at a time: it holds a lock on `<out>/.run.lock`, and a second invocation on
the same folder stops with exit 2 and writes nothing. SIGTERM and SIGHUP end an invocation like Ctrl-C (exit 130): the
claude process group is killed, the manifest says `interrupted: true`, the README is written and the temporary
home is removed (a SIGHUP that is ignored, as under `nohup`, stays ignored). A real run with condition B also refuses an `--out` outside the
repo, the main checkout and the real home, because B's sandbox denies reading only those, so B's Bash could read the
transcripts of earlier runs there.

## 4. Run plan

The runner executes a **run plan**: one frozen JSONL file that says exactly what will be run. Running is a separate
stage that consumes this file. The runner reads nothing else to decide *what* to run; it still reads `ts.json` and the
settings template to render paths, but those are pinned by hash in the plan. Every other stage is also a file-in,
file-out step with a hash in its output.

### 4.1 Format

`plan.jsonl`: line 1 is a header (`"kind":"header"`), then one `"kind":"run"` record per run. One file, grep-able,
diff-able, sortable by `run_id`. The schema is `src/tsbench/data/schemas/plan.schema.json` (JSON Schema draft 2020-12,
`oneOf` on `kind`, `additionalProperties: false` so a typo cannot slip in). Schema versions 2, 3 and 4 load. Version 2
has no `answer_schema` and means `fit`; version 4 adds `b_stack_sha256` to B runs. A built-in validator checks the
plan before anything runs; it also requires every run record's `split` to equal the header's `spec.split`. The
confirmatory guard of the runner (the DOI of the preregistration) applies when the header or any run record says
`confirmatory`. `plan_id` is the sha256 of the canonical run lines in `run_id` order; it ignores timestamps, pins and
file order.

Header fields: `schema_version`, `plan_id`, `created_utc`, `spec` (the selection, verbatim: split, models, conditions,
efforts, k, budget, limit, system prompt file, gateway), `tasks_sha256` (the subset hash from `tasks.sha256` for the
split), `generator_git_commit`, `pins`, `sealed` (bool), `n_runs`, `budget_usd_total`, `counts`.

Run record fields:

| Field | Meaning |
|---|---|
| `run_id` | `<model>/<cond>/<effort>/<task_id>-k<i>`. Unique key. |
| `task_id`, `task_class`, `split` | Copied from the task. |
| `task_sha256` | sha256 of the canonical task record. |
| `prompt` | Full user-message text (what goes to stdin). Not elided. |
| `prompt_sha256` | Hash of the UTF-8 prompt, so a view can show "unchanged". |
| `system_prompt_file`, `system_prompt_sha256`, `system_prompt_text` | Path relative to the repository, hash, and the text itself (short; makes the record standalone). |
| `model` | Full model ID. |
| `effort` | `low`, `medium`, `high`, `xhigh` or `max`, as `--effort` accepts. |
| `condition` | `A`, `B` or `C`. |
| `k` | 1-based repetition index. |
| `max_turns` | Per-run turn limit (3.4, item 4). The run-set budget lives in the header. |
| `tools_expected` | What `check_init` must see: `{"tools":[...] or "mcp_prefix", "mcp_servers":[...]}`. Copied from `conditions.TOOLS_EXPECTED`, the one statement of the rule that `check_init` enforces; stored in the plan so the runner can refuse a plan whose record differs from it. |
| `argv_template` | The argv with placeholders `{SETTINGS}`, `{MCP_CONFIG}`, prompt elided (as in sidecars). Exactly what `build_argv` returns, minus per-machine paths. The runner rebuilds it for every record before the first call and refuses a plan whose stored template differs. |
| `expected_flags` | Optional: flags that are suspect for the condition (`b_no_tool_use`, `c_no_mcp_call`). Scored in the score stage; the runner refuses a plan whose list differs from the code. |
| `answer_schema`, `answer_schema_sha256`, `answer_format` | The answer schema of the record (section 2). |
| `disallowed_tools` | Text-only gateway models (3.4, item 5). |

`pins` (header): `claude_cli_version`, `tanabesugano` (2.0.0), `python` major.minor, `sandbox_settings_sha256`,
`sandbox_probe_script_sha256`, `ts_json_sha256`, `b_stack_sha256`, `answer_schema_sha256` and `answer_schemas`; the
system-prompt hash is per run. The runner checks `argv_template`, `max_turns`, `expected_flags` and `tools_expected`
of every record against the code.
The run compares the live environment with the pins before the first call. Drift aborts a confirmatory run (exit 2)
and is recorded as `pin_drift` in the manifest for the pilot. A `--resume` of the flags form keeps the
`claude_cli_version` pin of the first invocation, also when it extends the matrix and so changes `plan_id`: a CLI
update between the invocations is drift. A change to `neutral.txt` changes `plan_id`. The plan decides the system
prompt: the runner writes the record's `system_prompt_text` to `<out>/system-prompts/system-prompt-<sha16>.txt` and
passes that file, so an edit of the package file after the plan was built changes nothing for that plan (there is no
system-prompt drift). A change to `neutral.txt` between two flags-form invocations breaks `--resume` through the
sidecar comparison in 3.5.

### 4.2 Commands

- `tsbench plan build <same selection flags> --out-plan F` writes the plan (`--effort` may be a comma list);
  `tsbench plan validate F` checks it. Plan order is k, task, model, effort, condition. `plan build` and the flags
  form of `tsbench run` check their flags and build the spec in the same code (`tsbench.plan.spec_from_flags`,
  `build_from_spec`): the same message for a bad flag, and a confirmatory plan with condition B and no valid B stack
  is refused by both.
- The flags form builds the plan in memory, write `<out>/plan.jsonl`, `plan.sha256`, `plan.md` (pilot only) and run from
  it, so one execution path serves both forms. `tsbench run --plan F --out DIR [--dry-run] [--resume] [--gateway]
  [--budget-usd N]` runs `F` and reads nothing else for task, prompt, model, effort and condition; the selection flags
  are rejected with it. `--resume` with `--plan` needs the same `plan_id` (else exit 2); the flags form may extend the
  matrix, and then the old plan is kept as `plan.prev-<id>.jsonl`. `tsbench run` does not call `tasks.load` when it
  runs a plan.
- A `--out` that already holds a `MANIFEST.json` or transcripts is refused (exit 2) unless `--resume` is given, so a
  second invocation never truncates a finished transcript. `--resume` moves the unfinished transcript of a run aside
  (with its images and sidecar) before it runs again. A cell aborted by the init check keeps its partial transcript
  as `<stem>.attempt<N>.jsonl`, so the scorer does not count it as an answer.
- `MANIFEST.json` describes the whole run set after a `--resume`: `flagged_runs`, `reported_models` and `aborted_cells`
  come from the sidecars of all planned runs, and `start_time_utc` is the start of the first invocation. `counts` and
  `end_time_utc` describe the last invocation (runs finished earlier are `skipped`); the cost includes them.
- A `--gateway` run records the endpoint it used as `args.gateway_url` (scheme, host and port of `ANTHROPIC_BASE_URL`;
  never a token, user or path; the default endpoint `conditions.GATEWAY_URL` when the variable is unset).
  `inputs/commands.sh`, the reproduce block and the Endpoint row of the report name that endpoint, for example
  `gateway localhost:4000` for the local LiteLLM proxy of `contrib/gateway`. A manifest without the field is read as
  the default endpoint.
- `tsbench doctor` makes no model call and installs nothing. `--probe --out DIR` runs the paid sandbox probe (with
  `--gateway` also `--model ID`, a model the gateway serves); a probe that ended in an API error is a WARN, not a FAIL.
- `plan.md` is a rendered companion: it lists distinct prompts once and the matrix (models × conditions × efforts × k),
  so nobody has to read hundreds of identical system prompts.
- Confirmatory plans are sealed: only `plan.sealed.json` (header, counts, `tasks_sha256`, `plan_id`; no run record, no
  prompt) is written. They are built only with `--i-have-preregistered <DOI>`; `plan build --unseal-to PATH` writes the
  clear plan outside the repository. The runner refuses a sealed file and needs the clear plan, whose recomputed
  `plan_id` is the one preregistered.
- `MANIFEST.json` is `schema` 2: the fields of 3.1 plus `plan_id`, `plan_sha256`, `plan_file`, `plan_sealed`,
  `tasks_sha256`, `pin_drift`, `transcripts` (sha256 per run_id). Sidecars carry `plan_id`, `run_id` and
  `prompt_sha256`. The scorer takes the run id of a transcript from its path (`<model>/<cond>/<effort>/<task>-k<i>`,
  the id the plan gives the run). Each `scores.csv` row has `run_id`, `plan_id` and `prompt_sha256` (from the sidecar;
  empty without one) and `transcript_sha256`. `tsbench score` also prints the planned runs that have no transcript and
  the transcripts that no planned run explains. Tasks for scoring come from `tsbench.tasks.load`, because the
  reference is not in the plan.
- `check_init` and the plan's `tools_expected` both read `conditions.TOOLS_EXPECTED`; the runner aborts when a plan
  record differs from it.
- A dry run carries `"dry_run": true` in the manifest and never reaches published results.

### 4.3 Hash chain

```
tasks.jsonl --sha256--> tasks.sha256 (pilot / confirmatory subset hash)
      |  task_sha256 per record, tasks_sha256 in header
      v
plan.jsonl: plan_id = sha256(canonical run lines, in run_id order)       -> plan.sha256
      |  plan_id in every sidecar, in MANIFEST, in scores.csv
      v
transcript .jsonl --sha256--> MANIFEST.transcripts[run_id]
      v
scores.csv (row has run_id, plan_id, transcript_sha256)  -->  figure source tables and provenance files
```

`scores.csv` is older than the transcripts when a transcript has no row, or when a row's `transcript_sha256` differs
from `MANIFEST.transcripts[run_id]` (a run that was overwritten or re-run). The figures then score the transcripts in
memory and say so in the run set's notes; the dashboard names the count. A row without a transcript is no difference:
a results folder keeps `scores.csv` without all the transcripts.

### 4.4 Provenance

The functional test records provenance (`tsbench.core.trace`, rendered by `tsbench.report.provenance`). While a tsbench
process runs, the tracer records which tsbench functions it calls and which function called each one. It records every
Python-level file open, rename, removal, directory creation and subprocess start. For each file read, it stores the
sha256 at the time of the read. For each file written or renamed, it stores the sha256 when the process ends. The
records form a PROV-JSON graph and a hash chain. A read is intact when its sha256 equals the one the last earlier writer
recorded. Inputs that no earlier process wrote are not checked. What is not recorded: environment values, file contents,
host names and the data flow inside functions. A key file or a `.env` file is listed by path without a hash. The call tree covers tsbench code only. The file events cover Python code only, so I/O that
bypasses Python is missing. A child process appears as one event with its arguments, unless it is traced too. A matching
chain shows that each read saw the last write. It does not show that the output is correct.

## 5. Descriptive metrics

Six descriptive metrics, computed from the transcripts, which are scored again on every call. Nothing here makes an API
or LLM call, and nothing here is a hypothesis test: the preregistered hypotheses stay in
`src/tsbench/stats/hypotheses.py`. The acceptance gate is `tests/score/test_acceptance_metrics.py`.

Inputs are fixed by sections 1 to 3:
- Tasks come only from `tsbench.tasks.load(split)`. Nothing prints confirmatory records.
- Transcripts are found with `tsbench.score.score.find_transcripts(runs)` and read with
  `tsbench.score.extract.read_transcript(path)`.
- Answers are extracted with `extract.final_answer(tr.result_text)`, and only when `tr.result is not None`.
  Correctness comes from `numeric.score(task, answer)`, the same path that `score.score_dir` uses.
- Rows are the rows of `<runs>/scores.csv`, with the columns in `score.SCORE_COLUMNS`.

### 5.0 Conventions shared by every module

**Two row forms.** Each function that takes `rows` must accept either form, or a mix of both:
1. CSV rows: `csv.DictReader` on `scores.csv`. All values are `str`, booleans are `"True"`/`"False"`, and null is `""`.
2. Typed rows: `score.score_dir(runs, split)["rows"]`. Booleans are `bool`, a missing error is `float("nan")`, and
   other nulls are `None`.

The modules share no files, so each carries its own private coercion. They all follow the same rule:
- `_bool(v)`: `True` for `True`, `"True"`, `"true"` or `"1"`. `False` for `False`, `"False"`, `"false"` or `"0"`. `None`
  for `None`, `""` or NaN.
- `_float(v)`: `None` for `None`, `""` or NaN. Otherwise `float(v)`. `inf` stays `inf`.
- `_int(v)`: `int(_float(v))`, or `None`.

**Cell key.** Results are grouped by `(model, condition, effort)` and sorted by that key, then by any further key.
Output rows carry those three as strings.

**Expected out of scope.**
- A task is *expected out of scope* iff `task["expect_out_of_scope"]` is true. In the pilot this holds for
  `charge_transfer` and `jahn_teller`; a `tetrahedral` task has `required == ["Dq","B"]` and synthetic tolerances, so
  it is in scope.
- Functions that need `required`, `tolerance` or `expect_out_of_scope` take the task records explicitly, as a `task`
  dict or a `tasks: Mapping[str, dict]` keyed by task id (`failure_category(row, task)`,
  `scope_confusion(rows, tasks)`). `scores.csv` holds neither `required` nor `tolerance`, so `wrong_dq`, `wrong_b` and
  `wrong_c` cannot be told apart from the row alone. The task record is the authority; re-deriving it from `class`
  would duplicate it and could drift.

**Confidence intervals.** The binomial CI of the score tables is `tsbench.stats.hypotheses.clopper_pearson(k, n,
alpha=0.05)`. With `n == 0`, the rate and both CI bounds are `None`. The report pages give the share with the
task-clustered bootstrap (`core.intervals.cluster_bootstrap`, tasks sorted by id), not this interval.

**CSV cells.** `None` and NaN are written as `""`, and floats via `repr`. `metrics/*.csv` uses the column constants
below, in exactly that order.

**Row dict keys.** The dicts returned by `tolerance_curve`, `scope_confusion`, `failure_table`, `tool_use_rows`,
`per_class_accuracy` and `consistency` have exactly the keys of their column constant, in that order, and no extra
keys. The acceptance tests assert `list(row) == COLUMNS`. `tool_use()` returns exactly the eight metric keys, which
are the last eight entries of `TOOL_USE_COLUMNS`.

### 5.1 Tolerance sensitivity (`src/tsbench/score/sensitivity.py`)

**Question.** Does the A/B/C ranking depend on the 2 % / 5 % / 10 % tolerances?

**Definition.**
- For each scale `s`, every transcript of a task in the split is re-scored with `numeric.score(scaled, answer)`.
- `scaled = scale_tolerance(task, s)` is a deep copy of the task in which each non-null tolerance value is multiplied
  by `s`. A null tolerance (e.g. `C` on `experimental`) stays null. `item_accuracy_min` of the diagram tasks is the
  required share of correct values, not a tolerance, and is never scaled.
- The answer is `final_answer(tr.result_text)` when a result event exists, and `None` otherwise. A transcript without a
  result event is incorrect at every scale.
- Expected out-of-scope tasks are unaffected by `s`, because `numeric.score` never reads their tolerance.
- Transcripts of tasks outside the split are skipped, as `score_dir` does.
- `accuracy = n_correct / n`.
- At `s = 1`, `n_correct` per cell equals the count of `correct` in the `scores.csv` that `score_dir` writes for the
  same runs, and the test checks that. `n_correct` is non-decreasing in `s`.

**Interface.**
```python
DEFAULT_SCALES: tuple[float, ...] = (0.25, 0.5, 1, 2, 4, 10)
SENSITIVITY_COLUMNS = ["model", "condition", "effort", "scale", "n", "n_correct", "accuracy"]
def scale_tolerance(task: dict, scale: float) -> dict  # copy; input not mutated
def tolerance_curve(runs, split: str = "pilot", scales=DEFAULT_SCALES) -> list[dict]
    # one row per (model, condition, effort, scale); scale as given (float), n/n_correct int, accuracy float
```
Output: `metrics/tolerance_curve.csv`.

### 5.2 Scope confusion (`src/tsbench/score/taxonomy.py`)

**Question.** Does a model name the limits of the ligand-field model? And does it refuse tasks it could solve?

**Definition.** The definition applies per cell. Let `oos = _bool(row["answer_out_of_scope"])`, which is `None` when the
answer is unparseable, has no result, or the flag is not a boolean. `expected` is
`tasks[row["task_id"]]["expect_out_of_scope"]`.

| Column | Rows counted |
|---|---|
| `n_expected_oos` | rows with `expected` |
| `n_in_scope` | rows without `expected` |
| `true_limit` | `expected` and `oos is True`. Only the flag counts, so Dq/B may be non-null. Correctness additionally needs null Dq and B. |
| `missed_limit` | `expected` and `oos is False` |
| `false_refusal` | not `expected` and `oos is True` |
| `correct_scope` | `true_limit` + (not `expected` and `oos is False`) |
| `no_scope_answer` | rows of either kind with `oos is None` |

Identity: `n_expected_oos + n_in_scope == correct_scope + missed_limit + false_refusal + no_scope_answer`.
- `limit_naming_rate = true_limit / n_expected_oos`, with a Clopper-Pearson CI. Unparseable rows stay in the
  denominator.
- `false_refusal_rate = false_refusal / n_in_scope`, with a Clopper-Pearson CI.

**Interface.**
```python
SCOPE_COLUMNS = ["model", "condition", "effort", "n_expected_oos", "n_in_scope", "true_limit", "missed_limit",
                 "false_refusal", "correct_scope", "no_scope_answer",
                 "limit_naming_rate", "limit_naming_ci_lo", "limit_naming_ci_hi",
                 "false_refusal_rate", "false_refusal_ci_lo", "false_refusal_ci_hi"]
def scope_confusion(rows, tasks: Mapping[str, dict]) -> list[dict]  # one row per cell; rows of unknown task ids skipped
```
Output: `metrics/scope_confusion.csv`.

### 5.3 Failure taxonomy (`src/tsbench/score/taxonomy.py`)

**Question.** Why is a wrong answer wrong: infrastructure, format, scope, or which parameter?

**Definition.** `failure_category(row, task)` returns exactly one of `CATEGORIES`. The first rule that matches wins:

| # | Category | Rule |
|---|---|---|
| 1 | `correct` | `_bool(correct)` |
| 2 | `no_result` | `has_result` is false |
| 3 | `max_turns` | `result_subtype == "error_max_turns"` |
| 4 | `budget` | `result_subtype == "error_max_budget_usd"` |
| 5 | `unparseable` | `result_subtype == "error_max_structured_output_retries"`: the CLI gave up after repeated StructuredOutput calls that failed the answer schema. This is a format failure of the model, not an API error. |
| 6 | `context_overflow` | `context_overflow` true: the request outgrew the model's context window (3.4 (d)). A model failure, evaluable and wrong. |
| 7 | `api_error` | `is_error` true, with any other subtype. The no-login fixture has `subtype "success"` and `is_error true`. |
| 8 | `unparseable` | `unparseable` true |
| 9 | `false_refusal` | task not expected out of scope, and `answer_out_of_scope` true |
| 10 | `missed_limit` | task expected out of scope, and incorrect for any other reason: flag false, flag null, or Dq/B given |
| 11 | `gross_error` | some `p` in `task["required"]` has `rel_err_p > 0.5`, finite or `inf`. Typically a wrong d-count, geometry or sign convention. |
| 12–14 | `wrong_dq` / `wrong_b` / `wrong_c` | exactly one required parameter is *off*, and it is that one |
| 15 | `wrong_multiple` | two or more required parameters are off. This is also the fallback of a fit answer. |
| 16 | `wrong_items` | a curve, batch, pairing or diagram answer that is wrong but not gross: items are outside the tolerance. |

- A parameter `p` is *off* iff its `rel_err_p` is null (missing value), or `rel_err_p > tolerance[p] + 1e-12`. That is
  the same slack as `numeric._EPS`.
- Parameters outside `required` never count, so `C` on a `closed_form` task is ignored even when its error is huge.
- **Curve, batch, pairing and diagram answers** have no Dq/B/C and no scope flag. A wrong one is `gross_error` when
  `curve_max_rel_err` (curve) or `median_rel_error` (batch) is above 0.5, or `item_accuracy` (diagram) is below 0.5,
  and `wrong_items` otherwise. A curve with no measurable error is `unparseable`.
  - A batch row without a `median_rel_error` is `gross_error`: the scorer writes no median when it is infinite, which
    is the case when half or more of the items are missing or null.
  - A pairing row has no median error. It is `gross_error` when any of `node_precision`, `node_recall`,
    `edge_precision` and `edge_recall` is below 0.5, and `wrong_items` otherwise (a missing column does not count).
- **Fallback.** A row that is incorrect, in scope, parsed, and has no off parameter can only occur when
  `answer_out_of_scope` is not a boolean, which is a format failure. It is classed `unparseable`, not
  `wrong_multiple`.
- `failure_table` aggregates per cell. It emits every category, zero counts included, so that `sum(n) == rows in cell`.
  `share = n / rows in cell`.

**Interface.**
```python
CATEGORIES = ("correct", "no_result", "max_turns", "budget", "context_overflow", "api_error", "unparseable",
              "false_refusal", "missed_limit", "gross_error", "wrong_dq", "wrong_b", "wrong_c", "wrong_multiple",
              "wrong_items")
GROSS_REL_ERR = 0.5
FAILURE_COLUMNS = ["model", "condition", "effort", "category", "n", "share"]
def failure_category(row: dict, task: dict) -> str
def failure_table(rows, tasks: Mapping[str, dict]) -> list[dict]  # len == n_cells * len(CATEGORIES)
```
Output: `metrics/failure_taxonomy.csv`.

### 5.4 Tool-use quality (`src/tsbench/score/tool_use.py`)

**Question.** In C, does the model call the right tool, with the right electron count? How often do tool calls fail?

**Definition.** The definition applies per transcript. Tool names are stripped of the prefix `mcp__tanabesugano__`, so
`Bash` is unchanged. Calls of `StructuredOutput` are not counted.
- `n_calls`: the number of `tool_use` blocks, all tools.
- `n_distinct`: the number of distinct stripped names.
- `n_bash_calls`: calls named `Bash`.
- `n_tool_errors`: the number of counted calls (distinct `tool_use_id`) that have a `tool_result` block with
  `is_error is True`. A `StructuredOutput` call is not counted: a rejected answer is no tool error. A call counts
  once even if its error result is repeated, so `tool_error_rate` stays at most 1 and is
  0 or `None` in condition A. `extract.Transcript.tool_results` drops `is_error`, so this **must** scan
  `transcript.events`: user events, `message.content[*]` with `type == "tool_result"`. A missing key counts as false.
- `tool_error_rate = n_tool_errors / n_calls`, or `None` when `n_calls == 0`.
- `expected_tool_used`, condition C only (`None` in A and B):
  - Let `E = expected_tools(task)`.
  - If `E` is non-empty: true iff some call's stripped name is in `E`. The match is any-of.
  - If `E` is empty, as for charge transfer and Jahn-Teller: true iff **no** call's stripped name is in `FIT_TOOLS`.
    No fit tool should be needed.
- `first_expected_index`: the 0-based index into `transcript.tool_uses` of the first call in `E`. It is `None` when
  there is no such call, when `E` is empty, or when the condition is not C.
- `d_count_matches`:
  - Look at the calls whose stripped name starts with `ts_` and whose input has a `d_count` that coerces to an int.
  - It is `None` when there are no such calls, or when `task["d_count"]` is `None`.
  - Otherwise it is true iff any of those values equals `d`, where `d = task["d_count"]`. For
    `task["geometry"] == "Td"` it also accepts `10 - d`.

The expected-tool table below is the one in `src/tsbench/score/tool_use.py`. The lookup is `f"{class}/{subtype}"`, then `class`, and `frozenset()` if neither
matches:
```python
EXPECTED_TOOLS = {
    "closed_form": frozenset({"ts_fit_spectrum"}),
    "numerical": frozenset({"ts_fit_spectrum"}),
    "racah_c": frozenset({"ts_terms_table_data", "ts_fit_spectrum"}),
    "experimental": frozenset({"ts_fit_spectrum"}),
    "numerical_hard": frozenset({"ts_fit_spectrum"}),
    "tetrahedral": frozenset({"ts_fit_spectrum"}),
    "crossover": frozenset({"ts_spin_crossover_app"}),
    "curve": frozenset({"ts_compute_app", "ts_terms_table_data"}),
    "literature_all": frozenset({"ts_fit_spectrum"}),
    "literature_new": frozenset({"ts_fit_spectrum"}),
    "batch/crossover_series": frozenset({"ts_spin_crossover_app"}),
    "batch/band_series": frozenset({"ts_compute_app", "ts_terms_table_data"}),
    "pairing": frozenset({"ts_terms_table_data"}),
    "diagram": frozenset({"ts_compute_app", "ts_terms_table_data"}),
    "out_of_scope/charge_transfer": frozenset(),
    "out_of_scope/jahn_teller": frozenset(),
}
FIT_TOOLS = frozenset({"ts_fit_spectrum", "ts_ratio_fit_app", "ts_reverse_fit_app", "ts_fit_plot_app", "ts_fit_script"})
MCP_PREFIX = "mcp__tanabesugano__"
TOOL_USE_COLUMNS = ["model", "condition", "effort", "task_id", "k_index", "class", "subtype", "n_calls", "n_distinct",
                    "n_tool_errors", "tool_error_rate", "expected_tool_used", "first_expected_index",
                    "d_count_matches", "n_bash_calls"]
def strip_prefix(name: str) -> str
def expected_tools(task: dict) -> frozenset[str]
def tool_use(task: dict, transcript: Transcript, condition: str) -> dict  # the 8 metric keys above
def tool_use_rows(runs, split: str = "pilot") -> list[dict]  # one row per transcript of a task in the split
```
Output: `metrics/tool_use.csv`, one row per transcript. The real Haiku C smoke transcript of `P-closed_form-01` (k1,
`claude-haiku-5-5`, condition C, effort medium) gives the following, and the acceptance suite checks it: `n_calls 2`,
`n_distinct 2`, `n_tool_errors 0`, `expected_tool_used True`, `first_expected_index 0` and `d_count_matches True`.

### 5.5 Per-class accuracy (`src/tsbench/stats/descriptive.py`)

**Question.** Where does each condition win or lose: synthetic classes or literature spectra?

**Definition.**
- Per cell and per group: `n` rows, `n_correct`, `accuracy = n_correct / n` and a Clopper-Pearson CI.
- `grouping == "class"`: the group is the row's `class`. Every class present in the rows is included (v2: 14).
- `grouping == "source"`, derived from the row alone (`descriptive.source_group`, `SYNTHETIC_CLASSES`):
  - `literature`: class `experimental`, `literature_all` or `literature_new` (bands are published maxima).
  - `synthetic`: class `closed_form`, `numerical`, `numerical_hard`, `racah_c`, `tetrahedral`, `crossover`, `curve`,
    `batch` or `diagram`.
  - `pairing` and the expected out-of-scope subtypes (`charge_transfer`, `jahn_teller`) belong to neither source group.
- Groups with no rows are not emitted.

**Interface.**
```python
PER_CLASS_COLUMNS = ["model", "condition", "effort", "grouping", "group", "n", "n_correct", "accuracy", "ci_lo", "ci_hi"]
def source_group(row: dict) -> str | None  # "synthetic" | "literature" | None
def per_class_accuracy(rows) -> list[dict]
```
Output: `metrics/per_class.csv`.

### 5.6 Consistency over k (`src/tsbench/stats/descriptive.py`)

**Question.** Is a model's answer stable across the k repeats, or is the accuracy a coin flip?

**Definition.**
- The definition applies per cell, over the tasks with `k >= 2` rows in that cell. Tasks with a single run are left
  out of every column.
- `n_tasks`: the number of such tasks.
- `n_unanimous` and `unanimity_rate = n_unanimous / n_tasks`: a task is unanimous when its k runs share one
  correctness value.
- `mean_pairwise_agreement`: the mean over tasks of the fraction of unordered run pairs `(i < j)` with equal
  correctness.
- Coefficient of variation of the reported Dq. Correct and incorrect runs both count; null Dq values are ignored.
  - Per task, `cv = statistics.stdev(v) / statistics.fmean(v)` with `v = [abs(dq)]`. That is the sample standard
    deviation (ddof = 1), and `abs` keeps the Td sign convention out of the spread.
  - Only tasks with at least 2 non-null Dq values and `fmean(v) > 0` count. Their number is `n_tasks_cv`.
  - `median_cv_dq` is `statistics.median` over those tasks, or `None` when there are none.
- All rates are `None` when `n_tasks == 0`.

**Interface.**
```python
CONSISTENCY_COLUMNS = ["model", "condition", "effort", "n_tasks", "n_unanimous", "unanimity_rate",
                       "mean_pairwise_agreement", "n_tasks_cv", "median_cv_dq"]
def consistency(rows) -> list[dict]
```
Output: `metrics/consistency.csv`.

### 5.7 Report command (`src/tsbench/stats/metrics.py`)

```
tsbench metrics --runs <dir> --split pilot [--i-have-preregistered DOI]
```
1. If `--split confirmatory` is given without `--i-have-preregistered`, or with a value that is not DOI-shaped
   (`10.<4-9 digits>/<suffix>`, the same check as `plan build`, `run`, `score` and `figures`; code in
   `tsbench.core.prereg`), exit 2 with a stderr message that names
   `--i-have-preregistered`. This happens before any task is loaded or file written; no `metrics/` directory is
   created.
2. If `--runs` is not a directory, exit 2.
3. Run `tsbench.score.score.score_dir(runs, split)` every time, so that `scores.csv` and the transcripts describe the
   same run set. Every transcript is read once; `score_dir`, the tolerance curve and the tool-use rows share the parse.
4. Read `scores.csv` as CSV rows (form 1), and the tasks with `load(split)`. Rows with `evaluable=False` (HTTP 429,
   API error, see 3.4) are left out of every table, as `rates.csv` does, except `failure_taxonomy`, which keeps them.
   The tolerance curve and the tool-use rows skip those transcripts too.
5. Write `<runs>/metrics/{tolerance_curve,scope_confusion,failure_taxonomy,tool_use,per_class,consistency}.csv` with the
   column constants above.
6. Print a compact summary to stdout, at most about 40 lines: per cell, the accuracy, `limit_naming_rate`,
   `false_refusal_rate`, the top failure categories, and `expected_tool_used` in C. Exit 0.

```python
METRIC_FILES = ("tolerance_curve", "scope_confusion", "failure_taxonomy", "tool_use", "per_class", "consistency")
def write_metrics(runs, split: str = "pilot") -> dict[str, pathlib.Path]  # name -> written csv path
def main(argv=None) -> int
```

### 5.8 Tests of the metric code

The metric code makes no API or LLM call and prints no confirmatory task content. Its tests use synthetic transcripts
in `tmp_path` that copy the event shapes of `src/tsbench/run/fake_cli_fixtures/*.json`, plus a copy of the three real
smoke transcripts. Each metric module has its own test file in `tests/score/`.

## 6. Run views and confirmatory secrecy

The run views:
1. `plan.jsonl`: the complete test file. One line per run, readable with `jq`; the header says what it is. `plan.md`
   is its rendered companion (4.2).
2. `views/INDEX.html`: one row per run: run_id, task class, condition, model, effort, correct, error, cost, turns,
   tool-call count, flags; every `run_id` links to its view. Columns are sortable; no JavaScript framework, a small
   inline script is enough.
3. `views/<model>/<cond>/<effort>/<task>-k<i>.html`: top to bottom: the input (system prompt, user prompt, argv
   template, pins), the tool calls (name, input, truncated result, in order), the final answer (raw text plus the
   parsed JSON line), the oracle comparison (answer, reference, error, tolerance, verdict, failure category), cost and
   tokens, and a link to the raw transcript. Rendered by `tsbench report views`, never edited. A page is a pure
   function of its inputs: rendering again gives byte-identical files except a timestamp line that is excluded from
   hashing.
4. Figures: each plot has its files and a `.source.csv` and provenance `.json` with the plotted numbers (the data
   behind each point), so a reader can redo the plot. The plotting code is committed.

`tsbench report views --runs DIR` writes the views (`DIR/views/…` and
`DIR/views/INDEX.html`): self-contained pages (inline CSS, light and dark), all transcript text escaped, tool results
truncated, the `scores.csv` row if present. It refuses a confirmatory directory without
`--i-have-preregistered <DOI>`.

Confirmatory secrecy. The constraint: no model, and no published artifact, shows confirmatory tasks before
preregistration.
- A confirmatory plan can be built at any time. The file written to the repository is `plan.sealed.json`: header plus
  `plan_id`, `n_runs`, `tasks_sha256`, per-condition and per-class counts, and **no run records**. The full plan is
  written outside the repository (`--unseal-to PATH`); the preregistration cites `plan_id`.
- The runner refuses a sealed plan; it requires the clear plan whose recomputed `plan_id` equals the preregistered one,
  and `--i-have-preregistered <DOI>`. Anyone with the clear plan can verify it against the preregistered
  `plan_id`.
- Views of confirmatory runs are rendered only after the run. Before that, an index can be built from the sealed
  header only (counts, no content). Confirmatory prompts embed the hidden task text, so the clear plan of the
  confirmatory split is written outside the repository and is not tracked by git.
- Because the plan contains prompts but not references, even a leaked clear plan does not leak answers. (The oracle
  arguments such as exact Dq/B are in `tasks.jsonl`, not in the plan.)
- Page content is scanned for secrets: environment variable names only, never values; the sandbox strips host paths
  (`strip_path`). Views include tool results verbatim.
