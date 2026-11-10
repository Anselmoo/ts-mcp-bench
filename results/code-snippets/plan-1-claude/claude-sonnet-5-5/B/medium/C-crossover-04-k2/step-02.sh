
mkdir -p /tmp/w && cd /tmp/w && cat > a.py <<'E'
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
def g(a,b,cc,d): # <ab|g|cd> spin-orbitals
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=orb[a],orb[b],orb[cc],orb[d]
    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: return 0
    return sum(Fk[k]*c(k,m1,m3)*c(k,m4,m2) for k in (2,4))
G=np.zeros((n,)*4)
for a,b,cc,d in itertools.product(range(n),repeat=4): G[a,b,cc,d]=g(a,b,cc,d)
states=[s for s in itertools.combinations(range(n),7) if sum(orb[i][1] for i in s)==1]  # Ms=1/2
si={s:i for i,s in enumerate(states)}
def apply(ops,s): # ops list of (idx,create?) applied right to left
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
for j,s in enumerate(states):
    for a,b,cc,d in itertools.product(range(n),repeat=4):
        v=G[a,b,cc,d]
        if v==0: continue
        # 1/2 sum <ab|g|cd> a†a† b ... : a†_a a†_b a_d a_c
        t,sg=apply([(a,1),(b,1),(d,0),(cc,0)],s)
        if t is not None: H2[si[t],j]+=0.5*v*sg
# one-body Dq unit matrix
h=np.zeros((n,n))
d={2:1,1:-4,0:6,-1:-4,-2:1}
for i,(m,s) in enumerate(orb):
    h[i,i]=d[m]
    for j,(m2,s2) in enumerate(orb):
        if s==s2 and abs(m)==2 and m!=m2 and abs(m2)==2: h[i,j]=5
H1=np.zeros((N,N))
for j,s in enumerate(states):
    for a in range(n):
        for b in range(n):
            if h[a,b]:
                t,sg=apply([(a,1),(b,0)],s)
                if t is not None: H1[si[t],j]+=h[a,b]*sg
# S^2 via total: use spin-sector: S^2 = Sz^2+Sz+S-S+ ; build S-S+... simpler: classify by degeneracy via H eigen + S2
Sp=np.zeros((N,N))  # need Ms=3/2 states; skip: classify using S2 computed with pair operator
# S2 = Sz(Sz+1) + S- S+ ; S- S+ = sum_{ij} a†_{i dn} a_{i up} a†_{j up} a_{j dn}
S2=np.zeros((N,N))
for j,s in enumerate(states):
    S2[j,j]+=0.75
    for p in range(-2,3):
        for q in range(-2,3):
            u=orb.index((p,1));dn=orb.index((p,-1));u2=orb.index((q,1));d2=orb.index((q,-1))
            t,sg=apply([(dn,1),(u,0),(u2,1),(d2,0)],s)
            if t is not None: S2[si[t],j]+=sg
def gs(Dq):
    H=H2+Dq*H1
    w,v=np.linalg.eigh(H)
    out={}
    for i in range(len(w)):
        s2=v[:,i]@S2@v[:,i]
        key='q' if abs(s2-3.75)<.1 else 'd' if abs(s2-.75)<.1 else 'x'
        if key not in out: out[key]=w[i]
        if 'q' in out and 'd' in out: break
    return out
f=lambda D:(lambda o:o['q']-o['d'])(gs(D))
for D in (500,1000,1500,2000,2500): print(D,f(D))
print(brentq(f,500,3000,xtol=1e-4))
E
python3 a.py