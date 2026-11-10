
cd "$(pwd)" 2>/dev/null; pwd; touch ./_t 2>&1 && echo writable_cwd; python3 -c "import numpy, scipy; print('ok')"
