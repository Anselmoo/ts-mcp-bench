import numpy as np
from itertools import combinations
from scipy.special import sph_harm
ms=[-2,-1,0,1,2]
nth,nph=40,80
x,w=np.polynomial.legendre.leggauss(nth)
th=np.arccos(x); ph=np.linspace(0,2*np.pi,nph,endpoint=False)
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.ones(nph))*(2*np.pi/nph)
def Y(l,m,t,p): return sph_harm(m,l,p,t)
def ang(k):
    A=np.zeros((5,5,5,5),complex)
    for q in range(-k,k+1):
        Ykq=Y(k,q,TH,PH)
        M1=np.zeros((5,5),complex); M2=np.zeros((5,5),complex)
        for i,m1 in enumerate(ms):
            for j,m3 in enumerate(ms):
                M1[i,j]=np.sum(W*np.conj(Y(2,m1,TH,PH))*np.conj(Ykq)*Y(2,m3,TH,PH))
                M2[i,j]=np.sum(W*np.conj(Y(2,m1,TH,PH))*Ykq*Y(2,m3,TH,PH))
        A+=np.einsum('ac,bd->abcd',M1,M2)*(4*np.pi/(2*k+1))
    return A
A2=ang(2); A4=ang(4)
idx={m:i for i,m in enumerate(ms)}
P=np.zeros((5,5),complex); P[idx[0],idx[0]]=1
u=np.zeros(5,complex); u[idx[2]]=1/np.sqrt(2); u[idx[-2]]=1/np.sqrt(2)
P+=np.outer(u,np.conj(u))
h_dq=-4*np.eye(5)+10*P
pairs=list(combinations(range(5),2))
Bm=[]
for (i,j) in pairs:
    v=np.zeros(25,complex); v[i*5+j]+=1/np.sqrt(2); v[j*5+i]-=1/np.sqrt(2); Bm.append(v)
Bm=np.array(Bm).T
def build(Dq,B,C):
    F4=12.6*C; F2=441*B+5*F4
    V=(F2*A2+F4*A4).reshape(25,25)
    I5=np.eye(5)
    H=np.kron(Dq*h_dq,I5)+np.kron(I5,Dq*h_dq)+V
    Hs=Bm.conj().T@H@Bm
    return np.sort(np.linalg.eigvalsh((Hs+Hs.conj().T)/2))
print("Dq only:",build(1,0,0).real.round(4))
print("B only:",build(0,1,0).real.round(4))
print("C only:",build(0,0,1).real.round(4))
