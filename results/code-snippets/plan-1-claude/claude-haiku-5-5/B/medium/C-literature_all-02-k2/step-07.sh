cd /tmp/tsbench-run-vitfy8cz 2>/dev/null || cd /; cat > /dev/null << 'EOF'
EOF
python3 - << 'EOF'
import numpy as np, itertools
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
w=np.linalg.eigvalsh(Om); SP=w[-1]-w[0]
h1=Om*(10/SP)
def ang(a,b,c,d,k):
    return 4*np.pi/(2*k+1)*sum(Ysum(a,c,k,q)*Yprod(b,d,k,q) for q in range(-k,k+1))
A={}
for a,b,c,d in itertools.product(ms,repeat=4):
    for k in (2,4): A[(a,b,c,d,k)]=ang(a,b,c,d,k)
so=[(m,s) for m in ms for s in (1,-1)]; N=len(so)
def V2(i,j,k_,l_):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[i],so[j],so[k_],so[l_]
    if sa!=sc or sb!=sd: return (0.0,0.0)
    return (A[(ma,mb,mc,md,2)], A[(ma,mb,mc,md,4)])
states=list(itertools.combinations(range(N),2)); idx={s:i for i,s in enumerate(states)}
def apply_ops(ops,st):
    occ=list(st); sign=1
    for typ,o in reversed(ops):
        if typ=='a':
            if o not in occ: return None
            p=occ.index(o); sign*=(-1)**p; occ.pop(p)
        else:
            if o in occ: return None
            p=sum(1 for x in occ if x<o); sign*=(-1)**p; occ.insert(p,o)
    return sign, tuple(sorted(occ))
# precompute ee operator pieces (independent of B,C): list of (a,b,c,d,F2coef,F4coef) and cf
ee_terms=[]
for a,b,c,d in itertools.product(range(N),repeat=4):
    v=V2(a,b,c,d)
    if v==(0.0,0.0): continue
    ee_terms.append((a,b,c,d,v))
one=[]
for a in range(N):
    for b in range(N):
        if so[a][1]!=so[b][1]: continue
        one.append((a,b,h1[ms.index(so[a][0]),ms.index(so[b][0])]))
# matrices: H = Dq*H_cf + F2*H_F2 + F4*H_F4
def mats():
    Hcf=np.zeros((len(states),)*2); H2=np.zeros_like(Hcf); H4=np.zeros_like(Hcf)
    for col,st in enumerate(states):
        for a,b,h in one:
            if abs(h)<1e-14: continue
            r=apply_ops([('c',a),('a',b)],st)
            if r: Hcf[idx[r[1]],col]+=r[0]*h
        for a,b,c,d,v in ee_terms:
            r=apply_ops([('c',a),('c',b),('a',d),('a',c)],st)
            if r:
                H2[idx[r[1]],col]+=0.5*r[0]*v[0]; H4[idx[r[1]],col]+=0.5*r[0]*v[1]
    return Hcf,H2,H4
Hcf,H2,H4=mats()
np.save if False else None
def spectrum(Dq,B,C):
    F4=441*C/35; F2=(441*B+5*F4)/9
    H=Dq*Hcf+F2*H2+F4*H4
    up=[i for i,s in enumerate(states) if so[s[0]][1]==1 and so[s[1]][1]==1]
    mz0=[i for i,s in enumerate(states) if so[s[0]][1]!=so[s[1]][1]]
    T=np.sort(np.linalg.eigvalsh(H[np.ix_(up,up)]))
    M0=np.sort(np.linalg.eigvalsh(H[np.ix_(mz0,mz0)]))
    # singlets = M0 minus T
    S=list(M0)
    for t in T:
        k=int(np.argmin([abs(x-t) for x in S])); S.pop(k)
    return T,np.array(S)
# checks: free ion d2: E(3P)-E(3F)=15B
T,S=spectrum(0,1,0)
print("free ion triplets (B=1,C=0):",np.round(T,4))
print("singlets:",np.round(S,4))
EOF