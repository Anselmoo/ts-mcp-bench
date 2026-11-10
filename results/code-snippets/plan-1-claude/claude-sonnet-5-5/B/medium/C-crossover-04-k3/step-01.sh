
cat > /tmp/a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
B,C=922.,4156.
F2=49*B+7*C; F4=63*C/5
F={0:0,2:F2,4:F4}
ms=[-2,-1,0,1,2]
def ck(k,l1,m1,l2,m2):
    # <l1m1|C^k_q|l2m2> with q=m1-m2
    q=m1-m2
    return float((-1)**m1*np.sqrt((2*2+1)*(2*2+1))*gaunt(2,k,2,-m1,q,m2)) 
# <m1 m2|1/r12|m3 m4> = sum_k a_k F^k, a_k = c^k(m1,m3)c^k(m4,m2)
def c(k,a,b):
    return float((-1)**a*5*gaunt(2,k,2,-a,a-b,b))
def V(a,b,cc,d):
    s=0
    for k in (2,4):
        if a+b!=cc+d: return 0
        s+=c(k,a,cc)*c(k,d,b)*F[k]/ (1) *1
    return s
# Gaunt normalization: c^k = sqrt(4pi/(2k+1)) * int Y Y Y ; gaunt gives int YYY. fix factor
import math
def c(k,a,b):
    return float((-1)**a*5*math.sqrt(4*math.pi/(2*k+1))*gaunt(2,k,2,-a,a-b,b))
# check F2 normalization via c^k(0,0): should be <C^2>=-2/7
print(c(2,0,0),c(4,0,0))
# cubic basis: t2: xy=(2,-2 combos), e: z2=m0, x2-y2
s2=1/math.sqrt(2)
orb=np.zeros((5,5),complex) # columns orbitals in m basis index m+2
orb[2,0]=1 # z2 (e)
orb[4,1]=s2;orb[0,1]=s2 # x2-y2 (e)
orb[3,2]=s2;orb[1,2]=-s2 # xz-ish t2
orb[3,3]=s2;orb[1,3]=s2  # yz-ish (complex phase irrelevant for energies? use real combos)
orb[4,4]=s2;orb[0,4]=-s2 # xy
orb[3,3]=s2*1;orb[1,3]=s2
# make xz,yz real combos: use m=±1 combos with i for yz
orb[3,3]=1j*s2*-1;orb[1,3]=1j*s2*-1*-1*-1
# fine: any orthonormal t2 combos spanning m=±1,±2 appropriately
O=orb
# 4-index tensor in m basis
M=np.zeros((5,5,5,5))
for a in range(5):
 for b in range(5):
  for cc in range(5):
   for d in range(5):
    if a+b==cc+d:
     M[a,b,cc,d]=sum(c(k,a-2,cc-2)*c(k,d-2,b-2)*F[k] for k in (2,4))
# <ab|cd> in orbital basis (a,b bra electron1,2; c,d ket)
G=np.einsum('ai,bj,ck,dl,abcd->ijkl',O.conj(),O.conj(),O,O,M) if False else np.einsum('ai,bj,ck,dl,abcd->ijkl',O.conj(),O.conj(),O,O,M)
# spin orbitals p=(orb,spin)
def build(Dq):
    h=np.diag([6*Dq]*2+[-4*Dq]*3)
    N=10
    H1=np.kron(h,np.eye(2))
    # H2 = 1/2 sum <pq|rs> a+p a+q a_s a_r
    def two(p,q,r,s):
        if p%2!=r%2 or q%2!=s%2: return 0
        return G[p//2,q//2,r//2,s//2]
    dets=list(itertools.combinations(range(N),7))
    idx={d:i for i,d in enumerate(dets)}
    return dets,idx,H1,two
dets,idx,H1,two=build(0)
def apply(op,det):
    # op list of (create/annih, index) applied right to left; return sign,newdet
    d=list(det);sg=1
    for typ,i in reversed(op):
        if typ=='a':
            if i not in d: return 0,None
            pos=d.index(i);sg*=(-1)**pos;d.pop(pos)
        else:
            if i in d: return 0,None
            pos=sum(1 for x in d if x<i);sg*=(-1)**pos;d.insert(pos,i)
    return sg,tuple(d)
n=len(dets)
H2=np.zeros((n,n),complex);HL=np.zeros((n,n),complex)
Dlist=[(0,0)]
for j,dt in enumerate(dets):
    for r in range(10):
      for p in range(10):
        if H1[p,r]!=0:
            sg,nd=apply([('c',p),('a',r)],dt)
            if sg: 
                HL[idx[nd],j]+=sg*H1[p,r]/1.0
    for p in range(10):
     for q in range(10):
      for r in range(10):
       for s in range(10):
        v=two(p,q,r,s)
        if abs(v)<1e-12: continue
        sg,nd=apply([('c',p),('c',q),('a',s),('a',r)],dt)
        if sg: H2[idx[nd],j]+=0.5*v*sg
# spin
Sz=np.diag([sum(0.5 if i%2==0 else -0.5 for i in d) for d in dets])
Sp=np.zeros((n,n))
for j,dt in enumerate(dets):
    for o in range(5):
        sg,nd=apply([('c',2*o),('a',2*o+1)],dt)
        if sg: Sp[idx[nd],j]+=sg
S2=Sp.T@Sp+Sz@Sz-Sz  # S-S+ +Sz^2+Sz
HL1=HL/1.0
# HL built with h at Dq=1 -> linear scaling
H1=None
def lev(Dq):
    H=H2+Dq*HLd
    return H
# HL computed with Dq=0 -> zero; recompute with unit
E
echo