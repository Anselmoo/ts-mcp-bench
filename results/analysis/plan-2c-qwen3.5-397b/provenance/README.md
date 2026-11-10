# Provenance of the answer numbers

Inputs: the transcripts of one scored run folder, the task records of its split (the prompt) and its `scores.csv`
(for `correct`, `class`, `n_reported` and `n_traced`).

Every finite number of the answer the scorer used is one row of `numbers.csv` (`path` names it: `Dq`, `B`, `C`,
`points[3].e_over_b`, ...). `source` says where it came from, by the links of the solution path (a number matches a
number of a tool result within 0.5 % relative, by absolute value): `tool` (a step printed it whose own input does not
hold it; `source_step` and `source_tool` name the step: the last such step that ran a script, else the last such
step), `typed` (every step that printed it holds it in its own input, a literal of the command or its heredocs or an
argument of the MCP call that the tool echoes back: the model chose the number), `weak` (an integer below 50, which
turns up by chance, linked to some step) and `none` (no tool result holds it: the model's own number). `traced` is
the scorer's test (`n_traced` of `scores.csv`): the number appears in some tool result; it can differ from `source`
because the solution path keeps only the first 20 000 characters of a result. `in_prompt` says that the number is
written in the task prompt.

In condition C each Dq, B and C is compared with the fitted values of the `ts_fit_spectrum` calls of the run
(`fitted_Dq`, `fitted_B`, `fitted_C`): `copied` (within 0.5 % of a fitted value of any call), `changed` (a fit
returned that parameter but the answer differs; `fit_value` and `fit_rel_diff` refer to the last fit that returned
it), `no_fit` (no call returned it). Outside condition C the field is empty.

`runs.csv`: per run the counts per source, `n_traced` (Dq, B, C traced here) next to `n_traced_scores` (the scorer's
column) and the origin of Dq, B and C. After a fit in condition C: `fit_copied`, `fit_other_tool` (not the fitted
value, but another tool step printed it, such as `ts_ratio_fit_app`) or `fit_changed` (not the fitted value and no
tool step computed it); otherwise the source (`tool`, `typed`, `weak`, `none`); `null` when the answer leaves the
parameter out. `by_group.csv`: per model, condition, parameter and origin
the runs, the correct runs and the wrong runs.
