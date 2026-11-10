import numpy as np
from itertools import combinations
from scipy.optimize import least_squares
from scipy.special import sph_harm
# l=2 complex orbitals m=-2..2 ; grid integration on sphere
ms=[-2,-1,0,1,2]
nth,nph=40,80
x,w=np.polynomial.legendre.leggauss(nth)
th=np.arccos(x); ph=np.linspace(0,2*np.pi,nph,endpoint=False)
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.ones(nph))*(2*np.pi/nph)
def Y(l,m,t,p): return sph_harm(m,l,p,t)  # scipy: sph_harm(m,n,azimuth,polar)
# angular coefficients a_k[m1,m2,m3,m4] = (4pi/(2k+1)) sum_q int Y_2m1* Y_kq* Y_2m3 * int Y_2m2* Y_kq Y_2m4
def ang(k):
    A=np.zeros((5,5,5,5),complex)
    for q in range(-k,k+1):
        Ykq=Y(k,q,TH,PH)
        M1=np.zeros((5,5),complex)  # <m1|Y_kq*|m3>
        for i,m1 in enumerate(ms):
            for j,m3 in enumerate(ms):
                M1[i,j]=np.sum(W*np.conj(Y(2,m1,TH,PH))*np.conj(Ykq)*Y(2,m3,TH,PH))
        M2=np.zeros((5,5),complex)  # <m2|Y_kq|m4>
        for i,m2 in enumerate(ms):
            for j,m4 in enumerate(ms):
                M2[i,j]=np.sum(W*np.conj(Y(2,m2,TH,PH))*Ykq*Y(2,m4,TH,PH))
        A+=np.einsum('ac,bd->abcd',M1,M2)*(4*np.pi/(2*k+1))
    return A
A0,A2,A4=ang(0),ang(2),ang(4)
# cubic one-body: V=-4Dq I + 10Dq P_eg (per Dq unit)
P=np.zeros((5,5),complex)
idx={m:i for i,m in enumerate(ms)}
P[idx[0],idx[0]]=1
u=np.zeros(5,complex); u[idx[2]]=1/np.sqrt(2); u[idx[-2]]=1/np.sqrt(2)
P+=np.outer(u,np.conj(u))
h_dq=-4*np.eye(5)+10*P
pairs=list(combinations(range(5),2))
def build(Dq,B,C):
    F4=12.6*C; F2=441*B+5*F4
    V=F2*A2+F4*A4  # F0 irrelevant (same-spin)
    # two-electron product-space operator on 25 states
    H=np.zeros((25,25),complex)
    h=h_dq*Dq
    I5=np.eye(5)
    H=np.kron(h,I5)+np.kron(I5,h)+V.reshape(25,25)
    # antisymmetric pair states
    basis=[]
    for (i,j) in pairs:
        v=np.zeros(25,complex)
        v[i*5+j]+=1/np.sqrt(2); v[j*5+i]-=1/np.sqrt(2)
        basis.append(v)
    Bm=np.array(basis).T
    Hs=Bm.conj().T@H@Bm
    return np.sort(np.linalg.eigvalsh((Hs+Hs.conj().T)/2))
# check: pure Dq (B=C=0) energies
print(build(1.0,0,0))
