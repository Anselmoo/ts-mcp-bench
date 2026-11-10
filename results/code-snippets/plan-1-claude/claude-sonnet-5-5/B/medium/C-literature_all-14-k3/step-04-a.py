import numpy as np, itertools
from sympy.physics.wigner import gaunt
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]
def c(k,m1,m2):
    return float(np.sqrt(4*np.pi/(2*k+1))*(-1)**m1*gaunt(2,k,2,-m1,m1-m2,m2))
C2={(a,b,k):c(k,orbs[a][0],orbs[b][0]) for a in range(10) for b in range(10) for k in (2,4)}
states=[s for s in itertools.combinations(range(10),7) if sum(1 if o%2==0 else -1 for o in s)==1]
idx={s:i for i,s in enumerate(states)}
n=len(states);print(n)
def ap(op,st,dag):
    if dag:
        if op in st: return None
        pos=sum(1 for x in st if x<op); return tuple(sorted(st+(op,))),(-1)**pos
    if op not in st: return None
    pos=st.index(op); return tuple(x for x in st if x!=op),(-1)**pos
def one(i,j):
    M=np.zeros((n,n))
    for st in states:
        r=ap(j,st,False)
        if r is None: continue
        s2,p=r; r=ap(i,s2,True)
        if r is None: continue
        M[idx[r[0]],idx[st]]+=p*r[1]
    return M
hd=np.zeros((n,n))
for m,v in {2:1,-2:1,1:-4,-1:-4,0:6}.items():
    for s in (0,1):
        i=2*(m+2)+s; hd+=v*one(i,i)
for s in (0,1): hd+=5*(one(8+s,s)+one(s,8+s))
def two(k):
    M=np.zeros((n,n))
    for a in range(10):
     for b in range(10):
      for cc in range(10):
       for d in range(10):
        (m1,s1),(m2,s2),(m3,s3),(m4,s4)=orbs[a],orbs[b],orbs[cc],orbs[d]
        if not(s1==s3 and s2==s4 and m1+m2==m3+m4 and a!=b and cc!=d): continue
        v=C2[(a,cc,k)]*C2[(d,b,k)]
        if abs(v)<1e-14: continue
        for st in states:
            x=ap(cc,st,False)
            if not x: continue
            s1_,p1=x; x=ap(d,s1_,False)
            if not x: continue
            x2,p2=x; x=ap(b,x2,True)
            if not x: continue
            x3,p3=x; x=ap(a,x3,True)
            if not x: continue
            M[idx[x[0]],idx[st]]+=0.5*v*p1*p2*p3*x[1]
    return M
T2=two(2);T4=two(4)
Sp=sum(one(2*m,2*m+1) for m in range(5))
# S+ raises Sz: but Sz=1/2 subspace -> use Sz-conserving S2 via full? use Sp not in subspace; instead classify by energy degeneracy
np.savez('m.npz',hd=hd,T2=T2,T4=T4)
