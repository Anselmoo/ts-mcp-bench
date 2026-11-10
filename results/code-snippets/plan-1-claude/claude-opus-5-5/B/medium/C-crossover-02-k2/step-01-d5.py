import numpy as np, itertools
from sympy.physics.wigner import gaunt
B,C=621.,2851.
F4=C*441/35; F2=49*(B+5*F4/441)
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):  # c^k(l m1, l m2)
    return float(gaunt(2,k,2,-m1,m1-m2,m2))*(-1)**m1*np.sqrt(4*np.pi/(2*k+1))*5
def R(m1,m2,m3,m4): # <m1 m2|1/r|m3 m4>, m1+m2=m3+m4
    if m1+m2!=m3+m4: return 0
    s=0
    for k,F in [(2,F2),(4,F4)]:
        s+=ck(k,m1,m3)*ck(k,m4,m2)*F/ (25)
    return s
so=[(m,s) for m in ms for s in (0,1)]
states=list(itertools.combinations(range(10),5))
idx={s:i for i,s in enumerate(states)}
def Hint():
    H=np.zeros((252,252))
    for st in states:
        i=idx[st]
        for a,b in itertools.combinations(range(5),2):
            p,q=st[a],st[b]
            for r,s_ in itertools.permutations(range(10),2):
                if r>s_: continue
                rest=[x for x in st if x not in (p,q)]
                if r in rest or s_ in rest: continue
                (m1,s1),(m2,s2)=so[p],so[q];(m3,s3),(m4,s4)=so[r],so[s_]
                v=0
                if s1==s3 and s2==s4: v+=R(m1,m2,m3,m4)
                if s1==s4 and s2==s3: v-=R(m1,m2,m4,m3)
                if v==0: continue
                # sign: annihilate q,p create s_,r : a_r^+ a_s^+ a_q a_p
                lst=list(st); sign=1
                def ann(l,x):
                    k=l.index(x); return (-1)**k, l[:k]+l[k+1:]
                def cre(l,x):
                    k=sum(1 for y in l if y<x); return (-1)**k, sorted(l+[x])
                s1_,lst=ann(lst,p); s2_,lst=ann(lst,q); s3_,lst=cre(lst,s_); s4_,lst=cre(lst,r)
                j=idx[tuple(lst)]
                H[j,i]+=v*s1_*s2_*s3_*s4_
    return H
HI=Hint()
V1=np.zeros((5,5))
for i,m in enumerate(ms):
    V1[i,i]={0:6,1:-4,-1:-4,2:1,-2:1}[m]
V1[0,4]=V1[4,0]=5
def onebody(M):
    H=np.zeros((252,252))
    for st in states:
        i=idx[st]
        for p in st:
            for r in range(10):
                if so[p][1]!=so[r][1]: continue
                v=M[ms.index(so[r][0]),ms.index(so[p][0])]
                if v==0: continue
                rest=[x for x in st if x!=p]
                if r in rest: continue
                k=st.index(p); s1=(-1)**k
                new=sorted(rest+[r]); s2=(-1)**new.index(r)
                H[idx[tuple(new)],i]+=v*s1*s2
    return H
HV=onebody(V1)
print(np.allclose(HI,HI.T), np.allclose(HV,HV.T))
# Sz
Sz=np.array([sum(0.5 if so[x][1] else -0.5 for x in st) for st in states])
def gap(Dq):
    sel=np.abs(Sz-0.5)<1e-9
    H=(HI+Dq*HV)[np.ix_(sel,sel)]
    w,v=np.linalg.eigh(H)
    # sextet energy: state Sz=5/2
    sel6=np.abs(Sz-2.5)<1e-9
    w6=np.linalg.eigvalsh((HI+Dq*HV)[np.ix_(sel6,sel6)])[0]
    # lowest non-sextet: sorted eigen of Sz=1/2 sector, sextet one removed
    ws=[x for x in w if abs(x-w6)>1e-6]
    return w6, min(ws)
from scipy.optimize import brentq
f=lambda d: gap(d)[0]-gap(d)[1]
for d in [2000,2500,3000]: print(d,f(d))
print(brentq(f,1500,4000,xtol=1e-6), 0.75*B+0.5*C)
