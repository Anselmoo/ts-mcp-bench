
cd /tmp/tsbench-run-la9r0a6w && cat << 'EOF' > d3.py
import numpy as np, itertools
from scipy.special import sph_harm, eval_legendre
nt, npz = 24, 48
x, w = np.polynomial.legendre.leggauss(nt)
phi = np.arange(npz)*2*np.pi/npz
ct, ph = np.meshgrid(x, phi, indexing='ij'); W = (np.outer(w, np.ones(npz))*2*np.pi/npz).reshape(-1)
ct=ct.reshape(-1); ph=ph.reshape(-1); st=np.sqrt(1-ct**2)
n = np.stack([st*np.cos(ph), st*np.sin(ph), ct], -1)
Ys = np.array([sph_harm(m, 2, ph, np.arccos(ct)) for m in range(-2,3)])
G = np.clip(n@n.T,-1,1)
def Ck(k):
    P = eval_legendre(k, G)
    Mac = np.einsum('ap,cp,pq->acq', Ys.conj()*W, Ys, P)
    return np.einsum('acq,bq,dq->acbd', Mac, Ys.conj()*W, Ys)
C = {k: Ck(k) for k in (0,2,4)}
states = list(itertools.combinations(range(5),3)); idx={s:i for i,s in enumerate(states)}; N=len(states)
def cre_ann(ops, occ):
    occ=list(occ); sign=1
    for t,o in ops:
        if t=='a':
            if o not in occ: return None
            p=occ.index(o); sign*=(-1)**p; occ.pop(p)
        else:
            if o in occ: return None
            p=sum(1 for x_ in occ if x_<o); sign*=(-1)**p; occ.insert(p,o)
    return sign, tuple(sorted(occ))
def build(F2,F4,D):
    Peg=np.zeros((5,5)); Peg[2,2]=1
    v=np.zeros(5); v[0]=v[4]=1/np.sqrt(2); Peg+=np.outer(v,v)
    h=6*D*Peg-4*D*(np.eye(5)-Peg)
    V=F2*C[2]+F4*C[4]
    H=np.zeros((N,N))
    for k,s in enumerate(states):
        for p in range(5):
            for q in range(5):
                if h[p,q]==0: continue
                r=cre_ann([('c',p),('a',q)], s)
                if r: H[idx[r[1]],k]+=h[p,q]*r[0]
        for p in range(5):
         for q in range(5):
          for r_ in range(5):
           for s_ in range(5):
            val=0.5*V[p,r_,q,s_]
            if abs(val)<1e-12: continue
            r=cre_ann([('c',p),('c',q),('a',s_),('a',r_)], s)
            if r: H[idx[r[1]],k]+=val*r[0]
    return H
EOF
cat << 'EOF' > run.py
from d3 import *
for F2,F4 in [(1,0),(0,1)]:
    H=build(F2,F4,0.0); print(F2,F4,np.round(np.linalg.eigvalsh(H),4))
EOF
python3 run.py