
cd /; cat > /tmp/d4run.py << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.optimize import least_squares
nth,nph=40,80
x,w=np.polynomial.legendre.leggauss(nth)
th=np.arccos(x); ph=np.arange(nph)*2*np.pi/nph
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.full(nph,2*np.pi/nph))
def Y(k,q): return sph_harm_y(k,q,TH,PH)
ms=[-2,-1,0,1,2]
cub=Y(4,0)+np.sqrt(5/14)*(Y(4,4)+Y(4,-4))
Mc=np.array([[np.sum(W*np.conj(Y(2,a))*cub*Y(2,b)) for b in ms] for a in ms]).real
scale=6/np.max(np.linalg.eigvalsh(Mc))   # eg=+6Dq
# spin-orbitals: index = 2*i + s, s=0 up,1 down
N=10
def Ak(k,q):  # A[ma,mc]=∫conj(Y2ma) conj(Ykq) Y2mc
    return np.array([[np.sum(W*np.conj(Y(2,a))*np.conj(Y(k,q))*Y(2,c)) for c in ms] for a in ms])
def Bk(k,q):
    return np.array([[np.sum(W*np.conj(Y(2,b))*Y(k,q)*Y(2,d)) for d in ms] for b in ms])
Ang={}
for k in (2,4):
    Ang[k]=[(4*np.pi/(2*k+1), Ak(k,q), Bk(k,q)) for q in range(-k,k+1)]
def Vspat(k,ma,mb,mc,md):
    i,j,kk,ll=ms.index(ma),ms.index(mb),ms.index(mc),ms.index(md)
    return sum(c*A[i,kk]*B[j,ll] for c,A,B in Ang[k])
def build(Dq,B,C):
    F4=441*C/35; F2=(441*B+5*F4)/9
    F={2:F2,4:F4}
    # basis: 4-electron subsets
    states=[s for s in itertools.combinations(range(N),4)]
    idx={s:i for i,s in enumerate(states)}
    D=len(states)
    H=np.zeros((D,D))
    # one-electron matrix in spin-orbitals
    h=np.zeros((N,N))
    for a in range(N):
        for b in range(N):
            if a%2==b%2:
                h[a,b]=scale*Dq*Mc[a//2,b//2]
    # V_{abcd}=<ab|1/r|cd>, spin-orbital indices
    V=np.zeros((N,N,N,N))
    for a,b,c,d in itertools.product(range(N),repeat=4):
        if a%2!=c%2 or b%2!=d%2: continue
        val=0
        for k in (2,4):
            val+=F[k]*Vspat(k,ms[a//2],ms[b//2],ms[c//2],ms[d//2])
        V[a,b,c,d]=val
    def apply_ops(occ, ops):
        # ops list of (type,i) applied right-to-left; return (sign,newocc) or None
        occ=list(occ); sign=1
        for t,i in reversed(ops):
            if t=='a':   # annihilate
                if i not in occ: return None
                p=occ.index(i); sign*= (-1)**p; occ.pop(p)
            else:        # create
                if i in occ: return None
                p=sum(1 for x in occ if x<i); sign*=(-1)**p; occ.insert(p,i)
        return sign,tuple(sorted(occ))
    for s in states:
        j=idx[s]
        # one-body
        for a in range(N):
            for b in range(N):
                if h[a,b]==0: continue
                r=apply_ops(s,[('c',a),('a',b)])
                if r: H[idx[r[1]],j]+=r[0]*h[a,b]
        # two-body 1/2 sum V_abcd c+a c+b c_d c_c
        for a,b,c,d in itertools.product(range(N),repeat=4):
            if V[a,b,c,d]==0: continue
            r=apply_ops(s,[('c',a),('c',b),('a',d),('a',c)])
            if r: H[idx[r[1]],j]+=0.5*r[0]*V[a,b,c,d]
    # S^2
    Sp=np.zeros((D,D)); Sz=np.zeros(D)
    for s in states:
        j=idx[s]
        for m in range(5):
            r=apply_ops(s,[('c',2*m),('a',2*m+1)])
            if r: Sp[idx[r[1]],j]+=r[0]
        Sz[j]=0.5*sum(1 if x%2==0 else -1 for x in s)
    S2=Sp.T@Sp+np.diag(Sz**2)-np.diag(Sz) if False else None
    Sm=Sp.T
    S2=Sm@Sp+np.diag(Sz*Sz+Sz)  # S-S+ + Sz^2+Sz? S^2 = S-S+ + Sz^2 + Sz
    return H,S2
def triplets(Dq,B,C):
    H,S2=build(Dq,B,C)
    # restrict to triplets: diagonalize H + big*(S2-2)^2
    Hs=H+1e5*(S2-2*np.eye(len(H)))@(S2-2*np.eye(len(H)))
    ev=np.linalg.eigvalsh(Hs)
    # collect eigenvalues with S2 ~ 2 (S=1)
    evals,vecs=np.linalg.eigh(H+1e5*(S2-2*np.eye(len(H)))@(S2-2*np.eye(len(H))))
    res=[]
    for k in range(len(evals)):
        v=vecs[:,k]
        s2=v@S2@v
        if abs(s2-2)<1e-3 and evals[k]<1e4:
            res.append(v@H@v)
    return np.sort(np.array(res))
if __name__=="__main__":
    import sys
    t=triplets(1000,1000,4700)
    print(np.round(t[:12]-t[0],1), len(t))
EOF
python3 /tmp/d4run.py
