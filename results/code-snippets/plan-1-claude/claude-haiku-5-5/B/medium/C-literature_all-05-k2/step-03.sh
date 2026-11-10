cd /tmp; cat > /tmp/run.py << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.optimize import least_squares
# quadrature
xg,wg=np.polynomial.legendre.leggauss(30)
nphi=60
ph=np.arange(nphi)*2*np.pi/nphi
TH=np.arccos(xg)
TT,PP=np.meshgrid(TH,ph,indexing='ij')
W=(np.outer(wg,np.ones(nphi))*(2*np.pi/nphi))
def Y(l,m): return sph_harm_y(l,m,TT,PP)
ms=range(-2,3)
Yd={m:Y(2,m) for m in ms}
def C(k,q,a,c):  # <a|C^k_q|c>, C = sqrt(4pi/(2k+1)) Y_kq
    if abs(q)>k: return 0
    f=np.sqrt(4*np.pi/(2*k+1))
    return np.sum(W*np.conj(Yd[a])*f*Y(k,q)*Yd[c])
# spin-orbitals: index = 2*(m+2)+s  s=0 up,1 down
so=[(m,s) for m in ms for s in (0,1)]
n=len(so)
def Vel(a,b,c,d):  # <ab|V|cd> with a,c orbital m's etc; a,b,c,d are m values
    tot=0
    for k,Fk in [(0,None),(2,'F2'),(4,'F4')]:
        pass
    return None
# Precompute angular parts A_k(a,b,c,d)=sum_q (-1)^q <a|C^k_q|c><b|C^k_-q|d>
A={}
for k in (0,2,4):
    for a in ms:
        for c in ms:
            for b in ms:
                for d in ms:
                    s=0
                    for q in range(-k,k+1):
                        s+= (-1)**q * C(k,q,a,c)*C(k,-q,b,d)
                    A[(k,a,b,c,d)]=s
def run(F2,F4,F0=0.0):
    F={0:F0,2:F2,4:F4}
    h=np.zeros((n,n))
    # Coulomb: V = sum_k F^k A_k ; spin delta
    V=np.zeros((n,n,n,n))
    for i,(ma,sa) in enumerate(so):
     for j,(mb,sb) in enumerate(so):
      for kk,(mc,sc) in enumerate(so):
       for l,(md,sd) in enumerate(so):
        if sa!=sc or sb!=sd: continue
        v=sum(F[k]*A[(k,ma,mb,mc,md)].real for k in (0,2,4))
        V[i,j,kk,l]=v
    return V
def ham(Dq,B,Cc):
    F4=7*Cc/5; F2=49*B+7*Cc
    V=run(F2,F4)
    h=np.zeros((n,n))
    for i,(m,s) in enumerate(so):
        h[i,i]= -4*Dq if m in (-1,1,-2,2) and False else 0
    # projectors: t2g: m=±1, and a=(m2-m-2)/sqrt2 ; eg: m0, b=(m2+m-2)/sqrt2
    P_t=np.zeros((5,5)); P_e=np.zeros((5,5))
    idx={m:i for i,m in enumerate(ms)}
    P_t[idx[1],idx[1]]=1; P_t[idx[-1],idx[-1]]=1
    va=np.zeros(5); va[idx[2]]=1/np.sqrt(2); va[idx[-2]]=-1/np.sqrt(2)
    vb=np.zeros(5); vb[idx[2]]=1/np.sqrt(2); vb[idx[-2]]=1/np.sqrt(2)
    P_t+=np.outer(va,va); P_e[idx[0],idx[0]]=1; P_e+=np.outer(vb,vb)
    Vf=-4*Dq*P_t+6*Dq*P_e
    for i,(m,s) in enumerate(so):
        for j,(m2,s2) in enumerate(so):
            if s==s2: h[i,j]=Vf[idx[m],idx[m2]]
    # full Fock space
    N=n
    dim=2**N
    def ann(p):
        M=np.zeros((dim,dim))
        for st in range(dim):
            if st>>p &1:
                sign=(-1)**bin(st & ((1<<p)-1)).count('1')
                M[st ^ (1<<p), st]=sign
        return M
    cs=[ann(p) for p in range(N)]
    # one-body
    Hf=np.zeros((dim,dim))
    for i in range(N):
        for j in range(N):
            if abs(h[i,j])>1e-12:
                Hf+=h[i,j]*cs[i].T@cs[j]
    # two-body: 1/2 sum V_ijkl c†_i c†_j c_l c_k  with V_ijkl=<ij|V|kl>
    for i in range(N):
     for j in range(N):
      for k_ in range(N):
       for l in range(N):
        v=V[i,j,k_,l]
        if abs(v)>1e-12:
            Hf+=0.5*v*(cs[i].T@cs[j].T@cs[l]@cs[k_])
    # N=3 subspace
    Nop=sum(c.T@c for c in cs)
    diag=np.diag(Nop)
    sel=np.where(np.abs(diag-3)<1e-9)[0]
    Hs=Hf[np.ix_(sel,sel)]
    # S^2 for quartet check: Sz and S+ S-
    Sz=np.zeros(dim)
    Sp=np.zeros((dim,dim))
    Hsz=np.diag([0.5*(sum((1 if (st>>(2*mi+0))&1 else 0)-(1 if (st>>(2*mi+1))&1 else 0) for mi in range(5)))  for st in range(dim)])
    return Hs,sel
if __name__=="__main__":
    import sys
EOF
python3 -c "
exec(open('/tmp/run.py').read())
Hs,sel=ham(0,0,0)
print(Hs.shape, np.round(np.linalg.eigvalsh(Hs),6)[:5])
" 2>&1 | tail -5