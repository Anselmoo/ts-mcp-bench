import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import brentq
B=922.;C=4156.
F4=C/35;F2=B+5*F4
Fk={2:49*F2,4:441*F4}
def c(k,m1,m3):
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m3,m3))
orb=[(m,s) for m in range(-2,3) for s in (1,-1)]
n=10
def g(a,b,cc,d):
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=orb[a],orb[b],orb[cc],orb[d]
    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: return 0
    return sum(Fk[k]*c(k,m1,m3)*c(k,m4,m2) for k in (2,4))
G=np.zeros((n,)*4)
for a,b,cc,d in itertools.product(range(n),repeat=4): G[a,b,cc,d]=g(a,b,cc,d)
states=[s for s in itertools.combinations(range(n),7) if sum(orb[i][1] for i in s)==1]
si={s:i for i,s in enumerate(states)}
def apply(ops,s):
    s=list(s);sign=1
    for o,cr in reversed(ops):
        if cr:
            if o in s: return None,0
            pos=sum(1 for x in s if x<o); sign*=(-1)**pos; s.insert(pos,o)
        else:
            if o not in s: return None,0
            pos=s.index(o); sign*=(-1)**pos; s.pop(pos)
    return tuple(s),sign
N=len(states)
H2=np.zeros((N,N))
nz=[(a,b,cc,d,G[a,b,cc,d]) for a,b,cc,d in itertools.product(range(n),repeat=4) if G[a,b,cc,d]!=0]
for j,s in enumerate(states):
    for a,b,cc,d,v in nz:
        t,sg=apply([(a,1),(b,1),(d,0),(cc,0)],s)
        if t is not None: H2[si[t],j]+=0.5*v*sg
h=np.zeros((n,n))
dd={2:1,1:-4,0:6,-1:-4,-2:1}
for i,(m,s) in enumerate(orb):
    h[i,i]=dd[m]
    for j,(m2,s2) in enumerate(orb):
        if s==s2 and abs(m)==2 and m!=m2 and abs(m2)==2: h[i,j]=5
H1=np.zeros((N,N))
for j,s in enumerate(states):
    for a in range(n):
        for b in range(n):
            if h[a,b]:
                t,sg=apply([(a,1),(b,0)],s)
                if t is not None: H1[si[t],j]+=h[a,b]*sg
S2=np.zeros((N,N))
for j,s in enumerate(states):
    S2[j,j]+=0.75
    for p in range(-2,3):
        for q in range(-2,3):
            u=orb.index((p,1));dn=orb.index((p,-1));u2=orb.index((q,1));d2=orb.index((q,-1))
            t,sg=apply([(dn,1),(u,0),(u2,1),(d2,0)],s)
            if t is not None: S2[si[t],j]+=sg
def gs(Dq):
    w,v=np.linalg.eigh(H2+Dq*H1)
    out={}
    for i in range(len(w)):
        s2=v[:,i]@S2@v[:,i]
        key='q' if abs(s2-3.75)<.1 else 'd' if abs(s2-.75)<.1 else 'x'
        out.setdefault(key,w[i])
    return out
f=lambda D:(lambda o:o['q']-o['d'])(gs(D))
for D in (500,1000,1500,2000,2500): print(D,f(D))
print(brentq(f,500,3000,xtol=1e-4))
