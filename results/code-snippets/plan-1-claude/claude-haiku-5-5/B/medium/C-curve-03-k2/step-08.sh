
cd /tmp/tsbench-run-me24kyq4 && python3 -c "
exec(open('ts.py').read())
import numpy as np
for C in (0.0,1.0,4.0):
  V=Vtab(1.0,C)
  S,H=build(2,V,np.zeros((5,5),complex))
  e=np.linalg.eigvalsh(H); print(C, np.round(e-e[0],4))
"