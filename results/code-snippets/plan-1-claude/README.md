# Code snippets

Inputs: the transcripts of one scored run folder. Only Bash commands are read; MCP calls are not code.

Files: `<run id>/step-NN.sh` is the NN-th Bash command of the run, byte for byte as the model sent it. Each heredoc
of that command is also written on its own: `step-NN-<target>.py` when it is redirected to a file (`cat > a.py
<<'EOF'`), `step-NN-heredoc-<i>.py` when it is fed to Python directly (`python3 - <<'EOF'`), and `.txt` instead of
`.py` when the body is not Python. A call to an unknown tool name (such as `bash`) never ran and is left out, as is
an empty command.

`index.csv` has one row per file: `run_id`, `step` (the number NN), `kind` (`bash` or `heredoc`), `file` (relative to
this folder), `lines`, `sha256` (of the file bytes), `tool_use_id` (of the Bash call), `exit` (the exit code the
result reports; 0 for a result without one; empty without a result), `is_error` (the result's flag), `target` (the
file a heredoc is redirected to).

Method: the commands are parsed by the parser of `tsbench report artifacts` (`score/artifacts.py`); nothing is
executed.
