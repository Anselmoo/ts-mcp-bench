
cd <SANDBOX_TMP> && cat << 'EOF' > d7.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
CK={}
for k in (0,2,4):
    for a in ms:
        for b in ms: CK[k,a,b]=float(gaunt(2,k,2,-a,a-b,b))*(-1)**a*np.sqrt(4*np.pi/(2*k+1))
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),7)); idx={d:i for i,d in enumerate(dets)}; N=len(dets)
def ins(lst,o):
    k=sum(1 for t in lst if t<o); lst.insert(k,o); return (-1)**k
def rem(lst,o):
    k=lst.index(o); lst.pop(k); return (-1)**k
def one(h):
    H=np.zeros((N,N))
    for I,d in enumerate(dets):
        for p in d:
            for q in range(10):
                if h[q,p]==0: continue
                l=list(d); sg=rem(l,p)
                if q in l: continue
                sg*=ins(l,q); H[idx[tuple(l)],I]+=sg*h[q,p]
    return H
def two(F):
    def V(a,b,c,d):
        (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[c],so[d]
        if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
        return sum(F[k]*CK[k,ma,mc]*CK[k,md,mb] for k in (2,4))
    H=np.zeros((N,N))
    for I,d in enumerate(dets):
        dl=list(d)
        for x in range(7):
            for y in range(x+1,7):
                p,q=dl[x],dl[y]
                for r in range(10):
                    for s in range(r+1,10):
                        val=V(r,s,p,q)-V(r,s,q,p)
                        if abs(val)<1e-12: continue
                        l=dl[:]; sg=rem(l,q)*rem(l,p)
                        if r in l or s in l: continue
                        sg*=ins(l,s)*ins(l,r)
                        H[idx[tuple(l)],I]+=sg*val
    return H
h=np.zeros((10,10)); cf={2:1,-2:1,1:-4,-1:-4,0:6}
for i,(m,s) in enumerate(so):
    h[i,i]=cf[m]
    for j,(m2,s2) in enumerate(so):
        if s==s2 and abs(m-m2)==4: h[i,j]=5
HD=one(h)
HB=two({2:49,4:0})          # B=1,C=0: F2=1,F4=0
HC=two({2:49/7,4:441/35})   # C=1: F4=1/35, F2=5/35
# S^2
SS=np.zeros((N,N))
for I,d in enumerate(dets):
    sz=sum(0.5 if so[o][1] else -0.5 for o in d); SS[I,I]+=sz*sz+sz
    for o in d:
        m,s=so[o]
        if s==0:
            t=so.index((m,1)); l=list(d); sg=rem(l,o)
            if t in l: continue
            sg*=ins(l,t)
            for o2 in l:
                m2,s2=so[o2]
                if s2==1:
                    t2=so.index((m2,0)); l2=l[:]; sg2=rem(l2,o2)
                    if t2 in l2: continue
                    sg2*=ins(l2,t2); SS[idx[tuple(l2)],I]+=sg*sg2
np.savez('mats.npz',HD=HD,HB=HB,HC=HC,SS=SS)
EOF
python d7.py && ls