import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.optimize import least_squares
nth, nph = 40, 80
x, w = np.polynomial.legendre.leggauss(nth)
ph = np.arange(nph)*2*np.pi/nph
TH, PH = np.meshgrid(np.arccos(x), ph, indexing='ij')
W = np.outer(w, np.full(nph, 2*np.pi/nph))
def Y(l,m): return sph_harm_y(l, m, TH, PH)
ms=[-2,-1,0,1,2]
Yd=[Y(2,m) for m in ms]
def integ(f): return np.sum(W*f)
def ak(kk):
    A=np.zeros((5,5,5,5),complex)
    for q in range(-kk,kk+1):
        Yq=Y(kk,q)
        G=np.array([[integ(np.conj(Yd[i])*np.conj(Yq)*Yd[k]) for k in range(5)] for i in range(5)])
        H=np.array([[integ(np.conj(Yd[j])*Yq*Yd[l]) for l in range(5)] for j in range(5)])
        A+=np.einsum('ik,jl->ijkl',G,H)
    return A*4*np.pi/(2*kk+1)
A2=ak(2); A4=ak(4)
print("orthonormal check max dev:", np.abs(np.array([[integ(np.conj(Yd[i])*Yd[j]) for j in range(5)] for i in range(5)])-np.eye(5)).max())
# real d orbitals -> crystal field
X=np.sin(TH)*np.cos(PH); Yc=np.sin(TH)*np.sin(PH); Z=np.cos(TH)
rf={'xy':np.sqrt(15/(4*np.pi))*X*Yc,'yz':np.sqrt(15/(4*np.pi))*Yc*Z,'zx':np.sqrt(15/(4*np.pi))*Z*X,
    'z2':np.sqrt(5/(16*np.pi))*(3*Z**2-1),'x2y2':np.sqrt(15/(16*np.pi))*(X**2-Yc**2)}
names=['xy','yz','zx','z2','x2y2']
# phi_r = sum_j c[r,j] Y_j, c[r,j]=<Y_j|phi_r>
C=np.array([[integ(np.conj(Yd[j])*rf[n]) for j in range(5)] for n in names])
print("real orbital norm check:", np.abs(C@C.conj().T-np.eye(5)).max())
def field_matrix(Dq):
    eps=[-4*Dq]*3+[6*Dq]*2
    V=np.zeros((5,5),complex)
    for r in range(5):
        V+=eps[r]*np.outer(C[r],np.conj(C[r]))  # sum_r eps |phi_r><phi_r|, <Y_i|V|Y_j>=sum eps c_ri conj(c_rj)
    return V
# determinant space M_S=3/2: 5 up (all orbitals), 2 down
dets=[]
for dn in itertools.combinations(range(5),2):
    dets.append(frozenset([(o,0) for o in range(5)]+[(o,1) for o in dn]))
idx={d:i for i,d in enumerate(dets)}
def apply_ops(ops, det):
    # ops: list of (type,orbspin) applied right to left: ops[-1] acts first; returns (sign, newdet) or None
    occ=list(sorted(det, key=lambda t:(t[0],t[1])))  # spin orbital ordering
    order=[(o,s) for o in range(5) for s in (0,1)]
    occset=set(det)
    sign=1
    for typ,p in reversed(ops):
        pos=order.index(p)
        # sign: number of occupied spin-orbitals before p
        nbefore=sum(1 for q in occset if order.index(q)<pos)
        if typ=='a':   # annihilate
            if p not in occset: return None
            occset.remove(p)
        else:          # create
            if p in occset: return None
            occset.add(p)
        if nbefore%2: sign=-sign
    return sign, frozenset(occset)
def Hmat(Dq, F2, F4, Vint=None):
    Vint = F2*A2+F4*A4 if Vint is None else Vint
    Vc=field_matrix(Dq)
    n=len(dets); H=np.zeros((n,n),complex)
    order=[(o,s) for o in range(5) for s in (0,1)]
    for j,dj in enumerate(dets):
        # one-electron
        for (o1,s1) in dj:
            for o2 in range(5):
                for (dummy) in [0]:
                    pass
        # one-electron: sum_{pq} h_pq c+_p c_q, spin diagonal
        for s in (0,1):
            for p in range(5):
                for q in range(5):
                    if abs(Vc[p,q])<1e-14: continue
                    r=apply_ops([('c',(p,s)),('a',(q,s))], dj)
                    if r is None: continue
                    sg,nd=r
                    H[idx[nd],j]+=sg*Vc[p,q]
        # two-electron: 1/2 sum V_pqrs c+_p c+_q c_s c_r ; <pq|rs>=Vint[p,q,r,s] with spins
        occ=list(dj)
        for (pp,sp) in [(a,b) for a in range(5) for b in (0,1)]:
            pass
        for p in range(5):
         for sp in (0,1):
          for q in range(5):
           for sq in (0,1):
            for r in range(5):
             for sr in (0,1):
              for s_ in range(5):
               for ss in (0,1):
                if sp!=sr or sq!=ss: continue
                v=Vint[p,q,r,s_]
                if abs(v)<1e-14: continue
                # c+_(p,sp) c+_(q,sq) c_(s_,ss) c_(r,sr)
                res=apply_ops([('c',(p,sp)),('c',(q,sq)),('a',(s_,ss)),('a',(r,sr))], dj)
                if res is None: continue
                sg,nd=res
                H[idx[nd],j]+=0.5*sg*v
    return H
