import numpy as np
from scipy.optimize import least_squares
M=np.load('mats.npz')
def lev(Dq,B,C):
    F4=C/35; F2=B+5*F4
    H=49*F2*M['H2']+441*F4*M['H4']+Dq*M['HD']
    w,v=np.linalg.eigh(H)
    S=np.einsum('ij,jk,ki->i',v.T,M['S2'],v)
    # group
    out=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and abs(w[j]-w[i])<1e-3: j+=1
        out.append((w[i],j-i,round(S[i:j].mean(),2))); i=j
    return out
def assign(Dq,B,C):
    L=lev(Dq,B,C); E0=L[0][0]
    q=[(e-E0,n) for e,n,s in L if abs(s-3.75)<0.1]
    dbl=[(e-E0,n) for e,n,s in L if abs(s-0.75)<0.1]
    qT1=[e for e,n in q if n==12]; qT2=[e for e,n in q if n==12]
    return L,q,dbl
L,q,dbl=assign(900,1000,4000)
print(q); print(dbl[:8])
