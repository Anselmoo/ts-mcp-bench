import numpy as np
d=np.load('parts.npz'); Hob,H2,H4,S2=d['Hob'],d['H2'],d['H4'],d['S2']
w,v=np.linalg.eigh(S2)
Dd=v[:,np.abs(w-3/4)<1e-6]; Q=v[:,np.abs(w-15/4)<1e-6]
def lv(Dq,B,C,P):
    F2=49*B+7*C; F4=7*C/5
    H=Dq*Hob+F2*H2+F4*H4
    return np.linalg.eigvalsh(P.T@H@P)
for Dq in [0,2155]:
    e=lv(Dq,600,3000,Dd); g=lv(Dq,600,3000,Q)
    E0=g.min()
    print("Dq",Dq,"ground", round(E0,1))
    vals=np.round(e-E0,1)
    u,c=np.unique(vals,return_counts=True)
    print([ (x,k) for x,k in zip(u,c)])
