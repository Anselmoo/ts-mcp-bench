import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
l=2
ms=[-2,-1,0,1,2]
_gc={}
def G(k,ma,q,mc):
    key=(k,ma,q,mc)
    if key not in _gc:
        _gc[key]=float(gaunt(l,k,l,-ma,q,mc)) if abs(q)<=k and (-ma+q-mc)==0 else 0.0
    return _gc[key]
def ang(k,a,b,c,d):
    # a,b,c,d are m values; conservation a+b=c+d
    if a+b!=c+d: return 0.0
    s=0.0
    for q in range(-k,k+1):
        s+=((-1)**(a+q))*G(k,a,-q,c)*((-1)**b)*G(k,b,q,d)
    return 4*np.pi/(2*k+1)*s
A={}
for k in (2,4):
    T=np.zeros((5,5,5,5))
    for a,b,c,d in itertools.product(range(5),repeat=4):
        T[a,b,c,d]=ang(k,ms[a],ms[b],ms[c],ms[d])
    A[k]=T
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[ms.index(m)]=c
    return v
s2=np.sqrt(2)
t2g=[vec({2:1/(1j*s2),-2:-1/(1j*s2)}), vec({1:1/s2,-1:-1/s2}), vec({1:1/(1j*s2),-1:1/(1j*s2)})]
eg=[vec({0:1}), vec({2:1/s2,-2:1/s2})]
Pt=sum(np.outer(v,v.conj()) for v in t2g)
Pe=sum(np.outer(v,v.conj()) for v in eg)
states=list(itertools.combinations(range(10),4))
idx={s:i for i,s in enumerate(states)}
def apply_ops(occ,ops):
    occ=list(occ); sign=1
    for t,i in reversed(ops):
        if t=='c':
            if i not in occ: return None
            p=occ.index(i); sign*=(-1)**p; occ.pop(p)
        else:
            if i in occ: return None
            p=sum(1 for x in occ if x<i); sign*=(-1)**p; occ.insert(p,i)
    return sign,tuple(occ)
def build(Dq,Bv,Cv):
    F={2:49*Bv+7*Cv,4:441*Cv/35}
    h=-4*Dq*Pt+6*Dq*Pe
    N=len(states); H=np.zeros((N,N),complex)
    for j,occ in enumerate(states):
        for a in range(10):
            for b in range(10):
                if a%2!=b%2: continue
                hv=h[a//2,b//2]
                if abs(hv)<1e-12: continue
                r=apply_ops(occ,[('c',a),('a',b)])
                if r is None: continue
                sg,new=r; H[idx[tuple(sorted(new))],j]+=sg*hv
        for a in range(10):
          for b in range(10):
            for c in range(10):
              for d in range(10):
                if a%2!=d%2 or b%2!=c%2: continue
                val=sum(F[k]*A[k][a//2,b//2,c//2,d//2] for k in (2,4))
                if abs(val)<1e-12: continue
                r=apply_ops(occ,[('c',a),('c',b),('a',d),('a',c)])
                if r is None: continue
                sg,new=r; H[idx[tuple(sorted(new))],j]+=0.5*sg*val
    return H.real
def Sz(occ): return sum(0.5 if x%2==0 else -0.5 for x in occ)
N=len(states)
Sp=np.zeros((N,N))
for j,occ in enumerate(states):
    for m in range(5):
        r=apply_ops(occ,[('c',2*m),('a',2*m+1)])
        if r: sg,new=r; Sp[idx[tuple(sorted(new))],j]+=sg
Szd=np.diag([Sz(o) for o in states])
S2=Sp.T@Sp+Szd@Szd-Szd   # S^2 = S-S+ + Sz^2 - Sz? check below
