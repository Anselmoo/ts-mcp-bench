
cat << 'EOF' > /tmp/d3.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
l=2; ms=[-2,-1,0,1,2]
def ck(k,m1,m2): # c^k(l m1, l m2)
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*(2*l+1)*gaunt(l,k,l,-m1,m2-m1*0+0*m2,m2) ) if False else None
from sympy.physics.wigner import wigner_3j
def c(k,m1,m2):
    return float((-1)**m1*(2*l+1)*wigner_3j(l,k,l,0,0,0)*wigner_3j(l,k,l,-m1,m1-m2,m2))
spin=[(m,s) for m in ms for s in (0.5,-0.5)]
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
def V(Dq):
    v=np.zeros((5,5))
    for i,m in enumerate(ms):
        v[i,i]={0:6,1:-4,2:1}[abs(m)]*Dq
    v[0,4]=v[4,0]=5*Dq
    return v
def g(a,b,cc,d,F):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=[spin[x] for x in (a,b,cc,d)]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
    return sum(F[k]*c(k,ma,mc)*c(k,md,mb) for k in (0,2,4))
from functools import lru_cache
def build(Dq,B,C):
    F4=C/35; F2=B+5*F4; F={0:0,2:49*F2,4:441*F4}
    v=V(Dq); N=len(dets); H=np.zeros((N,N))
    # second quantization generic
    def apply(ops,det):
        st=list(det); sign=1
        for typ,o in ops:
            if typ=='a':
                if o not in st: return None,0
                p=st.index(o); sign*=(-1)**p; st.pop(p)
            else:
                if o in st: return None,0
                st.insert(0,o)
        perm=sorted(range(len(st)),key=lambda i:st[i])
        # parity
        s=list(st); par=1
        for i in range(len(s)):
            for j in range(i+1,len(s)):
                if s[i]>s[j]: par=-par
        return tuple(sorted(st)),sign*par
    for j,d in enumerate(dets):
        for p in range(10):
            for q in range(10):
                if spin[p][1]!=spin[q][1]: continue
                val=v[ms.index(spin[p][0]),ms.index(spin[q][0])]
                if val==0: continue
                nd,s=apply([('a',q),('c',p)],d)
                if nd: H[idx[nd],j]+=val*s
        for a in range(10):
          for b in range(10):
            for cc in d:
              for dd in d:
                if cc==dd: continue
                val=g(a,b,cc,dd,F)
                if val==0: continue
                nd,s=apply([('a',dd),('a',cc),('c',b),('c',a)],d)
                if nd: H[idx[nd],j]+=0.5*val*s
    return H
import sys
Dq=1449; B=8990/15
def levels(C):
    e=np.linalg.eigvalsh(build(Dq,B,C)); e=e-e[0]
    return e
e=levels(4*B); print(np.round(e[:40]))
def f(C):
    e=levels(C); 
    # lowest level above ground degeneracy 4(4A2 has 12 states incl Ms) 
    return e[12]-12710
Cs=brentq(f,1500,4000,xtol=0.1); print(Cs, Cs/B, np.round(levels(Cs)[:40]))
EOF
python3 /tmp/d3.py
