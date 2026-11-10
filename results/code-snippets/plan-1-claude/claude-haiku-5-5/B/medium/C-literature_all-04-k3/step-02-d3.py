import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import N as sN
from scipy.optimize import fsolve
l=2
# spin-orbitals: index = 2*(m+2)+s, s=0 up,1 down
def so(m,s): return 2*(m+2)+s
ms=[(m,s) for m in range(-2,3) for s in (0,1)]
def G(l1,l2,l3,m1,m2,m3):
    return float(sN(gaunt(l1,l2,l3,m1,m2,m3)))
def Cmat(k,q,ma,mc):  # <l ma|C^k_q|l mc>
    if ma-mc!=q and False: pass
    return np.sqrt(4*np.pi/(2*k+1))*(-1)**ma*G(l,k,l,-ma,q,mc)
# two-electron integrals per unit F_k
Vk={}
ks=[0,2,4]
def Vel(k):
    V=np.zeros((10,10,10,10))
    for a,(ma,sa) in enumerate(ms):
      for b,(mb,sb) in enumerate(ms):
        for c,(mc,sc) in enumerate(ms):
          for d,(md,sd) in enumerate(ms):
            if sa!=sc or sb!=sd: continue
            tot=0.0
            for q in range(-k,k+1):
                if ma-mc!=-q or mb-md!=q: continue   # selection
                tot+=(-1)**q*Cmat(k,-q,ma,mc)*Cmat(k,q,mb,md)
            V[a,b,c,d]=tot
    return V
Vs={k:Vel(k) for k in ks}
# one-electron cubic field projector (per Dq units): eg +6, t2g -4
# real-like orbitals as combos of complex m
s2=np.sqrt(2)
orb={}
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
orbs={'z2':vec({0:1}),'x2y2':vec({2:1/s2,-2:1/s2}),
      'xy':vec({2:1j/s2,-2:-1j/s2}),'xz':vec({1:-1/s2,-1:1/s2}),'yz':vec({1:1j/s2,-1:1j/s2})}
h1=np.zeros((10,10),complex)
for name,v in orbs.items():
    e=6.0 if name in('z2','x2y2') else -4.0
    P=np.outer(v,v.conj())
    for i,(mi,si) in enumerate(ms):
        for j,(mj,sj) in enumerate(ms):
            if si==sj: h1[i,j]+=e*P[mi+2,mj+2]
# Fock basis
states=list(itertools.combinations(range(10),3))
idx={s:i for i,s in enumerate(states)}
def apply_ops(ops,state):
    # ops: list of (type,orbital) applied right-to-left; type 'c' create, 'a' annihilate
    occ=list(state); sign=1
    for typ,o in ops:
        if typ=='a':
            if o not in occ: return None,0
            p=occ.index(o); sign*=(-1)**p; occ.pop(p)
        else:
            if o in occ: return None,0
            p=sum(1 for x in occ if x<o); sign*=(-1)**p; occ.insert(p,o)
    return tuple(occ),sign
def build(Dq,B,C):
    F2=(441*B+5*(441*C/35))/9   # from B=(9F2-5F4)/441, C=35F4/441
    F4=441*C/35
    F0=0.0
    V=F0*Vs[0]+F2*Vs[2]+F4*Vs[4]
    H=np.zeros((120,120))
    H_1=h1*Dq
    for i,s in enumerate(states):
        # one-electron
        for a in range(10):
            for c in range(10):
                if abs(H_1[a,c])<1e-14: continue
                t,sg=apply_ops([('c',a),('a',c)],s)
                if t is None: continue
                H[idx[t],i]+=sg*H_1[a,c].real
        # two-electron: 1/2 sum V[a,b,c,d] c+a c+b cd cc
        for a in range(10):
          for b in range(10):
            for c in range(10):
              for d in range(10):
                v=V[a,b,c,d]
                if abs(v)<1e-14: continue
                t,sg=apply_ops([('c',a),('c',b),('a',d),('a',c)],s)
                if t is None: continue
                H[idx[t],i]+=0.5*sg*v
    return H
if __name__=='__main__':
    # test: free ion, Dq=0
    H=build(0,1.0,4.0)
    ev=np.linalg.eigvalsh(H)
    print(np.round(np.unique(np.round(ev,6)),4))
