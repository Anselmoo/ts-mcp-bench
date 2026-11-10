# TS-MCP benchmark: preregistered protocol and sealed run plans for language models on Tanabe-Sugano ligand-field tasks

DOI of this preregistration: 10.5281/zenodo.23889782

This document fixes the hypotheses, the design, the run plans and the analysis of the confirmatory study before any
model has seen a confirmatory task. It contains no task text, no reference value and no prompt of the confirmatory
split; it identifies them by hash only.

## 1. Aim

Language models determine ligand-field parameters (Dq, B, C) of transition-metal complexes from absorption bands,
compute Tanabe-Sugano curves and diagrams, and recognise questions outside the ligand-field model. The study compares
the accuracy of the models under three tool conditions: no tools, a general code interpreter, and a domain tool (an
MCP server built on the `tanabesugano` package).

## 2. Conditions

All conditions use the same harness (Claude Code CLI 2.1.316, non-interactive, `--bare`, structured output by JSON
schema), the same system prompts and the same task prompts. Only the tools differ.

| Condition | Tools | Turn limit |
|:-|:-|-:|
| A | none | 15 |
| B | Bash with a fixed scientific Python stack (numpy, scipy, sympy, matplotlib; 15 pinned packages) in a sandbox without network | 40 |
| C | the TS-MCP server (Tanabe-Sugano tools) | 25 |

Every system prompt contains one neutral sentence, "If tools are available in this session, you may use them." It
names no tool. Whether a model uses its tools is part of the result and is reported as the tool-use rate.

## 3. Tasks

- Task set `tasks.jsonl`, sha256 `81c43fca0b2538dc9f01c00691b8fad8d96a57eeb747d343914dec35cc48b151`.
- Confirmatory split: 55 tasks, subset hash `6aa12d6a7d2e992c1da3a4ca83d03e195d72883d61b872828581af5821b5e525`.
  Disjoint from the 50 pilot tasks (hash `77ca71ea7ce5bd1fb9c5f03a8afd4b6501905c980dfc4d762215e73d7fdd73fc`);
  no literature system occurs in both splits.
- Classes in the confirmatory split: numerical 6, numerical_hard 6, racah_c 5, tetrahedral 3, out_of_scope 4,
  crossover 4, curve 4, literature_all 18, diagram 5.
- References are computed by the task generator from forward models or published spectra, never typed by hand.

## 4. Scoring

- Fit answers are correct iff `out_of_scope` is false and every required parameter is within its relative tolerance
  (synthetic classes: Dq 2 %, B 5 %, C 10 %; per-task tolerances are part of the hashed task records). Out-of-scope
  tasks are correct iff the answer says out of scope and gives no Dq and B. Curve answers are correct iff all nine
  points are within 3 % relative or 0.3 E/B absolute. Diagram answers are scored by the rubric of the task set.
- Unparseable answers, runs without a result, turn limits, budget stops, timeouts and context overflows (HTTP 400/413
  with a context-window or request-too-large error) count as wrong.
- Not evaluable, and left out of the rates: runs that end in an infrastructure error with no model answer (HTTP 401,
  403, 404, 408, 429, 5xx). The runner retries such a run; the number of not-evaluable runs is reported per model and
  condition.
- Per task and cell (model, condition, effort) the success rate is the share of correct evaluable runs over k.

## 5. Run plans

All four plans are built from the same code, identified by its git tree hash `2f4114b57ce4e04d31a92ec92dff8a733bba7058`
(a hash of the file contents only; see section 9). Each plan is sealed: only its header with counts and hashes is
attached to this record; the clear plan is kept outside the code repository, and its recomputed `plan_id` must equal
the one below before a run starts.

| Plan | Models | Conditions | Effort | k | Runs | plan_id | sealed file sha256 |
|:-|:-|:-|:-|-:|-:|:-|:-|
| 1 (primary) | claude-haiku-5-5, claude-sonnet-5-5, claude-opus-5-5 | A, B, C | medium | 3 | 1485 | `cfd9c463c00a27185bebf057746bda55b5251be8b5764687886f1e11a3a29e3c` | `bd8aacf6785b6a7c443837d5f91c5fae7f9adaaa8818f5ef17f5338efd15cda1` |
| 2a (secondary) | gemma-4-31b-it (gateway) | A, B, C | medium (no effort control on the gateway) | 3 | 495 | `5c82f9135fd24fc05e37ee1fc3feb47e3f4c2a890ee87604fc9a2ccfd771f4e4` | `987a35f361130890bc6917783c66e9373269bd22064f8b94257a685c302af4c4` |
| 2b (secondary) | qwen3-30b-a3b-instruct-2507 (gateway) | A, B, C | medium (no effort control on the gateway) | 3 | 495 | `6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045` | `3f508b85271c2aecada6ee4df853c311fb1c9cedfe4abfb2d1195fc76a1852cc` |
| 2c (secondary) | qwen3.5-397b-a17b (gateway) | A, B, C | medium (no effort control on the gateway) | 3 | 495 | `c62f17a4c542bb250a631e7cb8acdc449dce8e581495a2ebdf4eed1c8c46156a` | `3e6f49aa0f164055a2631a1867ed0398c58bde05ddee1b5d6540754767009ccc` |

