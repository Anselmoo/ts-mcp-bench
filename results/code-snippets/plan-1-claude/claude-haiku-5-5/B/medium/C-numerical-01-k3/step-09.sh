cat <<'EOF' | python3 -
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from functools import lru_cache
from scipy.optimize import least_squares
l=2; MS=list(range(-2,3))
@lru_cache(None)
def w3(a,b,c,d,e,f): return float(wigner_3j(a,b,c,d,e,f))
def Vsp(F,ma,mb,mc,md):
    s=0.0
    for k in (0,2,4):
        g=(2*l+1)**2*w3(l,k,l,0,0,0)**2
        t=sum((-1)**q*w3(l,k,l,-ma,q,mc)*w3(l,k,l,-mb,-q,md) for q in range(-k,k+1))
        s+=F[k]*g*t*((-1)**(ma+mb))
    return s
spo=[(m,s) for m in MS for s in (0,1)]
N=10
st=[(i,j) for i,j in itertools.combinations(range(N),2) if spo[i][1]==0 and spo[j][1]==0]
def levels(B,C,Dq):
    F={0:0.0,2:49*B+7*C,4:441*C/35}
    V=np.zeros((N,N,N,N))
    for p,(mp,sp) in enumerate(spo):
     for q,(mq,sq) in enumerate(spo):
      for r,(mr,sr) in enumerate(spo):
       for s_,(ms_,ss) in enumerate(spo):
        if sp==sr and sq==ss: V[p,q,r,s_]=Vsp(F,mp,mq,mr,ms_)
    Peg=np.zeros((5,5)); Peg[2,2]=1.0; Peg[0,0]=Peg[4,4]=0.5; Peg[0,4]=Peg[4,0]=0.5
    hm=-4*Dq*np.eye(5)+10*Dq*Peg
    h=np.zeros((N,N))
    for p in range(5):
      for q in range(5):
        for s in (0,1): h[2*p+s,2*q+s]=hm[p,q]
    D=len(st); Hm=np.zeros((D,D))
    for I,(i,j) in enumerate(st):
      for J,(k,m) in enumerate(st):
        val=V[i,j,k,m]-V[i,j,m,k]
        val+= h[i,k]*(j==m) - h[i,m]*(j==k) + h[j,m]*(i==k) - h[j,k]*(i==m)
        Hm[I,J]=val
    return np.sort(np.linalg.eigvalsh(Hm))
def excit(x):
    B,C,Dq=x
    w=levels(B,C,Dq)
    # distinct levels with multiplicity
    lv=[];
    for e in w:
        if lv and abs(e-lv[-1][0])<1e-6: lv[-1][1]+=1
        else: lv.append([e,1])
    return lv
obs=np.array([20700,30570,42990.])
# parameters: use Dq, B, C; levels: ground = lowest; the nonground distinct levels
lv=excit([500,2000,1000]); print([ (round(a,1),b) for a,b in lv])
EOF