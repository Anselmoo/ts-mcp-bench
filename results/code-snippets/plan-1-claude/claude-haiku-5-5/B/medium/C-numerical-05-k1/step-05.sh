cd /; python3 - << 'EOF'
import numpy as np
from sympy.physics.wigner import wigner_3j
from scipy.optimize import brentq
l=2; ms=list(range(-2,3))
def C(k,m,mp,q):
    if q!=m-mp: return 0.0
    return float((-1)**(l-m)*wigner_3j(l,k,l,-m,q,mp)*(2*l+1)*(-1)**l*wigner_3j(l,k,l,0,0,0))
def Cmat(k,q):
    return np.array([[C(k,m,mp,q) for mp in ms] for m in ms])
def Vint(F):
    V=np.zeros((25,25))
    for q in range(-2,3):
        V+=F*((-1)**q)*np.kron(Cmat(2,q),Cmat(2,-q))
    return V
S=np.zeros((25,25))
for a in range(5):
    for b in range(5):
        S[a*5+b,a*5+b]+=1; S[a*5+b,b*5+a]-=1
S/=2
w,U=np.linalg.eigh(S); Q=U[:,w>0.5]
P=np.zeros((5,5)); P[2,2]=1
e2=np.zeros(5); e2[0]=e2[4]=1/np.sqrt(2)
P+=np.outer(e2,e2)
def levels(B,Dq):
    V=Vint(49*B)
    h=-4*Dq*np.eye(5)+10*Dq*P
    H=np.kron(h,np.eye(5))+np.kron(np.eye(5),h)+V
    return np.linalg.eigvalsh(Q.T@H@Q)
def distinct(ev,tol=1e-6):
    out=[]
    for e in ev:
        if out and abs(e-out[-1][0])<tol: out[-1][1]+=1
        else: out.append([e,1])
    return out
for B,Dq in [(1.0,0.0),(500.,1573.)]:
    print(B,Dq,[(round(e,3),d) for e,d in distinct(levels(B,Dq))])
EOF