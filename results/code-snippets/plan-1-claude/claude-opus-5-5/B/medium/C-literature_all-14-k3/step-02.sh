cd $(mktemp -d) && cat << 'EOF' > d7.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=range(-2,3)
orbs=[(m,s) for m in ms for s in (0.5,-0.5)]
def ck(k,m1,m2):
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,m1-m2,m2))
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
dets=list(itertools.combinations(range(10),7)); idx={d:i for i,d in enumerate(dets)}; N=len(dets)
def g(a,b,c,d,F):
    if a+b!=c+d: return 0
    return sum(F[k]*CK[(k,a,c)]*CK[(k,d,b)] for k in (0,2,4))
def build(F,V):
    Hm=np.zeros((N,N))
    for i,D in enumerate(dets):
        for p in D:
            for q in range(10):
                if orbs[p][1]!=orbs[q][1]: continue
                v=V[orbs[q][0]+2,orbs[p][0]+2]
                if v==0 or (q!=p and q in D): continue
                rem=[x for x in D if x!=p]
                s=(-1)**D.index(p)*(-1)**sum(1 for x in rem if x<q)
                Hm[idx[tuple(sorted(rem+[q]))],i]+=s*v
        for a_,b_ in itertools.combinations(D,2):
            rem=[x for x in D if x not in (a_,b_)]
            s1=(-1)**D.index(a_)*(-1)**([x for x in D if x!=a_].index(b_))
            for c_ in range(10):
                for d_ in range(10):
                    if c_==d_ or c_ in rem or d_ in rem: continue
                    oa,ob,oc,od=orbs[a_],orbs[b_],orbs[c_],orbs[d_]
                    val=0
                    if oa[1]==oc[1] and ob[1]==od[1]: val+=g(oc[0],od[0],oa[0],ob[0],F)
                    if oa[1]==od[1] and ob[1]==oc[1]: val-=g(oc[0],od[0],ob[0],oa[0],F)
                    if val==0: continue
                    r2=sorted(rem+[d_]); s2=(-1)**sum(1 for x in rem if x<d_)
                    s3=(-1)**sum(1 for x in r2 if x<c_)
                    Hm[idx[tuple(sorted(r2+[c_]))],i]+=0.5*val*s1*s2*s3
    return Hm
Z=np.zeros((5,5))
H2=build({0:0,2:1,4:0},Z); H4=build({0:0,2:0,4:1},Z)
V=np.zeros((5,5)); d={-2:1,-1:-4,0:6,1:-4,2:1}
for m in ms: V[m+2,m+2]=d[m]
V[0,4]=V[4,0]=5
HD=build({0:0,2:0,4:0},V)
# S^2
Sz=np.diag([sum(orbs[p][1] for p in D) for D in dets])
Sp=np.zeros((N,N))
for i,D in enumerate(dets):
    for p in D:
        m,s=orbs[p]
        if s==-0.5:
            q=orbs.index((m,0.5))
            if q in D: continue
            rem=[x for x in D if x!=p]
            sg=(-1)**D.index(p)*(-1)**sum(1 for x in rem if x<q)
            Sp[idx[tuple(sorted(rem+[q]))],i]+=sg
S2=Sp.T@Sp+Sz@Sz+Sz
np.savez('mats.npz',H2=H2,H4=H4,HD=HD,S2=S2)
EOF
python d7.py && cat << 'EOF' > fit.py
import numpy as np
from scipy.optimize import least_squares
M=np.load('mats.npz')
def lev(Dq,B,C):
    F4=C/35; F2=B+5*F4
    H=49*F2*M['H2']+441*F4*M['H4']+Dq*M['HD']
    w,v=np.linalg.eigh(H)
    S=np.einsum('ij,jk,ki->i',v.T,M['S2'],v)
    # group
    out=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and abs(w[j]-w[i])<1e-3: j+=1
        out.append((w[i],j-i,round(S[i:j].mean(),2))); i=j
    return out
def assign(Dq,B,C):
    L=lev(Dq,B,C); E0=L[0][0]
    q=[(e-E0,n) for e,n,s in L if abs(s-3.75)<0.1]
    dbl=[(e-E0,n) for e,n,s in L if abs(s-0.75)<0.1]
    qT1=[e for e,n in q if n==12]; qT2=[e for e,n in q if n==12]
    return L,q,dbl
L,q,dbl=assign(900,1000,4000)
print(q); print(dbl[:8])
EOF
python fit.py