import numpy as np
from scipy.optimize import least_squares
z=np.load('m.npz');HD,F2,F4,S2=z['HD'],z['F2'],z['F4'],z['S2']
def levels(Dq,B,C):
    H=Dq*HD+(49*B+7*C)*F2+(441*C/35)*F4
    w,v=np.linalg.eigh(H+1e-4*S2)
    s=np.einsum('ji,jk,ki->i',v,S2,v)
    S=np.round(-1+np.sqrt(1+4*s))/2
    return w-w[0],S
e,S=levels(0,1000,4000)
print(sorted(set(zip(np.round(e,0),S)))[:5])
def dbl(Dq,B,C=None):
    e,S=levels(Dq,B,4.4*B if C is None else C)
    vals=np.round(e[S==0.5],2); u=np.unique(vals); return S[0],u
print(dbl(3000,600))
