import numpy as np
from scipy.optimize import least_squares
from sym import analyse
def levels(B,C,Dq):
    o=analyse(B,C,Dq)
    g0=o['Ms32'][0][0]
    q=[(e-g0,m,chi) for e,m,chi in o['Ms32']]
    qe=[x[0] for x in q]
    dl=[]
    for e,m,chi in o['Ms12']:
        E=e-g0
        if any(abs(E-x)<1e-2 for x in qe): continue  # quartet level
        dl.append((E,m,chi))
    return q, dl
def res(p, verbose=False):
    Dq,B,C=p
    q,dl=levels(B,C,Dq)
    t2=[e for e,m,c in q if m==3 and c==-1][0]
    t1p=[e for e,m,c in q if m==3 and c==1 and e>1]
    t1p=t1p[0]
    T1=[e for e,m,c in dl if m==3 and c==1]
    if verbose: print("doublet T1g:",T1)
    return [t2-8100, t1p-19400, T1[1]-21600]
if __name__=='__main__':
    s=least_squares(res,[810,900,4000],diff_step=1e-4)
    print("fit Dq,B,C:",s.x,"resid",res(s.x))
    res(s.x,True)
    q,dl=levels(*[s.x[1],s.x[2],s.x[0]])
    print("quartets",[(round(e,0),m,c) for e,m,c in q])
