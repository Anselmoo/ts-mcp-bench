import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
l=2
# spin-orbitals: index = 2*orb + s, orb m=-2..2 -> 0..4
ms=[-2,-1,0,1,2]
def G(k,ma,q,mc): return float(gaunt(l,k,l,-ma,q,mc)) if abs(q)<=k and abs(-ma+q-mc)==0 else 0.0
# angular coefficient for <m_a m_b|V|m_c m_d> per k (without F^k)
def ang(k,a,b,c,d):
    if ma_ok(a,b,c,d)==False: return 0.0
    s=0.0
    for q in range(-k,k+1):
        s+= ((-1)**(a+q))*G(k,a,-q,c)*((-1)**b)*G(k,b,q,d)
    return 4*np.pi/(2*k+1)*s
def ma_ok(a,b,c,d): return (a+b-c-d)==0
A={}
for k in (0,2,4):
    T=np.zeros((5,5,5,5))
    for a,b,c,d in itertools.product(range(5),repeat=4):
        T[a,b,c,d]=ang(k,ms[a],ms[b],ms[c],ms[d])
    A[k]=T
# single-particle projectors in complex basis (index i -> m=ms[i])
def vec(d): 
    v=np.zeros(5,complex)
    for m,c in d.items(): v[ms.index(m)]=c
    return v
s2=np.sqrt(2)
t2g=[vec({2:1/(1j*s2),-2:-1/(1j*s2)}), vec({1:1/s2,-1:-1/s2}), vec({1:1/(1j*s2),-1:1/(1j*s2)})]
eg=[vec({0:1}), vec({2:1/s2,-2:1/s2})]
Pt=sum(np.outer(v,v.conj()) for v in t2g)
Pe=sum(np.outer(v,v.conj()) for v in eg)
def h1(Dq): return -4*Dq*Pt+6*Dq*Pe
# Fock space: 10 spin orbitals, 4 electrons
states=[c for c in itertools.combinations(range(10),4)]
idx={s:i for i,s in enumerate(states)}
def apply_ops(occ, ops):
    # ops: list of (type,i) applied right-to-left; returns (sign,newocc) or None
    occ=list(occ); sign=1
    for t,i in reversed(ops):
        if t=='c':  # annihilate
            if i not in occ: return None
            p=occ.index(i); sign*=(-1)**p; occ.pop(p)
        else:
            if i in occ: return None
            # insert creation at front-sorted position
            p=sum(1 for x in occ if x<i); sign*=(-1)**p; occ.insert(p,i)
    return sign,tuple(sorted(occ))
def build(Dq,Bv,Cv):
    F={0:None,2:49*Bv+7*Cv,4:441*Cv/35}
    F[0]=0.0  # F0 constant irrelevant for splittings
    N=len(states); H=np.zeros((N,N))
    h=h1(Dq)
    # one-body
    for j,occ in enumerate(states):
        for a in range(10):
            for b in range(10):
                ma,sa=ms[a//2],a%2; mb,sb=ms[b//2],b%2
                if sa!=sb: continue
                hv=h[a//2,b//2]
                if abs(hv)<1e-12: continue
                r=apply_ops(occ,[('c',a),('a',b)]) if False else None
                r=apply_ops(occ,[('c',a),('a',b)])
                if r is None: continue
                sg,new=r; H[idx[new],j]+=sg*hv.real
    # two-body: 1/2 sum V_{abcd} c+_a c+_b c_d c_c  with <ab|V|cd>
    for j,occ in enumerate(states):
        for a in range(10):
          for b in range(10):
            for c in range(10):
              for d in range(10):
                sa,sb,sc,sd=a%2,b%2,c%2,d%2
                if sa!=sd or sb!=sc: continue
                val=0.0
                for k in (2,4):
                    val+=F[k]*A[k][a//2,b//2,c//2,d//2]
                if abs(val)<1e-12: continue
                r=apply_ops(occ,[('c',a),('c',b),('a',d),('a',c)])
                if r is None: continue
                sg,new=r; H[idx[new],j]+=0.5*sg*val
    return H
def spinS2(occ):
    pass
# S_z total and total S^2 to separate multiplicity
def Sz(occ): return sum(0.5 if x%2==0 else -0.5 for x in occ)
def Sminus_plus_matrix():
    N=len(states); Sp=np.zeros((N,N))
    for j,occ in enumerate(states):
        for m in range(5):
            r=apply_ops(occ,[('c',2*m),('a',2*m+1)])
            if r: sg,new=r; Sp[idx[new],j]+=sg
    return Sp
Sp=Sminus_plus_matrix()
S2=Sp.T@Sp + np.diag([Sz(o) for o in states])*0  # placeholder
Szv=np.diag([Sz(o) for o in states])
S2=Sp.T@Sp+Szv@Szv+Szv  # S^2 = S- S+ + Sz^2 + Sz ... check sign
