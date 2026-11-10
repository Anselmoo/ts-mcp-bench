
cd /tmp/tsbench-run-la9r0a6w && python3 -c "
from d3 import *
import numpy as np
H=build(0,0,-1.0); print(np.round(H.real,3)[:3,:3]); print(np.round(np.linalg.eigvalsh(H),3))
Peg=np.zeros((5,5)); Peg[2,2]=1; v=np.zeros(5); v[0]=v[4]=1/np.sqrt(2); Peg+=np.outer(v,v); print(np.linalg.eigvalsh(Peg))
print(states[:3], N)
"