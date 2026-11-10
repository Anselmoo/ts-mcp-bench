cd /tmp && python3 - << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import brentq
l=2
orbs=[(m,s) for m in range(-2,3) for s in (0.5,-0.5)]
N=len(orbs)
W={}
def w3(*a):
    if a not in W: W[a]=float(wigner_3j(*a))
    return W[a]
def ck(k,ma,mc,q):
    if ma-mc!=q: return 0.0
    return (-1)**(l-ma)*w3(l,k,l,-ma,q,mc)*(-1)**l*(2*l+1)*w3(l,k,l,0,0,0)
ang={k:np.zeros((N,N,N,N)) for k in (0,2,4)}
for a,(ma,sa) in enumerate(orbs):
 for b,(mb,sb) in enumerate(orbs):
  for c,(mc,sc) in enumerate(orbs):
   for d,(md,sd) in enumerate(orbs):
    if sa!=sc or sb!=sd: continue
    for k in (0,2,4):
        t=0.0
        for q in range(-k,k+1):
            t+=(-1)**q*ck(k,ma,mc,-q)*ck(k,mb,md,q)
        ang[k][a,b,c,d]=t
states=list(itertools.combinations(range(N),5))
idx={s:i for i,s in enumerate(states)}
def apply_ops(occ,ops):
    occ=list(occ); sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in occ: return None,0
            p=occ.index(o); sign*=(-1)**p; occ.pop(p)
        else:
            if o in occ: return None,0
            p=sum(1 for x in occ if x<o); sign*=(-1)**p; occ.insert(p,o)
    return tuple(sorted(occ)),sign
# precompute ee operator pieces: list of (a,b,c,d,k-values)
terms=[]
for a in range(N):
 for b in range(N):
  for c in range(N):
   for d in range(N):
    v=[ang[k][a,b,c,d] for k in (0,2,4)]
    if max(abs(x) for x in v)<1e-12: continue
    if a==b or c==d: continue
    terms.append((a,b,c,d,v))
D=len(states)
def mats():
    # returns matrices for F2 and F4 coefficients and F0 (constant)
    M={2:np.zeros((D,D)),4:np.zeros((D,D))}
    for i,s in enumerate(states):
        for (a,b,c,d,v) in terms:
            nocc,sg=apply_ops(s,[('c',a),('c',b),('a',d),('a',c)])
            if nocc is None: continue
            M[2][idx[nocc],i]+=0.5*v[1]*sg
            M[4][idx[nocc],i]+=0.5*v[2]*sg
    return M
M=mats()
# one-body: h = -4Dq I + 10Dq Peg
v0=np.zeros(5); v0[2]=1
v2=np.zeros(5); v2[4]=1/np.sqrt(2); v2[0]=1/np.sqrt(2)
Peg=np.outer(v0,v0)+np.outer(v2,v2)
def h1(): 
    H=np.zeros((D,D)); Hd=np.zeros((D,D))
    hI=np.zeros((N,N)); hP=np.zeros((N,N))
    for a,(ma,sa) in enumerate(orbs):
     for b,(mb,sb) in enumerate(orbs):
      if sa==sb:
        hI[a,b]=(1 if ma==mb else 0); hP[a,b]=Peg[ma+2,mb+2]
    def op(h):
        R=np.zeros((D,D))
        for i,s in enumerate(states):
            for a in range(N):
              for b in range(N):
                if abs(h[a,b])<1e-14: continue
                nocc,sg=apply_ops(s,[('c',a),('a',b)])
                if nocc is None: continue
                R[idx[nocc],i]+=h[a,b]*sg
        return R
    return op(hI),op(hP)
OI,OP=h1()
# Number-of-electron-pair operator check: total two-body needs 1/2 sum over pairs already handled.
def H(Dq,B,C):
    F4=C*441/35.0; F2=(441*B+5*F4)/9.0
    return F2*M[2]+F4*M[4]+(-4*Dq)*OI+10*Dq*OP
# spin S^2
# build S^2 via Sz,S+ 
def Sops():
    Sz=np.zeros((D,D)); Sp=np.zeros((D,D))
    for i,s in enumerate(states):
        Sz[i,i]=sum(0.5 if (o%2==0) else -0.5 for o in s)  # index: even=up
        for a in range(N):
          for b in range(N):
            pass
    # S+ = sum_m c+_{m,up} c_{m,down}
    for m in range(-2,3):
        up=orbs.index((m,0.5)); dn=orbs.index((m,-0.5))
        for i,s in enumerate(states):
            nocc,sg=apply_ops(s,[('c',up),('a',dn)])
            if nocc is None: continue
            Sp[idx[nocc],i]+=sg
    S2=Sp.T@Sp+Sz@Sz+ (Sz)  # S^2 = S-S+ + Sz^2 + Sz ; S-S+ = S+^T S+
    return S2
S2=Sops()
# check orbs index parity: orbs ordering (m,0.5) index even, (m,-0.5) odd
EOF
echo done