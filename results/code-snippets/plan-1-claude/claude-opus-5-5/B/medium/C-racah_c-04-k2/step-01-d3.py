import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
# spin-orbitals: (m, s)
orbs=[(m,s) for m in range(-2,3) for s in (0.5,-0.5)]
# Coulomb integrals <ab|cd> with Slater-Condon: ck coefficients
def ck(k,l1,m1,l2,m2):
    return float((-1)**m1*np.sqrt((2*l1+1)*(2*l2+1))/(2*k+1)*0) # placeholder
from sympy.physics.wigner import wigner_3j
def c(k,m1,m2):
    l=2
    return float((-1)**m1*(2*l+1)*wigner_3j(l,k,l,0,0,0)*wigner_3j(l,k,l,-m1,m1-m2,m2))
def eri(a,b,cc,d,F):
    # <ab|1/r|cd>, a,c electron1
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=orbs[a],orbs[b],orbs[cc],orbs[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
    return sum(c(k,ma,mc)*c(k,md,mb)*F[k] for k in (0,2,4))
# cubic crystal field in real orbitals: use d-orbital matrix in m basis
def cf(Dq):
    V=np.zeros((5,5))
    for m in range(-2,3):
        V[m+2,m+2]={0:6,1:-4,-1:-4,2:1,-2:1}[m]*Dq
    V[0,4]=V[4,0]=5*Dq
    return V
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
def H(Dq,B,C):
    F={0:0,2:49*B+7*C,4:441*C/35}
    n=len(dets);Hm=np.zeros((n,n))
    V=cf(Dq)
    # one body
    for i,d in enumerate(dets):
        for p in d:
            for q in range(10):
                if orbs[p][1]!=orbs[q][1]: continue
                v=V[orbs[q][0]+2,orbs[p][0]+2]
                if v==0: continue
                if q!=p and q in d: continue
                nd=list(d); nd[nd.index(p)]=q
                sgn=np.linalg.det(np.eye(3)[np.argsort(nd)]) ; nd2=tuple(sorted(nd))
                # sign of permutation
                perm=np.argsort(nd); sgn=round(np.linalg.det(np.eye(3)[perm]))
                Hm[idx[nd2],i]+=sgn*v
        # two body
        for a,b in itertools.combinations(d,2):
            for cc in range(10):
                for dd in range(10):
                    if cc>=dd: continue
                    rest=[x for x in d if x not in (a,b)]
                    if cc in rest or dd in rest: continue
                    val=eri(cc,dd,a,b,F)-eri(cc,dd,b,a,F)
                    if val==0: continue
                    nd=list(d); nd[nd.index(a)]=cc; nd[nd.index(b)]=dd
                    perm=np.argsort(nd); sgn=round(np.linalg.det(np.eye(3)[perm]))
                    Hm[idx[tuple(sorted(nd))],i]+=sgn*val
    return Hm
def levels(Dq,B,C):
    e=np.linalg.eigvalsh(H(Dq,B,C)); e=e-e[0]
    u=[];
    for x in np.round(e,1):
        if not u or abs(x-u[-1][0])>0.5: u.append([x,1])
        else: u[-1][1]+=1
    return u
Dq=1743;B=780.7
print(levels(Dq,B,4*B)[:8])
def f(C):
    u=levels(Dq,B,C); return u[1][0]-15410 if u[1][1]==4 else None
print(levels(Dq,B,3844)[:4])
