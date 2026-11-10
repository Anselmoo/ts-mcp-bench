
cd /tmp/tsbench-run-uqj8uf3b && sleep 60; cat out3.txt; OMP_NUM_THREADS=1 python3 -c "
from fast import levels
for p in [(514.4,537.1,2773.7),(532.4,158.6,4060.9)]:
    print(p); [print(round(e,0),m) for e,m in levels(*p)]
"