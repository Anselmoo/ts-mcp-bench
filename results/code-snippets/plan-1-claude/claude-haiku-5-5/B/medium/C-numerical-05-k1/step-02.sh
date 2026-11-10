cat << 'EOF' > /tmp/d2.py
import numpy as np, itertools
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
def Vint(F):  # F: dict k->F^k ; returns V[(a,b),(c,d)] 25x25
    V=np.zeros((25,25))
    for k,Fk in F.items():
        if Fk==0: continue
        for q in range(-k,k+1):
            A=Cmat(k,q); Bm=Cmat(k,-q)
            # sum_q (-1)^q <a|C_q|c><b|C_-q|d>
            T=((-1)**q)*np.einsum('ac,bd->abcd',A,Bm).reshape(25,25) if False else None
            T=((-1)**q)*np.kron(A,Bm)  # index (a,b),(c,d)
            V+=Fk*T
    return V
def spectrum(B,Dq):
    F={2:49*B,4:0.0}
    V=Vint(F)
    # one-electron: cubic field = -4Dq + 10Dq*P_eg, P_eg=|0><0|+|e2><e2|
    P=np.zeros((5,5))
    i0=ms.index(0); P[i0,i0]=1
    e2=np.zeros(5); e2[ms.index(2)]=1/np.sqrt(2); e2[ms.index(-2)]=1/np.sqrt(2)
    P+=np.outer(e2,e2)
    h=-4*Dq*np.eye(5)+10*Dq*P
    H=np.kron(h,np.eye(5))+np.kron(np.eye(5),h)+V
    # antisymmetric subspace
    Pa=(np.eye(25)-np.kron(np.eye(5),np.eye(5)).reshape(25,25)*0)  # placeholder
    S=np.zeros((25,25))
    for a in range(5):
        for b in range(5):
            S[a*5+b,a*5+b]+=1; S[a*5+b,b*5+a]-=1
    S/=2
    w,U=np.linalg.eigh(S)
    Q=U[:,w>0.5]
    Hr=Q.T@H@Q
    return np.sort(np.linalg.eigvalsh(Hr))
if __name__=="__main__":
    ev=spectrum(1.0,0.0)
    print("free ion B=1 eigenvalues:",np.round(ev,4))
EOF
python3 /tmp/d2.py