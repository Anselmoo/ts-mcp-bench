
mkdir -p ~/w && cd ~/w && cat > a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]
def c(k,m1,m2):
    return float(np.sqrt(4*np.pi/(2*k+1))*(-1)**m1*gaunt(2,k,2,-m1,m1-m2,m2))
C2={(a,b,k):c(k,orbs[a][0],orbs[b][0]) for a in range(10) for b in range(10) for k in (2,4)}
states=list(itertools.combinations(range(10),7)); idx={s:i for i,s in enumerate(states)}
def ap(op,st,dag):
    # apply a or a† to occupied tuple
    if dag:
        if op in st: return None
        pos=sum(1 for x in st if x<op); new=tuple(sorted(st+(op,)))
    else:
        if op not in st: return None
        pos=st.index(op); new=tuple(x for x in st if x!=op)
    return new,(-1)**pos
quads=[]
for a in range(10):
 for b in range(10):
  for cc in range(10):
   for d in range(10):
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=orbs[a],orbs[b],orbs[cc],orbs[d]
    if s1==s3 and s2==s4 and m1+m2==m3+m4 and a!=b and cc!=d:
        quads.append((a,b,cc,d))
def mats():
    n=len(states)
    H1=[np.zeros((n,n)) for _ in range(2)]
    # one-body ops
    def one(i,j):
        M=np.zeros((n,n))
        for st in states:
            r=ap(j,st,False)
            if r is None: continue
            s2,p=r; r=ap(i,s2,True)
            if r is None: continue
            s3,q=r; M[idx[s3],idx[st]]+=p*q
        return M
    hd=np.zeros((n,n))
    cf={2:1,-2:1,1:-4,-1:-4,0:6}
    for m,v in cf.items():
        for s in (0,1):
            i=2*(m+2)+s; hd+=v*one(i,i)
    for s in (0,1):
        hd+=5*(one(8+s,0+s)+one(0+s,8+s))
    # two-body, split into F2 and F4 parts
    def two(k):
        M=np.zeros((n,n))
        for (a,b,cc,d) in quads:
            v=C2[(a,cc,k)]*C2[(d,b,k)]
            if abs(v)<1e-14: continue
            # 1/2 a†a a†b ad ac  : <ab|cd> a†_a a†_b a_d a_c
            for st in states:
                x=ap(cc,st,False)
                if not x: continue
                s1,p1=x; x=ap(d,s1,False)
                if not x: continue
                s2,p2=x; x=ap(b,s2,True)
                if not x: continue
                s3,p3=x; x=ap(a,s3,True)
                if not x: continue
                s4,p4=x
                M[idx[s4],idx[st]]+=0.5*v*p1*p2*p3*p4
        return M
    # S^2
    Sz=sum(0.5*(1 if o[1]==0 else -1)*0 for o in orbs)
    Sp=sum(one(2*m+0,2*m+1) for m in range(5)); Sm=Sp.T
    Szm=np.diag([sum(0.5 if o%2==0 else -0.5 for o in st) for st in states])
    S2=Sm@Sp+Szm@Szm+Szm
    return hd,two(2),two(4),S2,Szm
hd,T2,T4,S2,Szm=mats()
np.savez('m.npz',hd=hd,T2=T2,T4=T4,S2=S2,Szm=Szm)
E
python3 a.py && echo done