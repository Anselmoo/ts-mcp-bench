import numpy as np
from fit import levels
from ham import build
import fit
Dq,B,C=1000,900,4000
w,S=levels(Dq,B,C)
# group distinct levels
lev=[]
for e,s in zip(w,S):
    if lev and abs(e-lev[-1][0])<1e-6: lev[-1][2]+=1
    else: lev.append([e,s,1])
for e,s,n in lev[:12]: print(round((e-w[0])),round(s,2),n)
