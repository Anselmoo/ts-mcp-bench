import numpy as np
from scipy.optimize import least_squares
from sym import analyse
def pick(B,C,Dq):
    o=analyse(B,C,Dq)
    g0=o['Ms32'][0][0]
    q=[(e-g0,m,chi) for e,m,chi in o['Ms32']]
    d=[(e-g0,m,chi) for e,m,chi in o['Ms12'] if True]
    # remove quartet levels from Ms12 list (match by energy)
    qe=[x[0] for x in q]
    dd=[]
    for e,m,chi in d:
        mm=m
        for qq in qe:
            if abs(qq-e)<1e-3: mm-=1 if False else 0
        dd.append((e,m,chi))
    T2g_q=[e for e,m,chi in q if m==3 and chi==-1][0]
    T1gP_q=[e for e,m,chi in q if m==3 and chi==1 and e>1000][0]
    # doublet T1g second: 3-fold doublets with chi=+1 excluding quartet-coincident ones
    qlist=[(e,m) for e,m,chi in q]
    dT1=[]
    for e,m,chi in o['Ms12']:
        if m==3 and chi==1:
            # check whether this cluster equals a quartet level (count)
            if any(abs(e-g0-qe_)<1e-3 for qe_ in qe if abs(qe_)>1e-3 and False): continue
            dT1.append(e-g0)
    return T2g_q, T1gP_q, dT1
def res(p):
    Dq,B,C=p
    t2,t1p,dT1=pick(B,C,Dq)
    return [t2-8100, t1p-19400, dT1[1]-21600]
if __name__=='__main__':
    print(pick(960,4300,810))
    s=least_squares(res,[810,900,4000],diff_step=1e-3)
    print("fit Dq,B,C:",s.x, "resid",res(s.x))
