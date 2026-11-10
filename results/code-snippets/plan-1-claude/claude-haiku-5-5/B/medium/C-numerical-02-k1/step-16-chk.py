import numpy as np
d=np.load('mats.npz'); Hd,H2,H4,S2=d['Hd'],d['H2'],d['H4'],d['S2']
from fit3 import levels, qlev
for Dq,F2,F4 in [(900,1000,600),(1000,800,500),(900,1000,0)]:
    v=qlev(Dq,F2,F4); print(Dq,F2,F4, np.round(v-v[0],0), len(v))
