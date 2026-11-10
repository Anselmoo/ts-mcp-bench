mkdir -p ~/w && cd ~/w && cat << 'EOF' > d3.py
import itertools, numpy as np
from sympy.physics.wigner import gaunt
from sympy import N
so=[(m,s) for m in range(-2,3) for s in (1,-1)]
def ang(k,a,b,c,d):
    tot=0.0
    for q in range(-k,k+1):
        g1=complex(N(gaunt(2,k,2,-a,q,c)))*(-1)**a
        g2=complex(N(gaunt(2,k,2,-b,-q,d)))*(-1)**b
        tot+= (-1)**q * g1*g2
    return tot*4*np.pi/(2*k+1)
states=list(itertools.combinations(range(10),3))
sid={s:i for i,s in enumerate(states)}
def apply_ops(ops, st):
    occ=list(st); sign=1
    for typ,i in reversed(ops):
        if typ=='a':
            if i not in occ: return None
            p=occ.index(i); sign*=(-1)**p; occ.pop(p)
        else:
            if i in occ: return None
            p=sum(1 for x in occ if x<i); sign*=(-1)**p; occ.insert(p,i)
    return sign, tuple(sorted(occ))
def angtab():
    T={}
    for a,b,c,d in itertools.product(range(-2,3),repeat=4):
        T[(a,b,c,d)]={k:ang(k,a,b,c,d).real for k in (0,2,4)}
    return T
AT=angtab()
def build(F):
    H=np.zeros((120,120))
    for st in states:
        j=sid[st]
        for a in range(10):
            for b in range(10):
                for c in range(10):
                    for d in range(10):
                        ma,sa=so[a]; mb,sb=so[b]; mc,sc=so[c]; md,sd=so[d]
                        if sa!=sc or sb!=sd: continue
                        val=sum(F[k]*AT[(ma,mb,mc,md)][k] for k in (0,2,4))
                        if abs(val)<1e-12: continue
                        r=apply_ops([('c',a),('c',b),('a',d),('a',c)],st)
                        if r is None: continue
                        sg,ns=r
                        H[sid[ns],j]+=0.5*sg*val
    return H
def S2():
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
    return Sp.T@Sp+np.diag(Sz*(Sz+1))
def L2():
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
    return Lp.T@Lp+np.diag(Lz*(Lz+1))
EOF
cat << 'EOF' > run.py
from d3 import *
import collections
S2m=S2(); L2m=L2()
for F2,F4 in [(1.0,0.0),(0.0,1.0)]:
    H=build({0:0.0,2:F2,4:F4})
    M=H+1e3*S2m+1e-3*L2m
    w,v=np.linalg.eigh(M)
    out=[]
    for i in range(120):
        x=v[:,i]
        out.append((round(x@S2m@x,2),round(x@L2m@x,2),round(x@H@x,4)))
    d=collections.Counter([(a,b) for a,b,_ in out])
    print("F2,F4=",F2,F4)
    for k in sorted(d): 
        es=sorted(set(round(e,4) for a,b,e in out if (a,b)==k))
        print(k,d[k],es)
EOF
timeout 900 python3 run.py