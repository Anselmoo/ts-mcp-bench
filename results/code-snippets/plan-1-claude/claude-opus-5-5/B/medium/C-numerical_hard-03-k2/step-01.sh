
cat << 'EOF' > /tmp/d5.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
# ck coefficients
def ck(k,m1,m2): # c^k(l m1, l m2)
    return float(gaunt(2,k,2,-m1,m1-m2,m2))*(-1)**m1*np.sqrt(4*np.pi/(2*k+1))
orbs=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),5))
idx={d:i for i,d in enumerate(dets)}
def two(a,b,c,d,F): # <ab|1/r|cd>
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=orbs[a],orbs[b],orbs[c],orbs[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
    return sum(F[k]*ck(k,ma,mc)*ck(k,md,mb) for k in (0,2,4) if abs(ma-mc)<=k)
def build(Dq,B,C):
    F4=C/35; F2=B+5*F4; F={0:0,2:F2*49,4:F4*441}
    h=np.zeros((10,10))
    for i,(m,s) in enumerate(orbs):
        h[i,i]={0:6,1:-4,-1:-4,2:1,-2:1}[m]*Dq
        for j,(m2,s2) in enumerate(orbs):
            if s==s2 and abs(m-m2)==4: h[i,j]=5*Dq
    N=len(dets);H=np.zeros((N,N))
    for I,d in enumerate(dets):
        for J,e in enumerate(dets):
            ds=set(d)-set(e); es=set(e)-set(d)
            if len(ds)>2: continue
            def sgn(lst,removed):
                # sign to move removed to front in order
                s=1;l=list(lst)
                out=[]
                for k,r in enumerate(removed):
                    p=l.index(r); s*=(-1)**p; l.pop(p)
                return s,l
            if len(ds)==0:
                v=sum(h[a,a] for a in d)
                for a,b in itertools.combinations(d,2):
                    v+=two(a,b,a,b,F)-two(a,b,b,a,F)
            elif len(ds)==1:
                a=list(ds)[0];c=list(es)[0]
                s1,r1=sgn(d,[a]);s2,r2=sgn(e,[c])
                v=h[a,c]+sum(two(a,b,c,b,F)-two(a,b,b,c,F) for b in r1)
                v*=s1*s2
            else:
                a,b=sorted(ds);c,dd=sorted(es)
                s1,_=sgn(d,[a,b]);s2,_=sgn(e,[c,dd])
                v=s1*s2*(two(a,b,c,dd,F)-two(a,b,dd,c,F))
            H[I,J]=v
    return H
# S^2
N=len(dets);S2=np.zeros((N,N))
def apply_Sminus_plus(): pass
# compute S^2 via S-S+ + Sz^2+Sz
def Sop(d,up):
    res={}
    for k,o in enumerate(d):
        m,s=orbs[o]
        if (up and s==0) or (not up and s==1):
            n=orbs.index((m,1-s))
            if n in d: continue
            l=list(d);l[k]=n
            perm=np.argsort(l);sign=np.linalg.det(np.eye(5)[perm])
            t=tuple(sorted(l));res[t]=res.get(t,0)+round(sign)
    return res
for I,d in enumerate(dets):
    sz=sum(0.5 if orbs[o][1]==1 else -0.5 for o in d)
    S2[I,I]+=sz*sz+sz
    for t,c in Sop(d,True).items():
        for t2,c2 in Sop(t,False).items():
            S2[idx[t2],I]+=c*c2
def levels(Dq,B,C):
    H=build(Dq,B,C);H2=H+1e-3*S2  # tiny shift to label
    w,v=np.linalg.eigh(H)
    s=np.einsum('ij,jk,ki->i',v.T,S2,v)
    return w,s
import sys
EOF
cat << 'EOF' > /tmp/run.py
exec(open('/tmp/d5.py').read())
def doublets(Dq,B):
    w,s=levels(Dq,B,4.6*B)
    # group degenerate levels
    out=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and abs(w[j]-w[i])<1e-3: j+=1
        S=s[i]; out.append((w[i],j-i,round(S,2))); i=j
    return out
lv=doublets(2500,600)
print(lv[:10])
EOF
python3 /tmp/run.py
