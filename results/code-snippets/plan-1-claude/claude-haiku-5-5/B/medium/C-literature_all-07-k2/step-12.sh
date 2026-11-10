
cd /tmp/tsbench-run-ub74fb61 && cat << 'EOF' > model.py
import numpy as np
from fit import levels
def model(p):
    Dq,B,C=p
    Esx,cl=levels(Dq,B,C)
    T=[e for e,d in cl if d==3 and e>1]
    E=[e for e,d in cl if d==2 and e>1]
    return T,E
EOF
cat << 'EOF' > grid.py
import numpy as np
from model import model
for Dq in [500,700,900]:
  for B in [600,800]:
    for CB in [4.0,4.5]:
        p=[Dq,B,CB*B]
        T,E=model(p)
        print(p, np.round(T[:3]), np.round(E[:2]), flush=True)
EOF
timeout 900 python3 grid.py
