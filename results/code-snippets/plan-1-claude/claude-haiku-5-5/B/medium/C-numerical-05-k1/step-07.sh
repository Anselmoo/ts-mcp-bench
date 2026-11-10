cd /; python3 - << 'EOF'
import numpy as np
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
l=2; ms=list(range(-2,3))
def C(k,m,mp,q):
    if q!=m-mp: return 0.0
    return float((-1)**(l-m)*wigner_3j(l,k,l,-m,q,mp)*(2*l+1)*(-1)**l*wigner_3j(l,k,l,0,0,0))
def Cmat(k,q): return np.array([[C(k,m,mp,q) for mp in ms] for m in ms])
V0=np.zeros((25,25))
for q in range(-2,3): V0+=((-1)**q)*np.kron(Cmat(2,q),Cmat(2,-q))
S=np.zeros((25,25))
for a in range(5):
    for b in range(5):
        S[a*5+b,a*5+b]+=1; S[a*5+b,b*5+a]-=1
S/=2
w,U=np.linalg.eigh(S); Q=U[:,w>0.5]
P=np.zeros((5,5)); P[2,2]=1
e2=np.zeros(5); e2[0]=e2[4]=1/np.sqrt(2); P+=np.outer(e2,e2)
def levels(B,Dq):
    h=-4*Dq*np.eye(5)+10*Dq*P
    H=np.kron(h,np.eye(5))+np.kron(np.eye(5),h)+49*B*V0
    return np.linalg.eigvalsh(Q.T@H@Q)
def terms(B,Dq):
    ev=levels(B,Dq)
    g=ev[0]
    # distinct levels
    d=[]
    for e in ev:
        if d and abs(e-d[-1])<1e-6: continue
        d.append(e)
    return d  # ground, then others ascending
obs=np.array([15730.,24030.,32750.])
# identify excited levels: T2 (pure, 3-fold), T1 (2nd), A2 (1-fold)
def model(p):
    Dq,B=p
    d=terms(B,Dq)
    return d
for B0 in [300,600,900]:
  for Dq0 in [1000,1500,2000]:
    pass
d=terms(600,1573); print([round(x,1) for x in d])
# Assignment: 3 spin-allowed bands = gnd->T2, gnd->T1(2nd), gnd->A2 (all triplets)
def res(p):
    d=terms(p[1],p[0])
    # levels: d[0]=gnd(T1). Excited: sorted
    ex=np.array(d[1:])-d[0]
    return ex
for p0 in [(1500,500),(1800,700),(1300,400)]:
    ex=res(p0); print(p0, np.round(ex,1))
EOF