cat << 'EOF' > /tmp/d3.py
import itertools, numpy as np
from sympy.physics.wigner import gaunt
from sympy import N
# spin-orbitals: (m, s) m in -2..2, s=+1 (up) / -1 (down)
so=[(m,s) for m in range(-2,3) for s in (1,-1)]
idx={x:i for i,x in enumerate(so)}
def ang(k,a,b,c,d):
    # <a b|Y_k(1,2)|c d> angular factor (no radial), a,b,c,d are orbital m values (l=2)
    tot=0.0
    for q in range(-k,k+1):
        g1=complex(N(gaunt(2,k,2,-a,q,c)))*(-1)**a
        g2=complex(N(gaunt(2,k,2,-b,-q,d)))*(-1)**b
        tot+= (-1)**q * g1*g2
    return tot*4*np.pi/(2*k+1)
def Vint(F):  # F dict k->F^k ; returns function <ab|V|cd> over orbital m
    cache={}
    def f(a,b,c,d):
        key=(a,b,c,d)
        if key in cache: return cache[key]
        v=0.0
        for k in (0,2,4):
            v+=F[k]*ang(k,a,b,c,d).real
        cache[key]=v
        return v
    return f
states=list(itertools.combinations(range(10),3))
sid={s:i for i,s in enumerate(states)}
def apply_ops(ops, st):
    # ops list of (type,index) applied right-to-left; returns (sign, newstate) or None
    occ=list(st); sign=1
    for typ,i in reversed(ops):
        if typ=='a':  # annihilate
            if i not in occ: return None
            p=occ.index(i); sign*= (-1)**p; occ.pop(p)
        else:
            if i in occ: return None
            # insert at sorted position
            p=sum(1 for x in occ if x<i); sign*=(-1)**p; occ.insert(p,i)
    return sign, tuple(sorted(occ))
def build(F):
    V=Vint(F)
    H=np.zeros((120,120))
    # two-body: 1/2 sum <ab|V|cd> a+_a a+_b a_d a_c
    for st in states:
        j=sid[st]
        for a in range(10):
            for b in range(10):
                for c in range(10):
                    for d in range(10):
                        ma,sa=so[a]; mb,sb=so[b]; mc,sc=so[c]; md,sd=so[d]
                        # spin delta
                        if sa!=sc or sb!=sd: continue
                        val=V(ma,mb,mc,md)
                        if abs(val)<1e-12: continue
                        r=apply_ops([('c',a),('c',b),('a',d),('a',c)],st)
                        if r is None: continue
                        sg,ns=r
                        H[sid[ns],j]+=0.5*sg*val
    return H
def S2():
    # S^2 = S-S+ + Sz(Sz+1)
    Sp=np.zeros((120,120)); Sz=np.zeros(120)
    for st in states:
        j=sid[st]
        n_up=sum(1 for x in st if so[x][1]==1)
        Sz[j]=0.5*(n_up-(3-n_up))
        for a in range(10):
            for b in range(10):
                ma,sa=so[a]; mb,sb=so[b]
                if ma==mb and sa==1 and sb==-1:
                    r=apply_ops([('c',a),('a',b)],st)
                    if r: sg,ns=r; Sp[sid[ns],j]+=sg
    Sm=Sp.T
    S2m=Sm@Sp+np.diag(Sz*(Sz+1))
    return S2m
def L2():
    # L^2 via L+ L-
    Lp=np.zeros((120,120)); Lz=np.zeros(120)
    for st in states:
        j=sid[st]
        Lz[j]=sum(so[x][0] for x in st)
        for a in range(10):
            for b in range(10):
                ma,sa=so[a]; mb,sb=so[b]
                if sa==sb and ma==mb+1:
                    r=apply_ops([('c',a),('a',b)],st)
                    if r: sg,ns=r; Lp[sid[ns],j]+=sg*np.sqrt(6-mb*(mb+1))
    Lm=Lp.T
    return Lm@Lp+np.diag(Lz*(Lz+1))
EOF
cd /tmp && cat << 'EOF' > run.py
from d3 import *
import numpy as np
S2m=S2(); L2m=L2()
res=[]
for F2,F4 in [(1.0,0.0),(0.0,1.0),(1.0,1.0)]:
    F={0:0.0,2:F2,4:F4}
    H=build(F)
    # project: diagonalize H + mu*S2 + nu*L2 to label (S,L)
    M=H+1e3*S2m+1e-3*L2m
    w,v=np.linalg.eigh(M)
    out=[]
    for i in range(120):
        s2=v[:,i]@S2m@v[:,i]; l2=v[:,i]@L2m@v[:,i]; e=v[:,i]@H@v[:,i]
        out.append((round(s2,3),round(l2,3),round(e,6)))
    import collections
    d=collections.Counter(out)
    print(F2,F4)
    for k in sorted(d): print(k,d[k])
EOF
python3 run.py 2>&1 | head -80