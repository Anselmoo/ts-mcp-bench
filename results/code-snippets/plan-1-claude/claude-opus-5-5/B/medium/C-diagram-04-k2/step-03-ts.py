import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
B,C=551.,2511.
F4=C/35; F2=B+5*F4; F0=0.0
Fk={0:F0,2:F2*49,4:F4*441}
ms=[-2,-1,0,1,2]
def ck(k,m,mp):
    return float((-1)**m*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m,m-mp,mp))
orbs=[(m,s) for s in (0,1) for m in ms]; n=10
# two-electron integral <ab|cd> (a,c electron1)
def g(a,b,c,d):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=orbs[a],orbs[b],orbs[c],orbs[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0.
    return sum(ck(k,ma,mc)*ck(k,md,mb)*Fk[k] for k in (0,2,4))
G=np.zeros((n,)*4)
for idx in itertools.product(range(n),repeat=4): G[idx]=g(*idx)
dets=[c for c in itertools.combinations(range(n),6)]
index={d:i for i,d in enumerate(dets)}; N=len(dets)
def apply_ops(ops,det):
    # ops list of (type,orb) applied right-to-left; type 'a' annihilate, 'c' create
    occ=list(det); sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in occ: return None,0
            p=occ.index(o); sign*=(-1)**p; occ.pop(p)
        else:
            if o in occ: return None,0
            occ2=sorted(occ+[o]); p=occ2.index(o); sign*=(-1)**p; occ=occ2
    return tuple(occ),sign
def onebody(h):
    M=np.zeros((N,N),complex)
    for j,d in enumerate(dets):
        for p in range(n):
            for q in range(n):
                if abs(h[p,q])<1e-14: continue
                r,s=apply_ops([('c',p),('a',q)],d)
                if r: M[index[r],j]+=h[p,q]*s
    return M
HC=np.zeros((N,N))
for j,d in enumerate(dets):
    for p,q,r,s_ in itertools.product(range(n),repeat=4):
        v=G[p,q,r,s_]
        if v==0: continue
        if r not in d or s_ not in d: continue
        res,sg=apply_ops([('c',p),('c',q),('a',s_),('a',r)],d)
        if res: HC[index[res],j]+=0.5*v*sg
# crystal field, Dq=1
v=np.zeros((5,5)); 
for i,m in enumerate(ms): v[i,i]={0:6,1:-4,2:1}[abs(m)]
v[0,4]=v[4,0]=5
hcf=np.kron(np.eye(2),v); HCF=onebody(hcf).real
# spin
sp=np.zeros((n,n)); sz=np.zeros((n,n))
for i,(m,s) in enumerate(orbs):
    sz[i,i]=0.5 if s==0 else -0.5
    if s==1: sp[orbs.index((m,0)),i]=1
Sp=onebody(sp).real; Sz=onebody(sz).real
S2=Sp.T@Sp+Sz@Sz+Sz
Mz=np.array([sum(orbs[o][0] for o in d) for d in dets])
Msv=np.diag(Sz)
sel=np.where(abs(Msv)<1e-9)[0]
C4=np.exp(-1j*np.pi/2*Mz[sel])
# C3 about (111): use rotation matrix in d-orbital basis via Wigner D; simpler: build via sympy
from sympy.physics.quantum.spin import Rotation
from sympy import N as sN, pi as spi, atan, sqrt
# C3 about [111] = Euler (alpha,beta,gamma)=(0,pi/2,pi/2) maps x->y->z
D=np.array([[complex(sN(Rotation.D(2,m1,m2,0,spi/2,spi/2).doit())) for m2 in ms] for m1 in ms])
d6=np.kron(np.eye(2),D)
def manybody_rot(R):
    M=np.zeros((N,N),complex)
    for j,d in enumerate(dets):
        # determinant of R columns
        for i,e in enumerate(dets):
            if Msv[i]!=Msv[j]: continue
            M[i,j]=np.linalg.det(R[np.ix_(e,d)])
    return M
R3=manybody_rot(d6)[np.ix_(sel,sel)]
np.save('mats.npy',dict(HC=HC,HCF=HCF,S2=S2,sel=sel,C4=C4,R3=R3),allow_pickle=True)
print(N, np.allclose(R3@R3@R3,np.eye(len(sel))))
