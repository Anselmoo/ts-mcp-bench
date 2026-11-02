#!/usr/bin/env bash
# One mutation-testing shard with mutmut, on a fresh `git archive HEAD` copy (mutmut writes a mutants/ folder; the
# checkout stays untouched). Report-only: survivors do not fail the job, a broken test run does.
#
#   bash tools/ci/mutation.sh NAME "SOURCE_PATHS" "TEST_PATHS"     (the shards are in tools/ci/mutation_shards.json)
#
# Output in $TSCI_MUT_DIR/NAME/ (default build/ci/mutation): results.txt, NAME.json, run.log. MUT_CHILDREN sets the
# number of parallel mutant runs (default: the number of CPUs).
set -uo pipefail
# shellcheck source=tools/ci/common.sh
. "$(dirname "$0")/common.sh"
ci_guard_keys || exit 1
[ $# -eq 3 ] || ci_die "usage: mutation.sh NAME \"SOURCE_PATHS\" \"TEST_PATHS\""
NAME=$1 SRCS=$2 TESTS=$3
OUT_ROOT="${TSCI_MUT_DIR:-build/ci/mutation}"
case "$OUT_ROOT" in build/ci/*) ;; *) ci_die "TSCI_MUT_DIR must be under build/ci/ (got $OUT_ROOT)" ;; esac
command -v uv >/dev/null 2>&1 || ci_die "uv not found (pip install uv)"
OUT="$TSCI_ROOT/$OUT_ROOT/$NAME"
COPY="$OUT/src"
CHILDREN="${MUT_CHILDREN:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)}"

ci_log "copy of HEAD for shard $NAME"
rm -rf "$OUT"
mkdir -p "$COPY"
git -C "$TSCI_ROOT" archive HEAD | tar -x -C "$COPY" || ci_die "git archive failed"
cd "$COPY" || exit 1
uv venv -q .venv || ci_die "uv venv failed"
uv pip install -q --python .venv/bin/python -e '.[test,mutation]' || ci_die "install failed"

# tests that read the git checkout or the docs tree, which the copy does not have, are left out of mutant runs
python3 - "$COPY/pyproject.toml" "$SRCS" "$TESTS" <<'PY'
import sys
path, srcs, tests = sys.argv[1], sys.argv[2].split(), sys.argv[3].split()
q = lambda xs: "[" + ", ".join(f'"{x}"' for x in xs) + "]"
deselect = ["--deselect=tests/report/test_templates.py::test_page_content_matches_golden[comparison]",
            "--deselect=tests/report/test_templates.py::test_page_content_matches_golden[literature]",
            "--deselect=tests/test_docs_layout.py::test_repository_markdown_is_the_allowlist",
            "--deselect=tests/run/test_inputs.py::test_commands_sh_reruns_the_run_set"]
with open(path, "a", encoding="utf-8") as f:
    f.write("\n[tool.mutmut]\n"
            f"source_paths = {q(srcs)}\n"
            'also_copy = ["src", "tests", "docs", "tools", "contrib", "README.md", "CONTRIBUTING.md", "uv.lock"]\n'
            f"pytest_add_cli_args = {q(deselect)}\n"
            f"pytest_add_cli_args_test_selection = {q(tests)}\n")
PY

# mutmut runs the tests in mutants/; the sandbox probe tests need <repo>/.venv/bin/python there, as in a checkout
mkdir -p mutants || ci_die "could not create mutants/"
ln -s ../.venv mutants/.venv || ci_die "could not link .venv into mutants/"

ci_log "mutmut run ($CHILDREN parallel)"
.venv/bin/mutmut run --max-children "$CHILDREN" > "$OUT/run.log" 2>&1
rc=$?
.venv/bin/mutmut results --all true > "$OUT/results.txt" 2>&1
"$TSCI_ROOT/.venv/bin/python" "$TSCI_ROOT/tools/ci/mutation_report.py" shard "$NAME" "$OUT/results.txt" \
  "$OUT/$NAME.json" --copy "$COPY" || ci_die "could not read the mutmut results"
rm -rf "$COPY/mutants"  # large; results.txt and NAME.json keep everything the report needs
[ "$rc" -eq 0 ] || ci_die "mutmut run exited $rc (see $OUT/run.log)"
