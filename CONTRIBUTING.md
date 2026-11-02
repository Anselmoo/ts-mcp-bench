# Contributing

## Setup

```bash
uv sync --extra test --extra lint
uv run pre-commit install --hook-type pre-commit --hook-type pre-push   # optional: the local git hooks
```

The hooks and the CI jobs are described in `docs/pipeline.md`.

## Checks

Run these before you propose a change. None of them calls a model or needs a key.

```bash
uv run pytest -q -p no:cacheprovider tests      # the unit tests (CI runs the same with tools/ci/test.sh)
bash tools/ci/lint.sh                           # ruff, bash -n and shellcheck
uv run tsbench tasks verify                     # counts and hashes of the task set
bash tools/ci/e2e_dry.sh                        # the whole pipeline with the fake claude, output in build/ci/e2e/
uv run tsbench release gate                     # no private material is tracked or in the release archive
```

## Conventions

- Python 3.12 or later. ruff with line length 120 (`pyproject.toml`). Use `from __future__ import annotations` and type
  hints.
- Every text read and write passes `encoding="utf-8"`.
- Tests live under `tests/`, which mirrors `src/tsbench/`: one `test_<module>.py` per module. Repository-wide checks
  sit directly in `tests/`. A behaviour change comes with a test.
- Data is read only through `tsbench.core.resource()`.
- Docs and commit messages are plain English in short sentences. Docs describe what the code does now.

## Task set

The task set is generated (`tsbench tasks generate`) and checked by hash. A change must keep the hashes of
`src/tsbench/data/tasks/tasks.sha256` (pilot `77ca71ea…`, confirmatory `6aa12d6a…`): `uv run tsbench tasks verify`
must pass. The files in `src/tsbench/data/tasks/` are written by the generator, not by hand.

## Keys and private material

No key, token or other credential enters the repository, and no private material does either: no run data, no
seeds, no analysis output. Keys live in the environment or in a key file outside the repository (`TSBENCH_KEY_FILE`,
default `~/.config/tsbench/env`). `uv run tsbench release gate` and the CI jobs check this. Names the gate should
also refuse are set in `TSBENCH_GATE_DENY` (separated by commas or whitespace), in the shell or as a CI variable
or secret, never in a tracked file. A hit prints as `***`.
