# Effort and time

Inputs: the transcripts and sidecars (`<task>-k<i>.meta.json`) of one scored run folder, its `scores.csv` (for
`correct`, `class` and `evaluable`) and, when it exists, its `metrics/consistency.csv`.

`runs.csv`: per run the thinking tokens (`output_tokens_details.thinking_tokens` of the result event's usage; empty
when the event does not report them), the thinking tokens the progress lines estimate (`estimated_thinking_tokens`:
the estimate restarts with every turn, so this sums the last estimate of each turn; it is the only count for a run
stopped before its result event), the output tokens, the turns, the tool steps and the failing tool steps (as in
the error analysis), the wall time measured by the runner (`wall_time_s` of the sidecar, with the start of the CLI),
the duration and API duration of the result event, `thinking_s` (the summed `thinking_duration_ms` of the
transcript's events), `tool_s` (the summed time from each tool call to its result), `failed_step_s` (the summed step
times of the failing steps, see the error analysis), the sidecar flags (`timeout`: the runner stopped the run at the
wall limit; `cost_unknown`: no cost was reported) and the cost. A run stopped at the wall limit has no result event,
so its reported tokens, turns and durations are empty.

`by_group.csv`: per model, condition and effort the runs, the correct runs, the runs with a timeout and with an
unknown cost, the medians of thinking tokens, output tokens, turns and wall time (over all runs and split by correct
and wrong), the rank correlation between thinking tokens and correctness (Spearman, over the runs that report
thinking tokens), and the shares of wall time spent thinking, in tools and in failing steps (sums over the runs that
have both numbers). The last columns are those of `metrics/consistency.csv` for the same cell: agreement of the k
repetitions per task.

`timeouts.csv`: the runs with the `timeout` flag. `tasks.csv`: per model, condition, effort and task the k runs, the
correct ones, whether they agree (`unanimous`), the timeouts, the median thinking tokens with their coefficient of
variation across the k runs, and the median wall time.
