import numpy as np
from d5 import *
from scipy.optimize import least_squares
sub=[i for i,d in enumerate(dets) if sum(orbs[x][1] for x in d)==3]
allup=idx[tuple(i for i,(m,s) in enumerate(orbs) if s==1)]
def levels(Dq,B,C):
    F=(0.0, 49*B+7*C, 35*C/441*9*0+ 441*C/35)  # F4 = 441C/35
    H=build(F,Dq).real
    Esx=H[allup,allup]
    w,v=np.linalg.eigh(H[np.ix_(sub,sub)])
    Hs=H[np.ix_(sub,sub)]
    # remove sextet: eigenvector with max overlap to allup
    ia=sub.index(allup)
    # cluster
    cl=[]; i=0
    while i<len(w):
        j=i
        while j+1<len(w) and abs(w[j+1]-w[i])<1e-6: j+=1
        cl.append((w[i]-Esx,j-i+1)); i=j+1
    return Esx,cl
if __name__=="__main__":
    Esx,cl=levels(1000.0,800.0,3200.0)
    print(Esx)
    for e,d in cl: print(round(e,2),d)
