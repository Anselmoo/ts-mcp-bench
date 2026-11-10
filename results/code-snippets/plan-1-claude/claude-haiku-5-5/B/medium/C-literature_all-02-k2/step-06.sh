cd /tmp/tsbench-run-vitfy8cz 2>/dev/null || cd /; python3 - << 'EOF'
import numpy as np
from functools import lru_cache
from sympy.physics.wigner import gaunt
from scipy.optimize import fsolve
l=2; ms=list(range(-2,3))
@lru_cache(None)
def G(l1,l2,l3,m1,m2,m3): return float(gaunt(l1,l2,l3,m1,m2,m3))
def Ysum(ma,mc,k,q):
    if mc-ma!=q: return 0.0
    return (-1)**(ma+q)*G(l,l,k,-ma,mc,-q)
def Yprod(mb,md,k,q):
    if md-mb!=q: return 0.0
    return (-1)**mb*G(l,l,k,-mb,md,q)
def Oint(ma,mc):
    tot=0.0
    for (q,coef) in [(0,1.0),(4,np.sqrt(5/14)),(-4,np.sqrt(5/14))]:
        if mc-ma+q!=0: continue
        tot+=coef*(-1)**ma*G(l,4,l,-ma,q,mc)
    return tot
Om=np.array([[Oint(a,c) for c in ms] for a in ms])
w=np.linalg.eigvalsh(Om); SP=w[-1]-w[0]  # eg-t2g
h1=Om*(10/SP)  # per unit Dq: t2g=-4, eg=+6
# two-electron integrals: angular coefficients for k=0,2,4
def ang(a,b,c,d,k):
    return 4*np.pi/(2*k+1)*sum(Ysum(a,c,k,q)*Yprod(b,d,k,q) for q in range(-k,k+1))
A={}
for a,b,c,d in __import__('itertools').product(ms,repeat=4):
    for k in (2,4):
        A[(a,b,c,d,k)]=ang(a,b,c,d,k)
# spin orbitals: (m,s), s=+1/-1 ; index
so=[(m,s) for m in ms for s in (1,-1)]
N=len(so)
def V2(i,j,k_,l_):  # <i j | V | k l> with spin deltas, coefficient of (F2,F4) returned as tuple
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[i],so[j],so[k_],so[l_]
    if sa!=sc or sb!=sd: return (0.0,0.0)
    return (A[(ma,mb,mc,md,2)], A[(ma,mb,mc,md,4)])
states=list(itertools.combinations(range(N),2)) if False else None
import itertools
states=list(itertools.combinations(range(N),2))
idx={s:i for i,s in enumerate(states)}
def apply_ops(ops,st):
    # ops: list of ('c'|'a', orbital) applied right-to-left (rightmost first); st: list of occupied
    occ=list(st); sign=1
    for typ,o in reversed(ops):
        if typ=='a':
            if o not in occ: return None
            p=occ.index(o); sign*=(-1)**p; occ.pop(p)
        else:
            if o in occ: return None
            p=sum(1 for x in occ if x<o); sign*=(-1)**p; occ.insert(p,o)
    return sign, tuple(sorted(occ))
def H_matrix(Dq,B,C,Ms_sector=None):
    F4=441*C/35; F2=(441*B+5*F4)/9
    H=np.zeros((len(states),len(states)))
    # one-body
    for col,st in enumerate(states):
        for a in range(N):
            for b in range(N):
                ma,sa=so[a]; mb,sb=so[b]
                if sa!=sb: continue
                h=Dq*h1[ms.index(ma),ms.index(mb)]
                if h==0: continue
                r=apply_ops([('c',a),('a',b)],st)
                if r is None: continue
                sg,new=r; H[idx[new],col]+=sg*h
    # two-body: 1/2 sum V_abcd a+a a+b a_d a_c
    for col,st in enumerate(states):
        for a,b,c,d in itertools.product(range(N),repeat=4):
            v2=V2(a,b,c,d)
            if v2==(0.0,0.0): continue
            val=0.5*(F2*v2[0]+F4*v2[1])
            if abs(val)<1e-14: continue
            r=apply_ops([('c',a),('c',b),('a',d),('a',c)],st)
            if r is None: continue
            sg,new=r; H[idx[new],col]+=sg*val
    return H
EOF
echo done