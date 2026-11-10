
mkdir -p ~/w && cd ~/w && cat << 'EOF' > d3.py
import numpy as np, itertools
from scipy.special import eval_legendre
from scipy.optimize import least_squares
nt, nphi = 30, 60
xg, wg = np.polynomial.legendre.leggauss(nt)
phis = np.arange(nphi)*2*np.pi/nphi
ct, ph = np.meshgrid(xg, phis, indexing='ij')
W = (np.outer(wg, np.ones(nphi))*(2*np.pi/nphi)).ravel()
st = np.sqrt(1-ct**2)
X=(st*np.cos(ph)).ravel(); Y=(st*np.sin(ph)).ravel(); Z=ct.ravel()
funcs=[X*Y,Y*Z,Z*X,X**2-Y**2,3*Z**2-(X**2+Y**2)]
orbs=np.array([f/np.sqrt(np.sum(W*f*f)) for f in funcs])
cg=np.clip(np.outer(X,X)+np.outer(Y,Y)+np.outer(Z,Z),-1,1)
rho=np.einsum('ip,kp->ikp',orbs,orbs)
def ang(k):
    P=eval_legendre(k,cg)
    R=np.einsum('ikp,pq,q->ikq',rho,P,W)
    return np.einsum('ikq,jlq->ikjl',R,rho)
A0,A2,A4=ang(0),ang(2),ang(4)
print("a0 check", A0[0,0,0,0], A0[3,3,3,3])
n=10
def ops():
    dim=2**n
    cr=[]
    for p in range(n):
        M=np.zeros((dim,dim))
        for s in range(dim):
            if not (s>>p)&1:
                sign=(-1)**bin(s&((1<<p)-1)).count('1')
                M[s|(1<<p),s]=sign
        cr.append(M)
    return cr
CR=ops(); AN=[m.T for m in CR]
dim=2**n
Nop=sum(CR[p]@AN[p] for p in range(n))
idx=[i for i in range(dim) if round(Nop[i,i])==3]
cr=[m[np.ix_(idx,idx)] for m in CR]; an=[m.T for m in cr]
# note: restriction of c† maps N=3 to N=4 ; restrict properly
def sub(M): return M[np.ix_(idx,idx)]
# Build operators on N=3 subspace as products
def build(Dq,B,C):
    F2=49*B+7*C; F4=63*C/5
    Vt=F2*A2+F4*A4          # (ij|kl) in orbital chemist notation, F0 term omitted (constant for d3)
    h=np.zeros((n,n))
    eps=[-4*Dq]*3+[6*Dq]*2
    for o in range(5):
        for s in range(2): h[2*o+s,2*o+s]=eps[o]
    H=np.zeros((len(idx),len(idx)))
    CRs=[ (CR[p]) for p in range(n)]
    ANs=[AN[p] for p in range(n)]
    Hf=np.zeros((dim,dim))
    for p in range(n):
        for q in range(n):
            if h[p,q]: Hf+=h[p,q]*CRs[p]@ANs[q]
    # two-body: 1/2 sum V_{pqrs} c_p^+ c_q^+ c_s c_r with spin-conserving
    for i,j,k,l in itertools.product(range(5),repeat=4):
        v=Vt[i,j,k,l]
        if abs(v)<1e-13: continue
        for s1 in range(2):
            for s2 in range(2):
                p=2*i+s1; q=2*k+s2; r=2*j+s1; s=2*l+s2
                # <ij|kl>: electron1 i->j? use term 1/2 sum (ij|kl) a+_i a+_k a_l a_j with spin i~j, k~l
                Hf+=0.5*v*CRs[p]@CRs[q]@ANs[s]@ANs[r]
    return Hf[np.ix_(idx,idx)]
def spectrum(Dq,B,C):
    H=build(Dq,B,C)
    # S^2 on subspace
    Sp=sum(CR[2*o]@AN[2*o+1] for o in range(5))
    Sm=Sp.T
    Sz=0.5*sum(CR[2*o]@AN[2*o]-CR[2*o+1]@AN[2*o+1] for o in range(5))
    S2=(Sm@Sp+Sz@Sz+Sz)[np.ix_(idx,idx)]
    # diagonalize H in basis; separate by S2 eigenvalue
    E,V=np.linalg.eigh(H+1e-0*0)
    out=[]
    for e,v in zip(E,V.T):
        s2=v@S2@v
        out.append((round(e,3), round(s2,3)))
    return out
if __name__=="__main__":
    for x in spectrum(1000.,600.,2400.): print(x)
EOF
python3 d3.py
