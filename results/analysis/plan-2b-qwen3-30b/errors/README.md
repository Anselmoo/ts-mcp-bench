# Failing tool steps

Inputs: the transcripts of one scored run folder and its `scores.csv` (for `correct` and `class`).

A step is one tool call other than the StructuredOutput answer. A step fails when its result shows one of these
kinds, checked in this order: `timeout` (the tool stopped the command: "timed out after"), `python` (a Python
exception line, `ValueError: ...`, after a Traceback, or with a non-zero exit or the error flag), `shell` (an error
line of the shell, `/bin/bash: line 3: pip: command not found`, or of a basic command such as mkdir, cd, sed or
python3 itself, `mkdir: cannot create directory`, also when the exit code is 0), `tool_error` (the harness refused
the call, such as an unknown tool name), `mcp_error` (an MCP result whose JSON has an `error` field), `exit` (a
non-zero exit code; the message is the first line after the exit code) and `is_error` (the result's error flag
alone). For `python` the exception type is the last exception line of the text (the one raised) and the missing name
is read from ImportError, ModuleNotFoundError, AttributeError and NameError messages (`scipy.special.sph_harm`). A
printed line that only looks like an exception, with exit code 0 and no Traceback, is not a failure.

`runs.csv`: per run the number of steps and of failing steps, the first failing step (0-based) with its kind,
exception and missing name, `steps_to_first_ok` (the steps before the first step that did not fail; empty when none
succeeded), `recovered` (a step after the first failure succeeded), `last_step_failed`, `span_s` (first to last
timestamp of the transcript), `wall_after_first_error_s` (from the result of the first failing step to the last
timestamp) and `failed_step_s` (the summed step times of the failing steps; a step's time runs from the result
before it, or the first timestamp, to its own result, so it holds the model's turn and the tool's run).

`steps.csv`: one row per failing step with the first line of its message. `exceptions.csv`: failing steps and runs
per model, condition, kind, exception and missing name. `by_group.csv`: per model and condition the runs, the steps,
the failing steps, the runs with a failure, how many of them recovered and were correct, the accuracy of runs with
steps with and without a failure, the median time after the first failure and the share of time in failing steps.
