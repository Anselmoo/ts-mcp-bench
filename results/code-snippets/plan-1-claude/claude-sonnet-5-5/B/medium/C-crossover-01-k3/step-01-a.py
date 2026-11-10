import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
B=706.;C=2734.
F2=49*B+7*C;F4=63*C/5
ms=[-2,-1,0,1,2]
def ck(k,m1,m2): # <2 m1|C^k|2 m2>
    return float((-1)**m1*np.sqrt(5*5)*0+0)
from sympy import sqrt as ss, Rational
def ckf(k,m1,m2):
    # <l m1|C^k_q|l m2>, q=m1-m2 ; = (-1)^m1 *5*3j(2 -m1;k q;2 m2)*3j(2 0 k 0 2 0)
    from sympy.physics.wigner import wigner_3j
    q=m1-m2
    return float((-1)**m1*5*wigner_3j(2,k,2,-m1,q,m2)*wigner_3j(2,k,2,0,0,0))
Fk={0:0,2:F2/49,4:F4/441}
# orbitals: (m,spin) index
orbs=[(m,s) for m in ms for s in (0,1)]
n=10
V=np.zeros((n,n,n,n))  # <ab|1/r|cd> physicist
for a,(ma,sa) in enumerate(orbs):
 for b,(mb,sb) in enumerate(orbs):
  for c,(mc,sc) in enumerate(orbs):
   for d,(md,sd) in enumerate(orbs):
    if sa!=sc or sb!=sd or ma+mb!=mc+md: continue
    v=0
    for k in (2,4):
        v+=Fk[k]*ckf(k,ma,mc)*ckf(k,md,mb)*(-1)**0  # c^k(a,c)c^k(d,b)
    V[a,b,c,d]=v
def H(Dq,Ms):
    h1=np.zeros((n,n))
    for a,(m,s) in enumerate(orbs):
        for b,(m2,s2) in enumerate(orbs):
            if s!=s2: continue
            if m==m2: h1[a,b]=Dq*{0:6,1:-4,-1:-4,2:1,-2:1}[m]
            elif abs(m)==2 and m==-m2: h1[a,b]=5*Dq
    N=4
    S=(N+Ms)/2 # nup
    nup=int((4+Ms)//2) if False else None
    return h1
def energies(Dq,Sz):
    h1=H(Dq,0)
    nup=(4+Sz)//2
    basis=[c for c in itertools.combinations(range(n),4) if sum(1 for i in c if orbs[i][1]==0)==nup]
    idx={b:i for i,b in enumerate(basis)}
    Hm=np.zeros((len(basis),)*2)
    # build via second quantization
    def apply(ops,state):
        st=list(state);sign=1
        for typ,o in ops:
            if typ=='a':
                if o not in st: return None,0
                p=st.index(o);sign*=(-1)**p;st.pop(p)
            else:
                if o in st: return None,0
                p=sum(1 for x in st if x<o);sign*=(-1)**p;st.insert(p,o)
        return tuple(st),sign
    for j,b in enumerate(basis):
        for a in range(n):
            for c in range(n):
                if h1[a,c]!=0:
                    s,sg=apply([('a',c),('c',a)],b)
                    if s is not None: Hm[idx[s],j]+=h1[a,c]*sg
        for a in range(n):
         for bb in range(n):
          for c in range(n):
           for d in range(n):
            v=V[a,bb,c,d]
            if v==0: continue
            s,sg=apply([('a',d),('a',c),('c',bb),('c',a)],b)
            if s is not None and s in idx: Hm[idx[s],j]+=0.5*v*sg
    return np.linalg.eigvalsh(Hm)[0]
f=lambda Dq: energies(Dq,0 if False else 2)-energies(Dq,2) 
def g(Dq): return energies(Dq,2)-energies(Dq,0)
# Sz in nup terms: Sz=2 ->nup=4; Sz=0 -> nup=2 ; but singlets lower? check triplet by Sz=2*1
def lowest_triplet_or_lower(Dq): return energies(Dq,0)
for Dq in (1500,1800,2000,2200,2500):
    print(Dq,energies(Dq,4),energies(Dq,2),energies(Dq,0))
