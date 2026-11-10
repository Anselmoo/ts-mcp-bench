
python3 - << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
B,C=621.,2851.
F4=C*441/35; F2=49*(B+5*F4/441)
ms=[-2,-1,0,1,2]
from functools import lru_cache
@lru_cache(None)
def ck(k,m1,m2):
    return float(gaunt(2,k,2,-m1,m1-m2,m2))*(-1)**m1*np.sqrt(4*np.pi/(2*k+1))*5
def R(m1,m2,m3,m4):
    if m1+m2!=m3+m4: return 0
    return sum(ck(k,m1,m3)*ck(k,m4,m2)*F/25 for k,F in [(2,F2),(4,F4)])
so=[(m,s) for m in ms for s in (0,1)]
states=list(itertools.combinations(range(10),5))
idx={s:i for i,s in enumerate(states)}
def ann(l,x):
    k=l.index(x); return (-1)**k, l[:k]+l[k+1:]
def cre(l,x):
    k=sum(1 for y in l if y<x); return (-1)**k, sorted(l+[x])
HI=np.zeros((252,252))
for st in states:
    i=idx[st]
    for a,b in itertools.combinations(range(5),2):
        p,q=st[a],st[b]
        rest=[x for x in st if x not in (p,q)]
        for r,s_ in itertools.combinations(range(10),2):
            if r in rest or s_ in rest: continue
            (m1,s1),(m2,s2)=so[p],so[q];(m3,s3),(m4,s4)=so[r],so[s_]
            v=0
            if s1==s3 and s2==s4: v+=R(m1,m2,m3,m4)
            if s1==s4 and s2==s3: v-=R(m1,m2,m4,m3)
            if v==0: continue
            lst=list(st)
            a1,lst=ann(lst,p); a2,lst=ann(lst,q); a3,lst=cre(lst,s_); a4,lst=cre(lst,r)
            HI[idx[tuple(lst)],i]+=v*a1*a2*a3*a4
V1=np.zeros((5,5))
for i,m in enumerate(ms): V1[i,i]={0:6,1:-4,-1:-4,2:1,-2:1}[m]
V1[0,4]=V1[4,0]=5
HV=np.zeros((252,252))
for st in states:
    i=idx[st]
    for p in st:
        for r in range(10):
            if so[p][1]!=so[r][1]: continue
            v=V1[ms.index(so[r][0]),ms.index(so[p][0])]
            if v==0: continue
            rest=[x for x in st if x!=p]
            if r in rest: continue
            s1=(-1)**st.index(p); new=sorted(rest+[r]); s2=(-1)**new.index(r)
            HV[idx[tuple(new)],i]+=v*s1*s2
print(np.allclose(HI,HI.T), np.allclose(HV,HV.T))
w=np.linalg.eigvalsh(HI); w-=w[0]; print(np.round(np.unique(np.round(w,3))[:6],1), 10*B+5*C)
Sz=np.array([sum(0.5 if so[x][1] else -0.5 for x in st) for st in states])
sel=np.abs(Sz-0.5)<1e-9; sel6=np.abs(Sz-2.5)<1e-9
def f(Dq):
    H=HI+Dq*HV
    w6=np.linalg.eigvalsh(H[np.ix_(sel6,sel6)])[0]
    w=np.linalg.eigvalsh(H[np.ix_(sel,sel)])
    ws=[x for x in w if abs(x-w6)>1e-6]
    return w6-min(ws)
from scipy.optimize import brentq
for d in [1500,2000,2500,3000]: print(d,f(d))
print(brentq(f,1000,4000,xtol=1e-6), 0.75*B+0.5*C)
EOF
