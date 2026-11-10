import numpy as np
from scipy.optimize import least_squares
HD,F0,F2,F4,S2=np.load('m.npy')
def levels(Dq,B,C):
    H=Dq*HD+(49*B+7*C)*F2+(441*C/35)*F4
    H=H+1e-3*S2*1e-6
    w,v=np.linalg.eigh(H)
    s=np.einsum('ij,jk,ki->i',v.T,S2,v)
    S=np.round((-1+np.sqrt(1+4*s))/2*2)/2
    return w,S
w,S=levels(0,1000,4000)
u=[]
for e,s in zip(w-w[0],S):
    u.append((round(e,1),s))
print(sorted(set(u))[:6])
def doublets(Dq,B,C):
    w,S=levels(Dq,B,C)
    e=w-w[0]
    d=np.unique(np.round(e[S==0.5],3))
    return e,S,d
e,S,d=doublets(3000,600,2640)
print(S[0],d[:12])
