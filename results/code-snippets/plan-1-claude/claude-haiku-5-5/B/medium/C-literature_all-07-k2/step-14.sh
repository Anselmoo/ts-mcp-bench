
cd /tmp/tsbench-run-ub74fb61 && cat << 'EOF' > scan.py
import numpy as np
from model import model
for B in [600,700,750,800,850,900,950,1000]:
    C=(23000-17*B)/5
    row=[]
    for Dq in range(500,1101,100):
        T,E=model([Dq,B,C]); row.append((Dq,round(T[0]),round(T[1])))
    print(B,round(C),row,flush=True)
EOF
timeout 900 python3 scan.py
