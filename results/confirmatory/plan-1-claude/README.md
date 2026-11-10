# Run set: claude-haiku-5-5, claude-sonnet-5-5, claude-opus-5-5 | conditions C,B,A | effort medium | k=3 | confirmatory (55 tasks)

## What was run

- models: claude-haiku-5-5, claude-sonnet-5-5, claude-opus-5-5
- conditions: C, B, A (A no tools, B Bash in a sandbox, C MCP server)
- effort: medium; k = 3
- tasks: 55 of the confirmatory split
- plan_id: `cfd9c463c00a27185bebf057746bda55b5251be8b5764687886f1e11a3a29e3c` (sealed: the prompts are not stored here)
- Anthropic API

## When

- start (UTC): 2026-11-03T06:56:55+00:00
- end (UTC): 2026-11-04T17:37:46+00:00
- state: finished

## Runs

- planned: 1485
- done in this invocation: 22
- skipped (finished in an earlier invocation, --resume): 1463
- flagged runs (see MANIFEST.json `flagged_runs`): 271

Total cost: USD 128.5165 (run-set budget USD 155.0)

## Inputs (next to the outputs)

- `inputs/commands.sh`: the command lines that made this run set (keys by name only)
- `inputs/plan.sealed.json`: the plan (sealed header only)
- `inputs/hashes.json`: task set, plan, system prompts, answer schemas, sandbox settings, B stack, versions

## Re-run

Run the whole run set again (into `<this folder>-rerun`, or a folder you name):

    bash inputs/commands.sh [TARGET]

Continue this run set (finished runs are skipped), from inside this folder:

    tsbench run --plan "$TSBENCH_CLEAR_PLAN" --budget-usd 155.0 --out . --i-have-preregistered 10.5281/zenodo.23889782 --resume

## Outputs

- transcripts: `<model>/<condition>/<effort>/<task_id>-k<k>.jsonl` (the raw stream-json of `claude -p`), each with a `.meta.json` sidecar (argv, cost, flags); earlier attempts as `.attempt<N>.jsonl`; harvested images in `.artifacts/`
- `MANIFEST.json`: counts, cost, versions, pins and the sha256 of every transcript
- scores: `tsbench score --runs <this folder>` writes `scores.csv` here
