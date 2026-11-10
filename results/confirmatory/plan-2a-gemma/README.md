# Run set: gemma-4-31b-it | conditions C,B,A | effort medium | k=3 | confirmatory (55 tasks) | gateway

## What was run

- models: gemma-4-31b-it
- conditions: C, B, A (A no tools, B Bash in a sandbox, C MCP server)
- effort: medium; k = 3
- tasks: 55 of the confirmatory split
- plan_id: `5c82f9135fd24fc05e37ee1fc3feb47e3f4c2a890ee87604fc9a2ccfd771f4e4` (sealed: the prompts are not stored here)
- gateway

## When

- start (UTC): 2026-11-03T07:27:32+00:00
- end (UTC): 2026-11-05T10:12:28+00:00
- state: finished

## Runs

- planned: 495
- done in this invocation: 120
- skipped (finished in an earlier invocation, --resume): 375
- flagged runs (see MANIFEST.json `flagged_runs`): 61

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
