mkdir -p /w && cat > /w/d5.py <<'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from functools import lru_cache
l=2
ms=[-2,-1,0,1,2]
def G(a,b,c):
    return float(gaunt(a[0],b[0],c[0],a[1],b[1],c[1]))
# spatial-orbital Gaunt tables
def Ang(mi,mk,K,q):
    # int conj(Y_{2mi}) Y_{2mk} conj(Y_{Kq})
    if -mi+mk-q!=0 or abs(q)>K: return 0.0
    return (-1)**(mi)*((-1)**q)*float(gaunt(2,2,K,-mi,mk,-q))
# spin-orbital index: (mi_index, s) s=0 up,1 down
orbs=[(m,s) for m in ms for s in (0,1)]
N=10
# real cubic basis coefficient vectors in complex Y_{2m} basis (index by m)
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
r2=np.sqrt(2)
t2g=[vec({-2:1/(1j*r2),2:-1/(1j*r2)}), vec({-1:-1/r2,1:1/r2}), vec({-1:1/(1j*r2),1:1/(1j*r2)})]
eg=[vec({0:1}), vec({-2:1/r2,2:1/r2})]
def build(Dq,B,C):
    F4=12.6*C; F2=49*B+7*C
    F={0:0.0,2:F2,4:F4}
    # one-electron matrix in complex spatial basis
    h=np.zeros((5,5),complex)
    for v in t2g: h+= -4*Dq*np.outer(v,v.conj())
    for v in eg: h+= 6*Dq*np.outer(v,v.conj())
    # two-electron integrals in spin-orbital basis <ij|kl> (electron1: i->k, electron2: j->l)
    V=np.zeros((N,N,N,N))
    for i,(mi,si) in enumerate(orbs):
     for k,(mk,sk) in enumerate(orbs):
      if si!=sk: continue
      for j,(mj,sj) in enumerate(orbs):
       for ll,(ml,sl) in enumerate(orbs):
        if sj!=sl: continue
        val=0.0
        for K in (0,2,4):
          if F[K]==0: continue
          for q in range(-K,K+1):
            a=Ang(mi,mk,K,q); 
            if a==0: continue
            b=Ang(mj,ml,K,-q)
            if b==0: continue
            val+= 4*np.pi/(2*K+1)*F[K]*a*b
        V[i,j,k,ll]=val
    # Hamiltonian in Fock space of 5 electrons: determinants as sorted tuples
    dets=[c for c in itertools.combinations(range(N),5)]
    idx={d:n for n,d in enumerate(dets)}
    # one-electron spin-orbital matrix
    h1=np.zeros((N,N),complex)
    for i,(mi,si) in enumerate(orbs):
        for k,(mk,sk) in enumerate(orbs):
            if si==sk: h1[i,k]=h[mi+2,mk+2]
    H=np.zeros((len(dets),len(dets)),complex)
    def apply_ops(state, ops):
        # ops list of ('c'|'a', idx) applied right to left: ops given in order of application (first applied first)
        s=list(state); sign=1
        for typ,p in ops:
            if typ=='a':
                if p not in s: return None,0
                pos=s.index(p); sign*=(-1)**pos; s.pop(pos)
            else:
                if p in s: return None,0
                pos=sum(1 for x in s if x<p); sign*=(-1)**pos; s.insert(pos,p)
        return tuple(s),sign
    for n,d in enumerate(dets):
        # one-body: sum h1[i,k] a+_i a_k
        for i in range(N):
            for k in range(N):
                if h1[i,k]==0: continue
                s,sg=apply_ops(d,[('a',k),('c',i)])
                if s is None: continue
                H[idx[s],n]+=sg*h1[i,k]
        # two-body: 1/2 sum V[i,j,k,l] a+_i a+_j a_l a_k
        for i in range(N):
         for j in range(N):
          for k in range(N):
           for ll in range(N):
            v=V[i,j,k,ll]
            if v==0: continue
            s,sg=apply_ops(d,[('a',k),('a',ll),('c',j),('c',i)])
            if s is None: continue
            H[idx[s],n]+=0.5*sg*v
    # S^2
    Sz=np.zeros(len(dets))
    Sp=np.zeros((len(dets),len(dets)))
    # S+ = sum_m a+_{m up} a_{m down}
    for n,d in enumerate(dets):
        for m in ms:
            iu=orbs.index((m,0)); idn=orbs.index((m,1))
            s,sg=apply_ops(d,[('a',idn),('c',iu)])
            if s is not None: Sp[idx[s],n]+=sg
    Szv=np.array([sum(0.5 if orbs[p][1]==0 else -0.5 for p in d) for d in dets])
    S2=Sp.T@Sp*0  # placeholder
    Smin=Sp.T
    S2 = Smin@Sp + np.diag(Szv)+np.diag(Szv)**2*0
    # S^2 = S- S+ + Sz^2 + Sz ; S- = Sp^T
    S2 = Sp.T@Sp + np.diag(Szv**2+Szv)
    return H,S2,dets
def doublet_energies(Dq,B,C,nlev=8):
    H,S2,dets=build(Dq,B,C)
    w,U=np.linalg.eigh(S2)
    # doublets: S2 eigenvalue 3/4
    P=U[:,np.abs(w-0.75)<1e-6]
    Hd=P.conj().T@H@P
    e=np.sort(np.linalg.eigvalsh(Hd).real)
    return e
if __name__=="__main__":
    import sys
    e=doublet_energies(1000,500,2200)
    print(np.round(e-e[0],1))
EOF
cd /w && time python3 d5.py