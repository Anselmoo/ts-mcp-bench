
cd /tmp/tsbench-run-ub74fb61 && cat << 'EOF' > grid.py
import numpy as np
from solve import model
best=[]
for Dq in [500,650,800,950]:
  for B in [500,700,900]:
    for CB in [3.5,4.5]:
        p=[Dq,B,CB*B]
        T,E=model(p)
        print(p, np.round(T[:3]), np.round(E[:2]))
EOF
timeout 900 python3 grid.py 2>&1 | grep -v "^\[" | tail -40
