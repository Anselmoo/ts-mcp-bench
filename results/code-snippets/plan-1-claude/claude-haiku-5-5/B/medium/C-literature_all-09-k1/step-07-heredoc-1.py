import numpy as np
d=np.load('<SANDBOX_TMP>/ops.npz'); M2,M4=d['M2'],d['M4']
for name,(F2,F4) in {'B only':(49,0),'C only':(0,441/35)}.items():
    ev=np.linalg.eigvalsh(F2*M2+F4*M4); print(name, np.round(ev-ev[0],3))
