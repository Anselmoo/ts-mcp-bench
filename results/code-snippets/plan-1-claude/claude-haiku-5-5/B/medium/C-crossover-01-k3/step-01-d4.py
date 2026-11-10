import numpy as np, itertools
from scipy.optimize import brentq
from numpy.polynomial.legendre import leggauss, legval
B=706.0; C=2734.0
F4=C*7/5; F2=49*B+5*F4   # Racah: B=(F2-5F4)/49, C=5F4/7
F={0:None,2:F2,4:F4}
# real d orbitals as polynomials in x,y,z on unit sphere
def orbs(x,y,z):
    s3=np.sqrt(3); s15=np.sqrt(15)
    t2g=[s15*x*y, s15*y*z, s15*x*z]
    eg=[s15/2*(x*x-y*y), np.sqrt(5)/2*(3*z*z-1)]
    return np.array(t2g+eg)  # index 0-2 t2g, 3-4 eg
# Gauss grid
nt,npz=24,48
ct,wt=leggauss(nt)
phi=np.arange(npz)*2*np.pi/npz; wp=2*np.pi/npz
pts=[];w=[]
for c,wc in zip(ct,wt):
    s=np.sqrt(1-c*c)
    for p in phi:
        pts.append([s*np.cos(p),s*np.sin(p),c]); w.append(wc*wp)
pts=np.array(pts); w=np.array(w)
Phi=orbs(pts[:,0],pts[:,1],pts[:,2])  # 5 x N
# normalization check
print("norm", np.round(Phi@(Phi*w).T,6).diagonal())
G=pts@pts.T; G=np.clip(G,-1,1)
Q={k:(w[:,None]*w[None,:])*legval(G,[0]*k+[1]) for k in [0,2,4]}
A={k:np.einsum('ia,ic,ij,jb,jd->acbd',Phi,Phi,Q[k],Phi,Phi) for k in [0,2,4]}
V=sum(F[k]*A[k] for k in [2,4]) + 0  # F0 contributes constant
# spin orbitals: idx = 2*orb + s (s=0 up,1 down)
N=10
Vso=np.zeros((N,N,N,N))
for a,b,c,d in itertools.product(range(5),repeat=4):
    for sa in range(2):
        for sb in range(2):
            Vso[2*a+sa,2*b+sb,2*c+sc,2*d+sd] if False else None
# build directly
Vfull=np.zeros((N,N,N,N))
for a in range(5):
 for b in range(5):
  for c in range(5):
   for d in range(5):
    v=V[a,b,c,d]
    if abs(v)<1e-14: continue
    for sa in range(2):
     for sb in range(2):
      Vfull[2*a+sa,2*b+sb,2*c+sa,2*d+sb]=v
# determinants with 4 electrons
dets=list(itertools.combinations(range(N),4))
idx={d:i for i,d in enumerate(dets)}
def apply_ops(ops,det):
    # ops list of (type,i) applied right-to-left: list in order as operator product left to right
    occ=list(det); sign=1
    for typ,i in reversed(ops):
        if typ=='a':  # annihilate
            if i not in occ: return None,0
            p=occ.index(i); sign*=(-1)**p; occ.pop(p)
        else:
            if i in occ: return None,0
            p=sum(1 for o in occ if o<i); sign*=(-1)**p; occ.insert(p,i)
    return tuple(occ),sign
H=np.zeros((len(dets),len(dets)))
# one-electron Ligand field diag: t2g -4Dq, eg +6Dq (unit Dq); store separately
T1=np.zeros((len(dets),len(dets)))
Hee=np.zeros_like(H)
nz=[(a,b,c,d,Vfull[a,b,c,d]) for a,b,c,d in itertools.product(range(N),repeat=4) if abs(Vfull[a,b,c,d])>1e-14]
for j,det in enumerate(dets):
    for a,b,c,d,v in nz:
        # 1/2 V a†a a†b a_d a_c
        if c not in det or d not in det: continue
        out,s=apply_ops([('c',a),('c',b),('a',d),('a',c)],det)
        if out is None: continue
        Hee[idx[out],j]+=0.5*v*s
# one-electron diag
orb_energy=np.array([-4,-4,-4,6,6])
Hcf_diag=np.array([sum(orb_energy[o//2] for o in det) for det in dets],float)
# S_z, S+ 
Sz=np.array([sum(0.5 if o%2==0 else -0.5 for o in det) for det in dets])
Sp=np.zeros_like(H)
for j,det in enumerate(dets):
    for m in range(5):
        out,s=apply_ops([('c',2*m),('a',2*m+1)],det)
        if out is not None: Sp[idx[out],j]+=s
Sm=Sp.T
S2=Sm@Sp+np.diag(Sz*(Sz+1))
np.save('/tmp/Hee.npy',Hee); np.save('/tmp/Hcf.npy',Hcf_diag); np.save('/tmp/S2.npy',S2); np.save('/tmp/Sz.npy',Sz)
print("done", np.allclose(Hee,Hee.T))
