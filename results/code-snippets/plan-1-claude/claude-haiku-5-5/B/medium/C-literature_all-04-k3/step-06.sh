cd ~ 2>/dev/null; python3 - << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import N as sN
from scipy.optimize import fsolve
l=2
ms=[(m,s) for m in range(-2,3) for s in (0,1)]
def G(l1,l2,l3,m1,m2,m3): return float(sN(gaunt(l1,l2,l3,m1,m2,m3)))
def Cmat(k,q,ma,mc): return np.sqrt(4*np.pi/(2*k+1))*(-1)**ma*G(l,k,l,-ma,q,mc)
def Vel(k):
    V=np.zeros((10,10,10,10))
    for a,(ma,sa) in enumerate(ms):
      for b,(mb,sb) in enumerate(ms):
        for c,(mc,sc) in enumerate(ms):
          for d,(md,sd) in enumerate(ms):
            if sa!=sc or sb!=sd: continue
            tot=0.0
            for q in range(-k,k+1):
                if ma-mc!=-q or mb-md!=q: continue
                tot+=(-1)**q*Cmat(k,-q,ma,mc)*Cmat(k,q,mb,md)
            V[a,b,c,d]=tot
    return V
Vs={k:Vel(k) for k in [0,2,4]}
s2=np.sqrt(2)
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
print('h1 eig',np.round(np.linalg.eigvalsh(h1),6))
states=list(itertools.combinations(range(10),3))
idx={s:i for i,s in enumerate(states)}
def apply_ops(ops,state):
    occ=list(state); sign=1
    for typ,o in ops:
        if typ=='a':
            if o not in occ: return None,0
            p=occ.index(o); sign*=(-1)**p; occ.pop(p)
        else:
            if o in occ: return None,0
            p=sum(1 for x in occ if x<o); sign*=(-1)**p; occ.insert(p,o)
    return tuple(occ),sign
Ms={k:np.zeros((120,120)) for k in [0,2,4]}
Hcf=np.zeros((120,120))
S2=np.zeros((120,120))
# spin-orbital index: ms[i]=(m,s) ; s=0 up, s=1 down
def opidx(m,s): return ms.index((m,s))
for i,s in enumerate(states):
    for a in range(10):
        for c in range(10):
            if abs(h1[a,c])>1e-14:
                t,sg=apply_ops([('a',c),('c',a)],s)
                if t is not None: Hcf[idx[t],i]+=sg*h1[a,c].real
    for k in [0,2,4]:
        V=Vs[k]
        for a in range(10):
         for b in range(10):
          for c in range(10):
           for d in range(10):
            v=V[a,b,c,d]
            if abs(v)<1e-14: continue
            t,sg=apply_ops([('a',c),('a',d),('c',b),('c',a)],s)
            if t is not None: Ms[k][idx[t],i]+=0.5*sg*v
# S+ = sum_m c+_{m up} c_{m down}; S- = transpose; S2 = S-S+ + Sz(Sz+1)
Sp=np.zeros((120,120))
for i,s in enumerate(states):
    for m in range(-2,3):
        t,sg=apply_ops([('a',opidx(m,1)),('c',opidx(m,0))],s)
        if t is not None: Sp[idx[t],i]+=sg
Sz=np.zeros(120)
for i,s in enumerate(states):
    Sz[i]=sum(0.5 if ms[x][1]==0 else -0.5 for x in s)
S2=Sp.T@Sp+np.diag(Sz*(Sz+1))  # S- S+ = (S+)^T S+ ; S^2 = S-S+ + Sz^2 + Sz... use Sz(Sz+1) - Sz? check below
# correct: S^2 = S+S- + Sz^2 - Sz = S-S+ + Sz^2 + Sz
S2=Sp.T@Sp+np.diag(Sz**2+Sz)
def build(Dq,B,C):
    F4=441*C/35; F2=(441*B+5*F4)/9
    return Dq*Hcf+F2*Ms[2]+F4*Ms[4]
def quart_levels(H):
    w,v=np.linalg.eigh(S2)
    Q=v[:,np.abs(w-3.75)<1e-6]; D=v[:,np.abs(w-0.75)<1e-6]
    hq=Q.T@H@Q; hd=D.T@H@D
    return np.round(np.linalg.eigvalsh(hq),3), np.round(np.linalg.eigvalsh(hd),3)
q,d=quart_levels(build(0,1.0,4.0))
print('Dq=0,B=1,C=4 quartets',q)
print('doublets',d)
np.save if False else None
import pickle
pickle.dump({'Ms2':Ms[2],'Ms4':Ms[4],'Hcf':Hcf,'S2':S2},open('/root/ops.pkl','wb')) if False else None
def levels(Dq,B,C):
    q,d=quart_levels(build(Dq,B,C))
    return q,d
# Check 4T2 and 4T1 positions at a sample
q,d=levels(1750,600,3000)
print('sample quart',q)
print('sample doub',d)
EOF