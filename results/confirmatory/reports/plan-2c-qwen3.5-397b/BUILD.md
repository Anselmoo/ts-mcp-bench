# How these pages were built

- Code: the second commit of this repository (the benchmark tree e7f9560 plus the confirmatory
  report, `stats hypotheses --family secondary` and the analyses; runner, conditions, plans and scoring
  unchanged).
- Input: copies of the published run folders `results/confirmatory/<plan>`; plans 2a to 2c in one folder
  with `results/confirmatory/secondary-family/hypotheses.json` (the report shows it as the secondary family).
- Commands, with SOURCE_DATE_EPOCH=0 (one `--runs` per run set: secondary/plan-2c-qwen3.5-397b)
  - `tsbench report full --runs <set> ... --split confirmatory --i-have-preregistered 10.5281/zenodo.23889782 --images results/images --redactions results/REDACTIONS.csv --coverage COVERAGE.json --mutation <folder of the shards> --out report.html --title "TS-MCP benchmark: confirmatory plan 2c (qwen3.5-397b-a17b)"`
  - report.html is stored as `report.html.zip` (one file, deflate, time stamp 1980-01-01): unzipped it is the page.
  - `tsbench report dashboard --runs <set> ... --split confirmatory --i-have-preregistered 10.5281/zenodo.23889782 --out dashboard.html --title "TS-MCP benchmark: confirmatory plan 2c (qwen3.5-397b-a17b)"`
- Code checks: line coverage from the full test suite (coverage.py JSON and pytest.log) and mutation testing
  (mutmut, tools/ci/mutation.sh) of the seven shards score stats tasks-oracles plan-core run conditions analyze, both on the code of this commit.
