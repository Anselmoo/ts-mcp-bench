import numpy as np
from sympy.physics.wigner import wigner_3j
l=2
ms=list(range(-2,3))
def C(k,m,mp,q):
    if q!=m-mp: return 0.0
    return float((-1)**(l-m)*wigner_3j(l,k,l,-m,q,mp)*(2*l+1)*(-1)**l*wigner_3j(l,k,l,0,0,0))
def Cmat(k,q):
    M=np.zeros((5,5))
    for i,m in enumerate(ms):
        for j,mp in enumerate(ms):
            M[i,j]=C(k,m,mp,q)
    return M
def Vint(F):
    V=np.zeros((25,25))
    for k,Fk in F.items():
        if Fk==0: continue
        for q in range(-k,k+1):
            V+=Fk*((-1)**q)*np.kron(Cmat(k,q),Cmat(k,-q))
    return V
S=np.zeros((25,25))
for a in range(5):
    for b in range(5):
        S[a*5+b,a*5+b]+=1; S[a*5+b,b*5+a]-=1
S/=2
w,U=np.linalg.eigh(S)
Q=U[:,w>0.5]
def spectrum(B,Dq):
    V=Vint({2:49*B,4:0.0})
    P=np.zeros((5,5))
    P[ms.index(0),ms.index(0)]=1
    e2=np.zeros(5); e2[ms.index(2)]=1/np.sqrt(2); e2[ms.index(-2)]=1/np.sqrt(2)
    P+=np.outer(e2,e2)
    h=-4*Dq*np.eye(5)+10*Dq*P
    H=np.kron(h,np.eye(5))+np.kron(np.eye(5),h)+V
    return np.sort(np.linalg.eigvalsh(Q.T@H@Q))
print("free ion B=1:",np.round(spectrum(1.0,0.0),4))
