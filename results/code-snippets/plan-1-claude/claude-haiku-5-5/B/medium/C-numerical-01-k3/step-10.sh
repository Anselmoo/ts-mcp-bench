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
Vc={}
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
def levs(x):
    w=levels(*x)
    lv=[]
    for e in w:
        if lv and abs(e-lv[-1][0])<1e-6: lv[-1][1]+=1
        else: lv.append([e,1])
    g=lv[0][0]
    return [e-g for e,_ in lv[1:]], [d for _,d in lv]
obs=np.array([20700,30570,42990.])
best=[]
for perm in itertools.permutations(range(3)):
    # perm[i]: observed index assigned to nonground level i (3fold lower, 3fold upper, singlet ordering by energy)
    def res(x):
        e,_=levs(x)
        return (np.array(e)[list(range(3))]-obs[list(perm)])/1000.0
    sols=[]
    for B0 in (300,600,900):
      for r0 in (3,4.5):
        for Dq0 in (800,1200):
          try:
            s=least_squares(res,[B0,r0*B0,Dq0],bounds=([50,0,100],[3000,30000,5000]),xtol=1e-12,ftol=1e-12,gtol=1e-12)
            if s.cost<1e-10: sols.append(s.x)
          except Exception as ex: pass
    if sols:
        u=np.unique(np.round(np.array(sols),1),axis=0)
        for x in u:
            e,d=levs(x)
            print(perm, "B=%.1f C=%.1f Dq=%.1f C/B=%.2f"%(x[0],x[1],x[2],x[1]/x[0]), "levels",np.round(e,0),d)
EOF