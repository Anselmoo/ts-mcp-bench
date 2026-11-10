import numpy as np, itertools, math
from sympy.physics.wigner import gaunt
C=3699/784
F4=441*C/35; F2=(441+5*F4)/9
Fk={0:0.0,2:F2,4:F4}
ms=list(range(-2,3))
def cmat(m,q,mp,k):
    if m-mp!=q: return 0.0
    return math.sqrt(4*math.pi/(2*k+1))*complex((-1)**m*float(gaunt(2,k,2,-m,q,mp)))
def g(m1,m2,m3,m4):
    return {k:sum((-1)**q*cmat(m1,q,m3,k)*cmat(m2,-q,m4,k) for q in range(-k,k+1)) for k in (0,2,4)}
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
r2=math.sqrt(2)
orbs=[(6,vec({0:1})),(6,vec({2:1/r2,-2:1/r2})),(-4,vec({2:1/(1j*r2),-2:-1/(1j*r2)})),(-4,vec({1:-1/r2,-1:1/r2})),(-4,vec({1:1j/r2,-1:1j/r2}))]
h=sum(e*np.outer(v,v.conj()) for e,v in orbs)
print("h diag in m basis", np.round(np.diag(h).real,3))
spin=[(m,s) for m in ms for s in (1,-1)]
n=10
dets=list(itertools.combinations(range(n),7)); idx={d:i for i,d in enumerate(dets)}
def app(det,ops):
    occ=list(det); sign=1
    for typ,i in ops:
        if typ=='a':
            if i not in occ: return None,0
            p=occ.index(i); sign*=(-1)**p; occ.pop(p)
        else:
            if i in occ: return None,0
            p=sum(1 for x in occ if x<i); sign*=(-1)**p; occ.insert(p,i)
    return tuple(occ),sign
N=len(dets)
Hcf=np.zeros((N,N),complex)
for a in range(n):
  for b in range(n):
    if spin[a][1]!=spin[b][1]: continue
    hv=h[spin[a][0]+2,spin[b][0]+2]
    if abs(hv)<1e-12: continue
    for j,d in enumerate(dets):
        new,s=app(d,[('c',a),('a',b)])
        if new is not None: Hcf[idx[new],j]+=hv*s
Sz=np.array([sum(0.5*spin[i][1] for i in d) for d in dets])
quart=np.where(np.isclose(Sz,1.5))[0]
print("Hcf quartet-sector eig", np.round(np.linalg.eigvalsh(Hcf[np.ix_(quart,quart)].real),3))
print("trace", np.trace(Hcf[np.ix_(quart,quart)]).real)
