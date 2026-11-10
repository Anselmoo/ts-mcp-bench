# Run set: qwen3-30b-a3b-instruct-2507 | conditions C,B,A | effort medium | k=3 | confirmatory (55 tasks) | gateway

## What was run

- models: qwen3-30b-a3b-instruct-2507
- conditions: C, B, A (A no tools, B Bash in a sandbox, C MCP server)
- effort: medium; k = 3
- tasks: 55 of the confirmatory split
- plan_id: `6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045` (sealed: the prompts are not stored here)
- gateway

## When

- start (UTC): 2026-11-05T10:16:24+00:00
- end (UTC): 2026-11-07T03:01:47+00:00
- state: finished

## Runs

- planned: 495
- done in this invocation: 175
- skipped (finished in an earlier invocation, --resume): 320
- flagged runs (see MANIFEST.json `flagged_runs`): 168

Total cost: not counted in USD: gateway

## Inputs (next to the outputs)

- `inputs/commands.sh`: the command lines that made this run set (keys by name only)
- `inputs/plan.sealed.json`: the plan (sealed header only)
- `inputs/hashes.json`: task set, plan, system prompts, answer schemas, sandbox settings, B stack, versions

## Re-run

Run the whole run set again (into `<this folder>-rerun`, or a folder you name):

    bash inputs/commands.sh [TARGET]

Continue this run set (finished runs are skipped), from inside this folder:

    tsbench run --plan "$TSBENCH_CLEAR_PLAN" --out . --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

## Outputs

- transcripts: `<model>/<condition>/<effort>/<task_id>-k<k>.jsonl` (the raw stream-json of `claude -p`), each with a `.meta.json` sidecar (argv, cost, flags); earlier attempts as `.attempt<N>.jsonl`; harvested images in `.artifacts/`
- `MANIFEST.json`: counts, cost, versions, pins and the sha256 of every transcript
- scores: `tsbench score --runs <this folder>` writes `scores.csv` here