The open-weight models of plans 2a, 2b and 2c are served through an OpenAI-compatible gateway. The three plans form
the secondary plan family: one plan per model, with the same split, conditions, effort and k.

Pinned in all four plan headers: answer schemas (fit `290d070f…`, curve `c8df6687…`, diagram `72da01c9…`), B stack
`381cee17a660148e87b571b2867184c9001c90572ca26771695fd2eb1fb24d9c`, sandbox settings `ddaa8ab6…`, sandbox probe
script `02f26d52…`, MCP server configuration `08253a37…`, `tanabesugano` 2.0.0, Claude Code CLI 2.1.316, Python 3.14.
A difference between a pin and the live environment aborts a confirmatory run. The sandbox settings name the path of
the checkout, so every plan runs from the checkout it was built in.

Execution rules:
- Runs are ordered by repetition first (all tasks, models and conditions of k = 1, then k = 2, then k = 3).
- Plan 1 has a budget guard of USD 125: once reached, no new run starts.
- Plans 2a to 2c run as the service quota allows. Their results are reported separately and do not delay or change
  the primary analysis. A run stopped by the service's request limit is resumed later; each of these plans carries a
  nominal budget guard of USD 1000.
- Staged analysis: tests use complete repetition layers only. For each test family, L is the largest k such that every
  task and cell of the family has a run at every layer 1..L; rates use the evaluable runs with k ≤ L. A family with
  L = 0 is not tested. If a plan stops early, the result is reported with the reached L.
- The secondary plans run one after another in the fixed order 2a (gemma-4-31b-it), 2b (qwen3-30b-a3b-instruct-2507),
  2c (qwen3.5-397b-a17b). A plan starts only after the previous one has finished or stopped.
- No plan starts before this preregistration is published. Plan 1 and the secondary plans may run at the same time.

## 6. Hypotheses and tests

All comparisons are paired by task on the tasks common to both cells. Differences read "second minus first", so a
positive value favours the second.

Primary family (plan 1, Holm correction over 4 tests, alpha 0.05, two-sided):
- **H2_haiku, H2_sonnet, H2_opus:** for each Claude model, the success rate in C differs from B.
  Test: Wilcoxon signed-rank on the per-task rate differences C − B (Pratt zero handling, differences rounded to 9
  decimals before ranking).
- **H3:** the gap between the largest and the smallest model shrinks with the MCP server. Test: Wilcoxon signed-rank on
  the per-task difference in differences (Opus − Haiku)_B − (Opus − Haiku)_C; a positive value means the gap is
  smaller in C.

Secondary (plan 1, no multiplicity correction):
- **H1_<model>:** C differs from A, same test.
- Exact McNemar test on the per-task majorities for each H1 and H2 pair.

Secondary (plans 2a, 2b, 2c, Holm over the 3 H2 tests of the secondary family, alpha 0.05): H2 for each open-weight
model (C vs B), same test, each on the runs of its own plan; H1 for each of these models without correction. For the
staged analysis the three plans form one family, so L is the largest layer complete in all three. The secondary plans
do not enter the primary family and cannot change its conclusion.

Not tested in this study: the effort sweep (H4 of the code base), because all plans use one effort.

Effect sizes: mean per-task difference with a task-level bootstrap 95 % interval (5000 resamples, seed 0) and the
matched-pairs rank-biserial correlation.

## 7. Descriptive analyses

Reported for all four plans, without tests: accuracy per class, the tool-use rate per condition, tolerance sensitivity
(the ranking at other tolerances), the failure taxonomy, consistency over k, and efficiency (tokens, time, and for
plan 1 cost) as the median per-task ratio C/A and C/B with bootstrap intervals.

## 8. Deviations

Any deviation from this document (a changed pin, a stopped plan, a changed rule) is listed in the results record with
its reason. Results of runs outside these four plans are exploratory.

## 9. Materials

- Code: the TS-MCP benchmark (`tsbench`), identified by its git tree hash `2f4114b57ce4e04d31a92ec92dff8a733bba7058`.
  The tree hash depends on the file contents only: `git rev-parse HEAD^{tree}` in any repository with the same files
  returns it. The code is not attached to this record, because it contains the confirmatory tasks.
- The plan headers name the generating commit (`generator_git_commit` `e7f956056098acc0f60065eaa88655b586e93a42`),
  whose tree is the hash above. The tree hash is the authority.
- Attached: `plan-1-claude.sealed.json`, `plan-2a-gemma.sealed.json`, `plan-2b-qwen3-30b.sealed.json`,
  `plan-2c-qwen3.5-397b.sealed.json`.
