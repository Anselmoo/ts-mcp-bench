import numpy as np, itertools
from scipy.special import sph_harm_y
nth,nph=40,80
x,w=np.polynomial.legendre.leggauss(nth)
th=np.arccos(x); ph=np.arange(nph)*2*np.pi/nph
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.full(nph,2*np.pi/nph))
def Y(k,q): return sph_harm_y(k,q,TH,PH)
ms=[-2,-1,0,1,2]
cub=Y(4,0)+np.sqrt(5/14)*(Y(4,4)+Y(4,-4))
Mc=np.array([[np.sum(W*np.conj(Y(2,a))*cub*Y(2,b)) for b in ms] for a in ms]).real
scale=6/np.max(np.linalg.eigvalsh(Mc))
N=10
Ang={}
for k in (2,4):
    L=[]
    for q in range(-k,k+1):
        A=np.array([[np.sum(W*np.conj(Y(2,a))*np.conj(Y(k,q))*Y(2,c)) for c in ms] for a in ms])
        B=np.array([[np.sum(W*np.conj(Y(2,b))*Y(k,q)*Y(2,d)) for d in ms] for b in ms])
        L.append((4*np.pi/(2*k+1),A,B))
    Ang[k]=L
def apply_ops(occ, ops):
    occ=list(occ); sign=1
    for t,i in reversed(ops):
        if t=='a':
            if i not in occ: return None
            p=occ.index(i); sign*=(-1)**p; occ.pop(p)
        else:
            if i in occ: return None
            p=sum(1 for x in occ if x<i); sign*=(-1)**p; occ.insert(p,i)
    return sign,tuple(sorted(occ))
states=list(itertools.combinations(range(N),4)); idx={s:i for i,s in enumerate(states)}; D=len(states)
def build(Dq,B,C):
    F4=441*C/35; F2=(441*B+5*F4)/9; F={2:F2,4:F4}
    h=np.zeros((N,N))
    for a in range(N):
        for b in range(N):
            if a%2==b%2: h[a,b]=scale*Dq*Mc[a//2,b//2]
    V=np.zeros((N,N,N,N))
    for a,b,c,d in itertools.product(range(N),repeat=4):
        if a%2!=c%2 or b%2!=d%2: continue
        i,j,kk,ll=a//2,b//2,c//2,d//2
        V[a,b,c,d]=sum(F[k]*sum(cf*A[i,kk]*Bm[j,ll] for cf,A,Bm in Ang[k]) for k in (2,4))
    H=np.zeros((D,D))
    for s in states:
        j=idx[s]
        for a in range(N):
            for b in range(N):
                if h[a,b]==0: continue
                r=apply_ops(s,[('c',a),('a',b)])
                if r: H[idx[r[1]],j]+=r[0]*h[a,b]
        for a,b,c,d in itertools.product(range(N),repeat=4):
            if V[a,b,c,d]==0: continue
            r=apply_ops(s,[('c',a),('c',b),('a',d),('a',c)])
            if r: H[idx[r[1]],j]+=0.5*r[0]*V[a,b,c,d]
    Sp=np.zeros((D,D)); Sz=np.zeros(D)
    for s in states:
        j=idx[s]
        for m in range(5):
            r=apply_ops(s,[('c',2*m),('a',2*m+1)])
            if r: Sp[idx[r[1]],j]+=r[0]
        Sz[j]=0.5*sum(1 if x%2==0 else -1 for x in s)
    S2=Sp.T@Sp+np.diag(Sz*Sz-Sz)  # S-S+ = S^2 - Sz^2 - Sz  => S^2 = S-S+ + Sz^2+Sz
    S2=Sp.T@Sp+np.diag(Sz*Sz+Sz)
    return H,S2
def spectrum(Dq,B,C):
    H,S2=build(Dq,B,C)
    s2,U=np.linalg.eigh(S2)
    # triplet subspace
    T=U[:,np.abs(s2-2)<1e-6]
    Ht=T.T@H@T
    e=np.linalg.eigvalsh(Ht)
    return e
e=spectrum(1000,1000,4700)
print("S2 check ok; triplet count",len(e))
print(np.round(e-e[0],1))
