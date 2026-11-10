cat > d5.py << 'EOF'
import numpy as np, itertools
from numpy.polynomial.legendre import leggauss
from scipy.special import eval_legendre
x,wx = leggauss(24); M=48
phi = np.arange(M)*2*np.pi/M; wphi = np.full(M,2*np.pi/M)
ct,ph = np.meshgrid(x,phi,indexing='ij'); W = np.outer(wx,wphi).ravel()
st=np.sqrt(1-ct**2)
X=(st*np.cos(ph)).ravel(); Y=(st*np.sin(ph)).ravel(); Z=ct.ravel()
s5=np.sqrt(5/(16*np.pi)); s15=np.sqrt(15/(4*np.pi)); s15b=np.sqrt(15/(16*np.pi))
Phi = np.array([s15*X*Y, s15*Y*Z, s15*X*Z, s5*(3*Z**2-1), s15b*(X**2-Y**2)])
print("norm", np.round((Phi*W)@Phi.T,6).diagonal())
dot = np.outer(X,X)+np.outer(Y,Y)+np.outer(Z,Z)
P={k:eval_legendre(k,np.clip(dot,-1,1)) for k in (0,2,4)}
G = np.einsum('ip,kp->ikp',Phi,Phi)
Ak={}
for k in (0,2,4):
    T = np.einsum('ikp,p,pq->ikq',G,W,P[k])
    Ak[k]= np.einsum('ikq,jlq,q->ikjl',T,G,W)
nso=10
def spin(p): return p%2
def orb(p): return p//2
def build(Dq,B,ratio=4.4):
    C=ratio*B
    F4 = 441*C/35; F2=(441*B+5*F4)/9
    F={0:0.0,2:F2,4:F4}
    h=np.zeros(nso)
    for p in range(nso):
        h[p] = 6*Dq if orb(p)>=3 else -4*Dq
    V=np.zeros((nso,)*4)
    for i,j,k,l in itertools.product(range(nso),repeat=4):
        if spin(i)!=spin(k) or spin(j)!=spin(l): continue
        V[i,j,k,l]=sum(F[kk]*Ak[kk][orb(i),orb(k),orb(j),orb(l)] for kk in (0,2,4))
    dets=[sum(1<<p for p in c) for c in itertools.combinations(range(nso),5)]
    idx={d:n for n,d in enumerate(dets)}
    H=np.zeros((len(dets),)*2)
    def cdag_c(i,j,occ):
        if not (occ>>j)&1: return None,0
        s=bin(occ & ((1<<j)-1)).count('1'); occ2=occ & ~(1<<j)
        if (occ2>>i)&1: return None,0
        s+=bin(occ2 & ((1<<i)-1)).count('1'); occ2|=(1<<i)
        return occ2, (-1)**s
    nz=[(i,j,V[i,j,k,l],k,l) for i,j,k,l in itertools.product(range(nso),repeat=4) if V[i,j,k,l]!=0]
    for n,d in enumerate(dets):
        for i in range(nso):
            o2,sg=cdag_c(i,i,d)
            if o2 is not None: H[idx[o2],n]+=sg*h[i]
        for i,j,v,k,l in nz:
            o=d; sg=1; ok=True
            for kind,p in ((0,k),(0,l),(1,j),(1,i)):
                if kind==0:
                    if not (o>>p)&1: ok=False;break
                    sg*=(-1)**bin(o&((1<<p)-1)).count('1'); o&=~(1<<p)
                else:
                    if (o>>p)&1: ok=False;break
                    sg*=(-1)**bin(o&((1<<p)-1)).count('1'); o|=(1<<p)
            if ok: H[idx[o],n]+=0.5*sg*v
    Sz=np.zeros_like(H); Sp=np.zeros_like(H)
    for n,d in enumerate(dets):
        Sz[n,n]=0.5*sum((1 if spin(p)==0 else -1) for p in range(nso) if (d>>p)&1)
        for p in range(0,nso,2):
            o2,sg=cdag_c(p,p+1,d)
            if o2 is not None: Sp[idx[o2],n]+=sg
    S2=Sp.T@Sp+Sz@Sz+Sz
    return H,S2
EOF
python3 -c "
import d5,numpy as np
H,S2=d5.build(1000.,1000.)
print(H.shape, np.allclose(H,H.T), np.allclose(S2,S2.T))
w,v=np.linalg.eigh(H+1e6*S2)
print(np.round(w[:30]))
"