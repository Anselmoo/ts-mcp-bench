
python3 - << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
B,C=803.,3078.
F4=441*C/35; F2=49*B+7*C; F={0:0.0,2:F2,4:F4}
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    q=m1-m2
    return float(np.sqrt(4*np.pi/(2*k+1))*(-1)**m1*gaunt(2,k,2,-m1,q,m2))
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
def U(m1,m2,m3,m4):
    if m1+m2!=m3+m4: return 0.
    return sum(F[k]*CK[(k,m1,m3)]*CK[(k,m4,m2)] for k in (0,2,4))
so=[(m,s) for m in ms for s in (0,1)]
states=list(itertools.combinations(range(10),6)); idx={s:i for i,s in enumerate(states)}
N=len(states)
def ann(st,p):
    if p not in st: return None,0
    l=list(st); s=(-1)**l.index(p); l.remove(p); return l,s
def cre(l,p):
    if p in l: return None,0
    n=sum(1 for x in l if x<p); return sorted(l+[p]),(-1)**n
h1=np.zeros((10,10)); d={0:6,1:-4,-1:-4,2:1,-2:1}
for i,(m,s) in enumerate(so):
    h1[i,i]=d[m]
    for j,(m2,s2) in enumerate(so):
        if s==s2 and abs(m-m2)==4: h1[i,j]=5
H1=np.zeros((N,N)); H2=np.zeros((N,N)); Sp=np.zeros((N,N))
for i,st in enumerate(states):
    for p in st:
        a,s1=ann(st,p)
        for q in range(10):
            if h1[q,p]==0: continue
            b,s2=cre(a,q)
            if b is None: continue
            H1[idx[tuple(b)],i]+=s1*s2*h1[q,p]
        if so[p][1]==1:
            b,s2=cre(a,p-1)
            if b is not None: Sp[idx[tuple(b)],i]+=s1*s2
    for k in st:
        for l_ in st:
            if k==l_: continue
            a,s1=ann(st,k); a,s2=ann(a,l_)
            for ii in range(10):
                for jj in range(10):
                    if so[ii][1]!=so[k][1] or so[jj][1]!=so[l_][1]: continue
                    v=U(so[ii][0],so[jj][0],so[k][0],so[l_][0])
                    if v==0: continue
                    b,s3=cre(a,jj)
                    if b is None: continue
                    c,s4=cre(b,ii)
                    if c is None: continue
                    H2[idx[tuple(c)],i]+=0.5*v*s1*s2*s3*s4
Msv=np.array([sum(0.5 if so[p][1]==0 else -0.5 for p in st) for st in states])
S2=Sp.T@Sp+np.diag(Msv**2-Msv)
print(np.round(np.linalg.eigvalsh(S2)[[0,-1]],6))
E0=np.linalg.eigvalsh(H2); print("free ion lowest-gaps",np.unique(np.round(E0-E0[0],1))[:6])
def f(Dq):
    E,V=np.linalg.eigh(H2+Dq*H1+1e-4*S2)
    s=np.einsum('ij,ik,kj->j',V,S2,V)
    return min(E[np.abs(s-6)<0.1])-6e-4-min(E[np.abs(s)<0.1])
for dq in [1500,2000,2500,3000]: print(dq,f(dq))
r=brentq(f,1000,4000,xtol=1e-6); print(r, 10*r/B)
EOF
