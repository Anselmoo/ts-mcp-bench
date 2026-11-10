import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
l=2; ms=[-2,-1,0,1,2]
def G(k,ma,q,mc):
    if abs(q)>k or (-ma+q+mc)!=0: return 0.0
    return float(gaunt(l,k,l,-ma,q,mc))
def ang(k,a,b,c,d):
    if a+b!=c+d: return 0.0
    s=0.0
    for q in range(-k,k+1):
        s+=((-1)**(a+q))*G(k,a,-q,c)*((-1)**b)*G(k,b,q,d)
    return 4*np.pi/(2*k+1)*s
A={k:np.array([[[[ang(k,ms[a],ms[b],ms[c],ms[d]) for d in range(5)] for c in range(5)] for b in range(5)] for a in range(5)]) for k in (2,4)}
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[ms.index(m)]=c
    return v
s2=np.sqrt(2)
t2g=[vec({2:1/(1j*s2),-2:-1/(1j*s2)}), vec({1:1/s2,-1:-1/s2}), vec({1:1/(1j*s2),-1:1/(1j*s2)})]
eg=[vec({0:1}), vec({2:1/s2,-2:1/s2})]
Pt=sum(np.outer(v,v.conj()) for v in t2g); Pe=sum(np.outer(v,v.conj()) for v in eg)
states=list(itertools.combinations(range(10),4)); idx={s:i for i,s in enumerate(states)}
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
N=len(states)
# precompute one-body and two-body operator lists (independent of Dq,B,C for two-body per k)
ops1=[]; ops2=[]
for j,occ in enumerate(states):
    for a in range(10):
        for b in range(10):
            if a%2!=b%2: continue
            r=apply_ops(occ,[('a',a),('c',b)])
            if r: ops1.append((j,idx[r[1]],r[0],a//2,b//2))
    for a,b,c,d in itertools.product(range(10),repeat=4):
        if a%2!=d%2 or b%2!=c%2: continue
        r=apply_ops(occ,[('a',a),('a',b),('c',d),('c',c)])
        if r: ops2.append((j,idx[r[1]],r[0],a//2,b//2,c//2,d//2))
def build(Dq,Bv,Cv):
    F={2:49*Bv+7*Cv,4:441*Cv/35}
    h=-4*Dq*Pt+6*Dq*Pe
    H=np.zeros((N,N))
    for j,i,sg,p,q in [(o[0],o[1],o[2],o[3],o[4]) for o in ops1]:
        H[i,j]+=sg*h[p,q].real
    for j,i,sg,a,b,c,d in ops2:
        val=sum(F[k]*A[k][a,b,c,d] for k in (2,4))
        H[i,j]+=0.5*sg*val
    return H
H=build(0,706.,2734.); print('herm', np.abs(H-H.T).max())
Sz=lambda occ: sum(0.5 if x%2==0 else -0.5 for x in occ)
Sp=np.zeros((N,N))
for j,occ in enumerate(states):
    for m in range(5):
        r=apply_ops(occ,[('a',2*m),('c',2*m+1)])
        if r: Sp[idx[r[1]],j]+=r[0]
Szd=np.diag([Sz(o) for o in states]); S2=Sp.T@Sp+Szd@Szd-Szd
def sect(Dq):
    w,v=np.linalg.eigh(build(Dq,706.,2734.))
    s=np.diag(v.T@S2@v)
    out={}
    for e,ss in zip(w,s):
        S=(-1+np.sqrt(1+4*ss))/2
        out.setdefault(round(S*2)/2,[]).append(e)
    return {k:round(min(vv),1) for k,vv in sorted(out.items())}
print('Dq=0',sect(0.))
# free-ion check: d4 5D energy should be 5D lowest, 3H above
# Find crossover: E(S=2 lowest) = E(S=1 lowest)
def diff(Dq):
    r=sect(Dq); return r[2.0]-r[1.0]
for Dq in [0,500,1000,2000,3000]:
    print(Dq, diff(Dq))
x=brentq(diff,500,4000,xtol=1e-6)
print('crossover Dq =',x, 'Dq/B=',x/706)
