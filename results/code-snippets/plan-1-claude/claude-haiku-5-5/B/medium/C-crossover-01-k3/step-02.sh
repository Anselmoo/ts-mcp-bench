
mkdir -p ~/d4 && cd ~/d4 && cat << 'EOF' > d4.py
import numpy as np, itertools
from numpy.polynomial.legendre import leggauss, legval
from scipy.linalg import eigh
B=706.0; C=2734.0
F4=C*7/5; F2=49*B+5*F4
F={2:F2,4:F4}
def orbs(x,y,z):
    s15=np.sqrt(15)
    return np.array([s15*x*y, s15*y*z, s15*x*z, s15/2*(x*x-y*y), np.sqrt(5)/2*(3*z*z-1)])
nt,npz=24,48
ct,wt=leggauss(nt)
phi=np.arange(npz)*2*np.pi/npz; wp=2*np.pi/npz
pts=[];w=[]
for c,wc in zip(ct,wt):
    s=np.sqrt(1-c*c)
    for p in phi:
        pts.append([s*np.cos(p),s*np.sin(p),c]); w.append(wc*wp)
pts=np.array(pts); w=np.array(w)
Phi=orbs(pts[:,0],pts[:,1],pts[:,2])
print("norm", np.round(Phi@(Phi*w[:,None]),6).diagonal())
G=np.clip(pts@pts.T,-1,1)
Q={k:(w[:,None]*w[None,:])*legval(G,[0]*k+[1]) for k in [2,4]}
A={k:np.einsum('ia,ic,ij,jb,jd->acbd',Phi,Phi,Q[k],Phi,Phi,optimize=True) for k in [2,4]}
V=sum(F[k]*A[k] for k in [2,4])
N=10
Vfull=np.zeros((N,N,N,N))
for a,b,c,d in itertools.product(range(5),repeat=4):
    v=V[a,b,c,d]
    if abs(v)<1e-12: continue
    for sa in range(2):
        for sb in range(2):
            Vfull[2*a+sa,2*b+sb,2*c+sa,2*d+sb]=v
dets=list(itertools.combinations(range(N),4))
idx={d:i for i,d in enumerate(dets)}
def apply_ops(ops,det):
    occ=list(det); sign=1
    for typ,i in reversed(ops):
        if typ=='a':
            if i not in occ: return None,0
            p=occ.index(i); sign*=(-1)**p; occ.pop(p)
        else:
            if i in occ: return None,0
            p=sum(1 for o in occ if o<i); sign*=(-1)**p; occ.insert(p,i)
    return tuple(occ),sign
nd=len(dets)
Hee=np.zeros((nd,nd))
nz=[(a,b,c,d,Vfull[a,b,c,d]) for a,b,c,d in itertools.product(range(N),repeat=4) if abs(Vfull[a,b,c,d])>1e-12]
for j,det in enumerate(dets):
    for a,b,c,d,v in nz:
        if c not in det or d not in det: continue
        out,s=apply_ops([('c',a),('c',b),('a',d),('a',c)],det)
        if out is None: continue
        Hee[idx[out],j]+=0.5*v*s
orb_energy=np.array([-4,-4,-4,6,6],float)  # per unit Dq
Hcf=np.array([sum(orb_energy[o//2] for o in det) for det in dets])
Sz=np.array([sum(0.5 if o%2==0 else -0.5 for o in det) for det in dets])
Sp=np.zeros((nd,nd))
for j,det in enumerate(dets):
    for m in range(5):
        out,s=apply_ops([('c',2*m),('a',2*m+1)],det)
        if out is not None: Sp[idx[out],j]+=s
S2=Sp.T@Sp+np.diag(Sz*(Sz+1))
# Ms=0 check of Hee spectrum: d2-like sanity: print lowest Hee eigen in Ms=2 sector
ms2=[i for i,d in enumerate(dets) if Sz[i]==2]
print("Ms=2 Hee eig:", np.round(np.linalg.eigvalsh(Hee[np.ix_(ms2,ms2)]),1))
np.savez('mats.npz',Hee=Hee,Hcf=Hcf,S2=S2,Sz=Sz)
# Ground-state analysis as function of Dq
def spectrum(Dq):
    H=Hee+np.diag(Dq*Hcf)
    # restrict to Ms=0 and Ms=1 sectors for lowest per S
    res={}
    for S in [0,1,2]:
        # use penalty to isolate spin S
        mu=1e6
        M=H+mu*(S2-S*(S+1))@(S2-S*(S+1))
        ev=np.linalg.eigvalsh(M)
        res[S]=ev[0] if False else None
    return res
def lowest_by_spin(Dq):
    H=Hee+np.diag(Dq*Hcf)
    out={}
    for S in [0,1,2]:
        Pm=(S2-S*(S+1)*np.eye(nd))
        M=H+1e7*Pm@Pm
        ev=np.linalg.eigvalsh(M)
        out[S]=ev[0]  # lowest in penalized spectrum (should be spin S)
    return out
for Dq in [0,500,1000,1500,2000,2500,3000,3500]:
    print(Dq, {k:round(v,1) for k,v in lowest_by_spin(Dq).items()})
EOF
python3 d4.py
