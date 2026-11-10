from d3 import *
import numpy as np
def levels(H):
    w=np.linalg.eigvalsh(H)
    out=[]
    for x in w:
        if out and abs(out[-1][0]-x)<1e-6: out[-1][1]+=1
        else: out.append([x,1])
    return out
for B,C in [(1,0),(0,1)]:
    print(B,C,[(round(a,4),b) for a,b in levels(build_H(0,B,C))])
