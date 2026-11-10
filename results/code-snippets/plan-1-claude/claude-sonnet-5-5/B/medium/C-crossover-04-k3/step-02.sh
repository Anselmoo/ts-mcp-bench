
mkdir -p /tmp/w && cd /tmp/w && cat > a.py <<'E'
import numpy as np, itertools, math
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
B,C=922.,4156.
F={2:49*B+7*C,4:63*C/5}
def c(k,a,b):
    return float((-1)**a*5*math.sqrt(4*math.pi/(2*k+1))*gaunt(2,k,2,-a,a-b,b))
s=1/math.sqrt(2)
O=np.zeros((5,5),complex) # rows m+2, cols orbitals
O[2,0]=1; O[4,1]=s;O[0,1]=s
O[3,2]=s;O[1,2]=-s
O[3,3]=1j*s;O[1,3]=1j*s
O[4,4]=s;O[0,4]=-s*1
M=np.zeros((5,5,5,5))
for a in range(5):
 for b in range(5):
  for cc in range(5):
   for d in range(5):
    if a+b==cc+d:
     M[a,b,cc,d]=sum(c(k,a-2,cc-2)*c(k,d-2,b-2)*F[k] for k in (2,4))
G=np.einsum('ai,bj,ck,dl,abcd->ijkl',O.conj(),O.conj(),O,O,M)
h=np.diag([6.]*2+[-4.]*3)
dets=list(itertools.combinations(range(10),7)); idx={d:i for i,d in enumerate(dets)}; n=len(dets)
def apply(op,det):
    d=list(det);sg=1
    for typ,i in reversed(op):
        if typ=='a':
            if i not in d: return 0,None
            pos=d.index(i);sg*=(-1)**pos;d.pop(pos)
        else:
            if i in d: return 0,None
            pos=sum(1 for x in d if x<i);sg*=(-1)**pos;d.insert(pos,i)
    return sg,tuple(d)
H2=np.zeros((n,n),complex);HL=np.zeros((n,n))
for j,dt in enumerate(dets):
    for p in range(10):
        sg,nd=apply([('c',p),('a',p)],dt)
        if sg: HL[idx[nd],j]+=h[p//2,p//2]
    for p in range(10):
     for q in range(10):
      for r in range(10):
       for s_ in range(10):
        if p%2!=r%2 or q%2!=s_%2: continue
        v=G[p//2,q//2,r//2,s_//2]
        if abs(v)<1e-12: continue
        sg,nd=apply([('c',p),('c',q),('a',s_),('a',r)],dt)
        if sg: H2[idx[nd],j]+=0.5*v*sg
Sz=np.array([sum(0.5 if i%2==0 else -0.5 for i in d) for d in dets])
sel=[i for i in range(n) if abs(Sz[i]-0.5)<1e-9]  # Sz=1/2 contains S=1/2 and 3/2
Hs2=H2[np.ix_(sel,sel)];Hl=HL[np.ix_(sel,sel)]
# spin projection
Sp=np.zeros((n,n))
for j,dt in enumerate(dets):
    for o in range(5):
        sg,nd=apply([('c',2*o),('a',2*o+1)],dt)
        if sg: Sp[idx[nd],j]+=sg
S2=(Sp.T@Sp+np.diag(Sz**2-Sz))[np.ix_(sel,sel)]
def lv(Dq):
    H=Hs2+Dq*Hl
    w,v=np.linalg.eigh((H+H.conj().T)/2)
    s2=np.real(np.einsum('ij,ik,kj->j',v.conj(),S2,v))
    q=w[abs(s2-3.75)<.1].min(); d=w[abs(s2-.75)<.1].min()
    return q-d
for D in (500,1000,1500,2000,3000): print(D,lv(D))
print(brentq(lv,500,3000))
E
python3 a.py