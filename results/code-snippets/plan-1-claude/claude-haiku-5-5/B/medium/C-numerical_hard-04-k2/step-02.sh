mkdir -p /w && cat > /w/d5.py << 'EOF'
import numpy as np, itertools
from numpy.polynomial.legendre import leggauss
from scipy.optimize import brentq, least_squares
# angular grid
x,wx = leggauss(24); M=48
phi = np.arange(M)*2*np.pi/M; wphi = np.full(M,2*np.pi/M)
ct,ph = np.meshgrid(x,phi,indexing='ij'); W = np.outer(wx,wphi).ravel()
st=np.sqrt(1-ct**2)
X=(st*np.cos(ph)).ravel(); Y=(st*np.sin(ph)).ravel(); Z=ct.ravel()
s5=np.sqrt(5/(16*np.pi)); s15=np.sqrt(15/(4*np.pi)); s15b=np.sqrt(15/(16*np.pi))
# real d orbitals: 0 xy,1 yz,2 zx (t2g); 3 z2, 4 x2-y2 (eg)
Phi = np.array([s15*X*Y, s15*Y*Z, s15*X*Z, s5*(3*Z**2-1), s15b*(X**2-Y**2)])
# check normalization
print("norm", np.round(Phi@np.diag(W)@Phi.T,6))
N=len(W)
P = {}
dot = np.outer(X,X)+np.outer(Y,Y)+np.outer(Z,Z)
from scipy.special import eval_legendre
for k in (0,2,4):
    P[k]=eval_legendre(k,np.clip(dot,-1,1))
# A_k[i,k,j,l] = sum_pq W_p W_q Phi_i Phi_k (p) Phi_j Phi_l (q) P_k(p.q)
Ak={}
for k in (0,2,4):
    G = np.einsum('ip,p,kp->ikp',Phi,W,Phi)  # pair (i,k) at point p
    Ak[k]=np.einsum('ikp,pq,jlq->ikjl',G,P[k]*1.0,np.einsum('ip,p,kp->ikp',Phi,W,Phi)*0+G) if False else None
# simpler explicit:
G = np.einsum('ip,kp->ikp',Phi,Phi)  # no weight
for k in (0,2,4):
    T = np.einsum('ikp,p,pq->ikq',G,W,P[k])      # sum over p
    Ak[k]= np.einsum('ikq,jlq,q->ikjl',T,G,W)
# spin-orbitals: index p = 2*orb + s
nso=10
def spin(p): return p%2
def orb(p): return p//2
# Slater integrals (F0 arbitrary=0), B,C -> F2,F4
def build(Dq,B,C=None,ratio=4.4):
    if C is None: C=ratio*B
    F4 = 441*C/35; F2=(441*B+5*F4)/9
    F={0:0.0,2:F2,4:F4}
    # one-electron
    h=np.zeros((nso,nso))
    for p in range(nso):
        o=orb(p)
        h[p,p] = 6*Dq if o>=3 else -4*Dq
    # two-electron V_ijkl=<ij|V|kl>
    V=np.zeros((nso,)*4)
    for i,j,k,l in itertools.product(range(nso),repeat=4):
        if spin(i)!=spin(k) or spin(j)!=spin(l): continue
        V[i,j,k,l]=sum(F[kk]*Ak[kk][orb(i),orb(k),orb(j),orb(l)] for kk in (0,2,4))
    # determinants
    dets=[sum(1<<p for p in c) for c in itertools.combinations(range(nso),5)]
    idx={d:n for n,d in enumerate(dets)}
    H=np.zeros((len(dets),)*2)
    def apply_cdag_c(i,j,occ):  # c_i^dag c_j
        if not (occ>>j)&1: return None,0
        s=bin(occ & ((1<<j)-1)).count('1'); occ2=occ & ~(1<<j)
        if (occ2>>i)&1: return None,0
        s+=bin(occ2 & ((1<<i)-1)).count('1'); occ2|=(1<<i)
        return occ2, (-1)**s
    for n,d in enumerate(dets):
        for i in range(nso):
            for j in range(nso):
                if h[i,j]!=0 or i==j:
                    if h[i,j]==0: continue
                    o2,sg=apply_cdag_c(i,j,d)
                    if o2 is not None: H[idx[o2],n]+=sg*h[i,j]
        for i,j,k,l in itertools.product(range(nso),repeat=4):
            v=V[i,j,k,l]
            if v==0: continue
            # c_i^dag c_j^dag c_l c_k
            o=d; sg=1; ok=True
            for op,p in ((False,k),(False,l),(True,j),(True,i)):
                if op==False:
                    if not (o>>p)&1: ok=False;break
                    sg*= (-1)**bin(o&((1<<p)-1)).count('1'); o&=~(1<<p)
                else:
                    if (o>>p)&1: ok=False;break
                    sg*= (-1)**bin(o&((1<<p)-1)).count('1'); o|=(1<<p)
            if ok: H[idx[o],n]+=0.5*sg*v
    # S^2
    Sz=np.zeros_like(H); Sp=np.zeros_like(H)
    for n,d in enumerate(dets):
        Sz[n,n]=0.5*sum((1 if spin(p)==0 else -1) for p in range(nso) if (d>>p)&1)
        for p in range(0,nso,2):
            # c_{p+1 spin down}^dag ... S+ = sum c_up^dag c_down
            o2,sg=apply_cdag_c(p,p+1,d)
            if o2 is not None: Sp[idx[o2],n]+=sg
    Sm=Sp.T
    S2=Sm@Sp+Sz@Sz+Sz
    return H,S2,dets
EOF
cd /w && python3 -c "
import d5
H,S2,dets=d5.build(1000.,1000.)
print(H.shape, np.allclose(H,H.T))
"