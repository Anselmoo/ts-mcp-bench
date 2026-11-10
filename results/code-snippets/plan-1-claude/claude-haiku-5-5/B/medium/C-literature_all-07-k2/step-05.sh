
cd /tmp/tsbench-run-ub74fb61 && cat << 'EOF' > test2.py
import numpy as np, collections
from d5 import *
sub=[i for i,d in enumerate(dets) if sum(orbs[x][1] for x in d)==3]
for F in [(0,1,0),(0,0,1)]:
    H=build(F,0.0)
    Hs=H[np.ix_(sub,sub)].real
    w=np.linalg.eigvalsh(Hs)
    print(F, collections.Counter(np.round(w,6)))
EOF
timeout 500 python3 test2.py
