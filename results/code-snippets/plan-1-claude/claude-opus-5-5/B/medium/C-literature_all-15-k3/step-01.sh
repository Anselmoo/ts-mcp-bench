
cat << 'EOF' > /tmp/d7.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
def ck(k,l1,m1,l2,m2): # c^k(l m1, l m2)
    return float(gaunt(2,k,2,-m1,m1-m2,m2))*(-1)**m1*np.sqrt(4*np.pi/(2*k+1))
CK={}
for k in (0,2,4):
    for a in ms:
        for b in ms: CK[k,a,b]=ck(k,2,a,2,b)
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),7))
idx={d:i for i,d in enumerate(dets)}
def V(a,b,c,d,F): # <ab|1/r|cd>
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[c],so[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
    return sum(F[k]*CK[k,ma,mc]*CK[k,md,mb] for k in (0,2,4))
def build(Dq,B,C):
    F4=C/35; F2=B+5*F4
    F={0:0,2:49*F2,4:441*F4}
    h=np.zeros((10,10))
    cf={2:Dq,-2:Dq,1:-4*Dq,-1:-4*Dq,0:6*Dq}
    for i,(m,s) in enumerate(so):
        h[i,i]=cf[m]
        for j,(m2,s2) in enumerate(so):
            if s==s2 and abs(m-m2)==4: h[i,j]=5*Dq
    N=len(dets);H=np.zeros((N,N))
    # two-body via second quantization
    from collections import defaultdict
    for I,d in enumerate(dets):
        occ=set(d)
        for p in d:
            for q in range(10):
                if h[q,p]==0: continue
                if q!=p and q in occ: continue
                new=sorted((occ-{p})|{q}); sign=(-1)**(sorted(occ).index(p)+new.index(q))
                H[idx[tuple(new)],I]+=sign*h[q,p]
        dl=list(d)
        for x in range(7):
            for y in range(x+1,7):
                p,q=dl[x],dl[y]
                rest=[o for o in dl if o not in (p,q)]
                for r in range(10):
                    for s in range(r+1,10):
                        if (r in rest) or (s in rest): continue
                        val=V(r,s,p,q,F)-V(r,s,q,p,F)
                        if val==0: continue
                        # annihilate q,p then create s,r: sign
                        lst=dl[:]; sg=1
                        for o in (q,p):
                            k=lst.index(o); sg*=(-1)**k; lst.pop(k)
                        for o in (s,r):
                            k=sum(1 for t in lst if t<o); sg*=(-1)**k; lst.insert(k,o)
                        H[idx[tuple(lst)],I]+=sg*val
    return H
# S^2
def S2():
    N=len(dets);M=np.zeros((N,N))
    for I,d in enumerate(dets):
        occ=set(d); sz=sum(0.5 if so[o][1] else -0.5 for o in d)
        M[I,I]+=sz*sz-sz
        # S+S-: actually use S^2=S-S+ + Sz^2 + Sz
        pass
    for I,d in enumerate(dets):
        occ=set(d)
        sz=sum(0.5 if so[o][1] else -0.5 for o in d)
        M[I,I]+=sz  # S^2 = S-S+ + Sz^2+Sz ; fix diag
    M=np.zeros((N,N))
    def Sp(vecdict):
        out={}
        for d,c in vecdict.items():
            for o in d:
                m,s=so[o]
                if s==0:
                    t=so.index((m,1))
                    if t in d: continue
                    occ=sorted(d); k=occ.index(o); occ.pop(k); sg=(-1)**k
                    k2=sum(1 for u in occ if u<t); sg*=(-1)**k2; occ.insert(k2,t)
                    out[tuple(occ)]=out.get(tuple(occ),0)+sg*c
        return out
    def Sm(vecdict):
        out={}
        for d,c in vecdict.items():
            for o in d:
                m,s=so[o]
                if s==1:
                    t=so.index((m,0))
                    if t in d: continue
                    occ=sorted(d); k=occ.index(o); occ.pop(k); sg=(-1)**k
                    k2=sum(1 for u in occ if u<t); sg*=(-1)**k2; occ.insert(k2,t)
                    out[tuple(occ)]=out.get(tuple(occ),0)+sg*c
        return out
    for I,d in enumerate(dets):
        sz=sum(0.5 if so[o][1] else -0.5 for o in d)
        M[I,I]+=sz*sz+sz
        for d2,c in Sm(Sp({d:1})).items(): M[idx[d2],I]+=c
    return M
SS=S2()
EOF
echo ok