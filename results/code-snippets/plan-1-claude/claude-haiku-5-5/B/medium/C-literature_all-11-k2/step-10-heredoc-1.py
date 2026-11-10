import numpy as np
from sympy.physics.wigner import wigner_3j
from math import sqrt
l=2; ms=list(range(-2,3))
def Ck(k,q,m,mp):
    if abs(q)>k: return 0.0
    return float((-1)**(l-m)*wigner_3j(l,k,l,-m,q,mp)*wigner_3j(l,k,l,0,0,0)*(2*l+1))
def Acoef(k,m1,m2,m3,m4):
    return sum((-1)**q*Ck(k,q,m1,m3)*Ck(k,-q,m2,m4) for q in range(-k,k+1))
Vk={k:np.zeros((5,5,5,5)) for k in (0,2,4)}
for k in (0,2,4):
    for i1,m1 in enumerate(ms):
        for i2,m2 in enumerate(ms):
            for i3,m3 in enumerate(ms):
                for i4,m4 in enumerate(ms):
                    if m1+m2==m3+m4: Vk[k][i1,i2,i3,i4]=Acoef(k,m1,m2,m3,m4)
s2=sqrt(2)
U=np.zeros((5,5),dtype=complex)
idx={m:i for i,m in enumerate(ms)}
U[0,idx[0]]=1
U[1,idx[2]]=1/s2; U[1,idx[-2]]=1/s2
U[2,idx[2]]=1/(1j*s2); U[2,idx[-2]]=-1/(1j*s2)
U[3,idx[1]]=1/s2; U[3,idx[-1]]=-1/s2
U[4,idx[1]]=1/(1j*s2); U[4,idx[-1]]=1/(1j*s2)
print(np.round(U@U.conj().T,6))
Vr={k:np.einsum('aw,bx,cy,dz,wxyz->abcd',U.conj(),U.conj(),U,U,Vk[k]) for k in Vk}
for k in Vr: print(k, np.abs(Vr[k]).max(), np.abs(Vr[k].imag).max())
print(np.round(Vr[2][0,0,0,0].real,5), np.round(Vr[2][2,2,2,2].real,5), np.round(Vr[2][2,3,2,3].real,5))
