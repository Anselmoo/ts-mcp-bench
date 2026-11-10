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
N=len(states); ops1=[]; ops2=[]
for j,occ in enumerate(states):
    for a in range(10):
        for b in range(10):
            if a%2!=b%2: continue
            r=apply_ops(occ,[('a',a),('c',b)])
            if r: ops1.append((idx[r[1]],j,r[0],a//2,b//2))
    for a,b,c,d in itertools.product(range(10),repeat=4):
        if a%2!=d%2 or b%2!=c%2: continue
        r=apply_ops(occ,[('a',a),('a',b),('c',d),('c',c)])
        if r: ops2.append((idx[r[1]],j,r[0],a//2,b//2,c//2,d//2))
def build(Dq,Bv,Cv):
    F={2:49*Bv+7*Cv,4:441*Cv/35}
    h=(-4*Dq*Pt+6*Dq*Pe).real
    H=np.zeros((N,N))
    for i,j,sg,p,q in ops1: H[i,j]+=sg*h[p,q]
    for i,j,sg,a,b,c,d in ops2: H[i,j]+=0.5*sg*sum(F[k]*A[k][a,b,c,d] for k in (2,4))
    return H
Sz=lambda occ: sum(0.5 if x%2==0 else -0.5 for x in occ)
Sp=np.zeros((N,N))
for j,occ in enumerate(states):
    for m in range(5):
        r=apply_ops(occ,[('a',2*m),('c',2*m+1)])
        if r: Sp[idx[r[1]],j]+=r[0]
Szd=np.diag([Sz(o) for o in states]); S2=Sp.T@Sp+Szd@Szd+Szd
print('S2 spectrum', sorted(set(np.round(np.linalg.eigvalsh(S2),3))))
def levels(Dq,B=706.,C=2734.):
    H=build(Dq,B,C)
    # block diagonalize in S-sectors: use projection by S2 eigen
    w,v=np.linalg.eigh(H+1e-3*S2)  # tiny shift to separate by S? instead project
    return w,v
def lowest_by_S(Dq,B=706.,C=2734.):
    H=build(Dq,B,C)
    out={}
    for S in [0,1,2]:
        # S(S+1) eigen-subspace
        vals,vecs=np.linalg.eigh(S2)
        P=vecs[:,np.abs(vals-S*(S+1)*1.0)<1e-6] if False else None
        Sv=S*(S+1)
        mask=np.abs(vals-Sv)<1e-6
        V=vecs[:,mask]
        out[S]=np.linalg.eigvalsh(V.T@H@V).min()
    return out
print('Dq=0', lowest_by_S(0.))
def diff(Dq):
    r=lowest_by_S(Dq); return r[2]-r[1]
for Dq in [0,500,1000,2000,3000]: print(Dq, diff(Dq))
