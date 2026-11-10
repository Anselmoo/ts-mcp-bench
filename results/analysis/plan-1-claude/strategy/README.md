# Solution strategies

Inputs: the transcripts of one scored run folder, the task records of its split and its `scores.csv` (for `correct`
and `class`). The steps of a run are those of its solution path (`tsbench score path`).

Tags of a run, read from all its tool steps (also the steps that failed): `mcp_fit` (a call of `ts_fit_spectrum` or
`ts_fit_plot_app`), `mcp_table` (`ts_terms_table_data`), `mcp_other` (any other MCP tool); and over the code of the
Bash calls: `diagonalisation` (an eigenvalue solver: `eig`, `eigh`, `eigvals`, `eigvalsh`), `least_squares`
(`least_squares`, `curve_fit`, `minimize`, `lstsq` and similar), `root_find` (`brentq`, `fsolve`, `root_scalar`,
`bisect(`, `newton(`), `interpolation`, `symbolic` (`sympy`); `closed_form` when the run made Bash calls but none of
these appear; `none` when the run made no tool call. The tags say what the code calls, not whether the physics is
right. The primary strategy is the first tag in the order mcp_fit, mcp_other, mcp_table, diagonalisation,
least_squares, root_find, interpolation, symbolic, closed_form, none.

`runs.csv`: per run the steps, scripts and failing steps of the solution path, the primary strategy, all tags, the
MCP tools called, the method tags of the solution path and how many answer numbers a step produced (`n_linked`).

`by_group.csv`: per model, condition and class (`all` for every class) and per strategy, counted once by the primary
strategy (`grouping` = primary) and once by every tag (`grouping` = tag): the runs, their share of the group's runs,
the correct runs and the accuracy with its exact 95 % interval.
