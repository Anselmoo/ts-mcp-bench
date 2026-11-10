import numpy as np, itertools
from scipy.optimize import least_squares
# Gauss-Legendre quadrature on sphere
nt, nphi = 40, 80
xg, wg = np.polynomial.legendre.leggauss(nt)
phis = np.arange(nphi)*2*np.pi/nphi
ct, ph = np.meshgrid(xg, phis, indexing='ij')
W = (np.outer(wg, np.ones(nphi))*(2*np.pi/nphi)).ravel()
st = np.sqrt(1-ct**2)
X = (st*np.cos(ph)).ravel(); Y=(st*np.sin(ph)).ravel(); Z=ct.ravel()
# real d orbitals (unnormalized), normalize numerically
funcs = [X*Y, Y*Z, Z*X, X**2-Y**2, 3*Z**2-(X**2+Y**2)]
orbs=[]
for f in funcs:
    n = np.sum(W*f*f); orbs.append(f/np.sqrt(n))
orbs=np.array(orbs)  # 5 x Npts
# cos gamma matrix
cg = np.outer(X,X)+np.outer(Y,Y)+np.outer(Z,Z)
from scipy.special import eval_legendre
Pk = {k: eval_legendre(k, np.clip(cg,-1,1)) for k in (0,2,4)}
# angular coefficients a_k(i,k;j,l) = int int rho_ik(1) rho_jl(2) P_k
rho = np.einsum('p,ip,kp->ikp', W, orbs, orbs)  # W*phi_i*phi_k
def ang(k):
    # A[i,k,j,l]
    M = np.einsum('ikp,pq,jlq->ikjl', rho, Pk[k], np.einsum('q,jq->jq',W, np.ones((1,1))) if False else np.zeros((1,1,1)).reshape(1,1,1)) if False else None
    R = np.einsum('ikp,pq->ikq', rho, Pk[k])
    return np.einsum('ikq,jlq->ikjl', R, rho)
A = {k: ang(k) for k in (0,2,4)}
print("check a0", np.allclose(A[0][0,0,0,0],1), A[0][0,0,0,0])
def build(Dq,B,C):
    F2=49*B+7*C; F4=63*C/5
    V = A[0] + 0  # F0 coefficient set to zero (cancels for energy differences? keep as 0)
    Vt = 0*A[0] + F2*A[2] + F4*A[4]
    # spin orbitals: index 2*o + s
    n=10
    # one-electron
    h=np.zeros((n,n))
    eg_ = [3,4]; t2_=[0,1,2]
    eps = [-4*Dq]*3+[6*Dq]*2
    for o in range(5):
        for s in range(2):
            h[2*o+s,2*o+s]=eps[o]
    # two-electron as 4-index on spin orbitals
    G=np.zeros((n,n,n,n))
    for i,j,k,l in itertools.product(range(5),repeat=4):
        v=Vt[i,j,k,l]  # (ij|kl) orbital chemist notation: rho_ij(1) rho_kl(2)
        if abs(v)<1e-14: continue
        for s1 in range(2):
            for s2 in range(2):
                G[2*i+s1,2*k+s2,2*j+s1,2*l+s2]+=v  # <i k|j l>-like; spin: 1 with 3 ,2 with 4
    # build Fock-space operators via JW
    dim=2**n
    def cr(p):
        M=np.zeros((dim,dim))
        for st_ in range(dim):
            if not (st_>>p)&1:
                sign=(-1)**bin(st_&((1<<p)-1)).count('1')
                M[st_|(1<<p), st_]=sign
        return M
    c=[cr(p) for p in range(n)]
    Hop=np.zeros((dim,dim))
    for p in range(n):
        for q in range(n):
            if h[p,q]!=0: Hop+=h[p,q]*c[p].T@c[q] if False else h[p,q]*(c[p]@c[q].T)
    for p,q,r,s in itertools.product(range(n),repeat=4):
        v=G[p,q,r,s]
        if abs(v)>1e-14:
            Hop+=0.5*v*(c[p]@c[q]@c[s].T@c[r].T)
    # restrict to N=3
    Nop=sum(c[p]@c[p].T for p in range(n))
    idx=[i for i in range(dim) if round(Nop[i,i])==3]
    H=Hop[np.ix_(idx,idx)]
    # S^2
    Sz=np.zeros(n)
    return H, idx
H,idx=build(1000.,600.,2400.)
E=np.linalg.eigvalsh(H)
print(np.round(E[:5],1), len(E))
