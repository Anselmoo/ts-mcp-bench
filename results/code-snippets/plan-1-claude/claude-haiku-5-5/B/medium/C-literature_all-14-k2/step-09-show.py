import numpy as np
from fit import levels
from scipy.optimize import least_squares
def spectrum(B,C,Dq):
    eq,ed=levels(B,C,Dq)
    # remove quartet levels from Ms=1/2 block
    rest=list(ed)
    for e in eq:
        j=int(np.argmin([abs(r-e) for r in rest])); rest.pop(j)
    rest=np.array(rest)
    return eq,rest
def groups(v,tol=1e-3):
    out=[]
    for e in sorted(v):
        if out and abs(e-out[-1][0])<tol: out[-1][1]+=1
        else: out.append([e,1])
    return out
if __name__=='__main__':
    import sys
    B,C,Dq=map(float,sys.argv[1:4])
    eq,dl=spectrum(B,C,Dq)
    g0=eq[0]
    print("quartets:", [(round(e-g0,0),m) for e,m in groups(eq)])
    print("doublets:", [(round(e-g0,0),m) for e,m in groups(dl)])
