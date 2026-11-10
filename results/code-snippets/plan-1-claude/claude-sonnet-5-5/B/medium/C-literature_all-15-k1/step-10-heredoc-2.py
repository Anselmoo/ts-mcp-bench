import sys; sys.path.insert(0,'<SANDBOX_TMP>')
import numpy as np
from d7 import *
def q(Dq,B):
    g=groups(lv(Dq,B,3000)['q']); return np.array([x-g[0][0] for x,c in g[1:4]])
best=[]
for Dq in range(800,1300,20):
  for B in range(500,1100,20):
    r=q(Dq,B)-[8480,16305,20360]; best.append((np.sum(r**2),Dq,B,r.round()))
best.sort(key=lambda t:t[0]); print(best[:5])
