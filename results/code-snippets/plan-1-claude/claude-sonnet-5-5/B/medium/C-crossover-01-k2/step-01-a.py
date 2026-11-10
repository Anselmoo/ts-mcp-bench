import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
B,C=706.,2734.
F={0:0,2:B+C/7,4:C/35}
def ck(k,l,m,lp,mp):
    # <l m|C^k_q|l' m'> with q=m-m'
    from sympy import sqrt
    return float(((-1)**m*(2*l+1)*gaunt(l,k,l,-m,m-mp,mp)).evalf()) if abs(m-mp)<=k else 0.
# use c^k(m,m')=sqrt(2l+1)... standard: c^k(lm,l'm')=sqrt((2l+1)(2l'+1))(-1)^m 3j... use gaunt
def c(k,m,mp):
    if abs(m-mp)>k: return 0.
    return float((-1)**m*5*gaunt(2,k,2,-m,m-mp,mp))
ms=range(-2,3)
orb=[(m,s) for m in ms for s in (0,1)]
def V(a,b,cc,d):  # <ab|1/r|cd> Coulomb
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=a,b,cc,d
    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: return 0.
    t=0
    for k in (0,2,4):
        Fk=F[k] if k else 0
        t+=0
    return None
# F0 irrelevant (constant for fixed N)
def Vv(a,b,cc,d):
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=a,b,cc,d
    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: return 0.
    t=0
    for k in (2,4):
        t+=F[k]*c(k,m1,m3)*c(k,m4,m2)
    return t
# Landau: <ab|cd> = sum F^k c^k(l m1,l m3) c^k(l m4,l m2)
cache={}
def build(Dq,Ms2):
    n=2*5
    dets=[d for d in itertools.combinations(range(10),4) if sum(1 if orb[i][1]==0 else -1 for i in d)==Ms2]
    idx={d:i for i,d in enumerate(dets)}
    N=len(dets);H=np.zeros((N,N))
    # one-body: cubic field in m basis: real d: eg=dz2,dx2-y2 ; Dq*( 6 eg -4 t2)
    # V4 matrix: diag m=0: 6Dq*... use: m=0:+6Dq, ±1:-4Dq, ±2: m=±2 mix: (1/2)(eg+t2)=Dq, offdiag m=2,-2: 5Dq
    h=np.zeros((10,10))
    for i,(m,s) in enumerate(orb):
        for j,(mp,sp) in enumerate(orb):
            if s!=sp: continue
            if m==mp: h[i,j]=6*Dq if m==0 else (-4*Dq if abs(m)==1 else Dq)
            elif abs(m)==2 and mp==-m: h[i,j]=5*Dq
    for d in dets:
        for e in dets:
            pass
    return dets,idx,h
def apply_ops(dets,idx,h,Dq):
    N=len(dets);H=np.zeros((N,N))
    for d in dets:
        i=idx[d]
        # one-body
        for p in range(10):
            for q in range(10):
                if h[p,q]==0 or q not in d: continue
                l=list(d);pos=l.index(q);rest=[x for x in l if x!=q]
                if p in rest: continue
                sg=(-1)**pos
                new=rest+[p]; 
                # insert p: sort with sign
                nl=sorted(new); 
                perm=sum(1 for a in range(len(new)) for b in range(a+1,len(new)) if new[a]>new[b])
                H[idx[tuple(nl)],i]+=h[p,q]*sg*(-1)**perm if tuple(nl) in idx else 0
        # two-body 1/2 sum V(pq|rs) a†p a†q a_s a_r
        for r in d:
            for s in d:
                if r==s: continue
                for p in range(10):
                    for q in range(10):
                        if p==q: continue
                        v=Vv(orb[p],orb[q],orb[r],orb[s])
                        if v==0: continue
                        l=list(d)
                        # apply a_s then a_r : a†p a†q a_s a_r |d>
                        sign=1
                        def ann(l,x):
                            pos=l.index(x);return [y for y in l if y!=x],(-1)**pos
                        l,s1=ann(l,r)
                        if s not in l: continue
                        l,s2=ann(l,s)
                        def cre(l,x):
                            if x in l: return None,0
                            nl=[x]+l;sg=1
                            nl2=sorted(nl);perm=sum(1 for a in range(len(nl)) for b in range(a+1,len(nl)) if nl[a]>nl[b])
                            return nl2,(-1)**perm
                        l2,s3=cre(l,q)
                        if l2 is None: continue
                        l3,s4=cre(l2,p)
                        if l3 is None: continue
                        H[idx[tuple(l3)],i]+=0.5*v*s1*s2*s3*s4
    return H
def gs(Dq,Ms2):
    dets,idx,h=build(Dq,Ms2)
    H=apply_ops(dets,idx,h,Dq)
    assert np.allclose(H,H.T,atol=1e-6)
    return np.linalg.eigvalsh(H)[0]
f=lambda Dq:gs(Dq,4)-gs(Dq,2)
for D in (1000,2000,2500,3000):print(D,f(D))
print(brentq(f,500,4000))
