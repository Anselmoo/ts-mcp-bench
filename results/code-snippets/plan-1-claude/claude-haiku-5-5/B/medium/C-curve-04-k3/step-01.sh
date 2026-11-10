
cat << 'EOF' > /tmp/d5.py
import numpy as np, itertools
from numpy.polynomial.legendre import leggauss
from scipy.special import eval_legendre

# ---------- angular grid on unit sphere ----------
nt, nph = 60, 120
x, w = leggauss(nt)
ph = np.arange(nph)*2*np.pi/nph
ct, PH = np.meshgrid(x, ph, indexing='ij')
st = np.sqrt(1-ct**2)
P = np.stack([st*np.cos(PH), st*np.sin(PH), ct], -1).reshape(-1,3)
W = (np.repeat(w[:,None], nph, 1)*(2*np.pi/nph)).reshape(-1)

# real d orbitals (unnormalised), basis order: xy,yz,zx,x2-y2,3z2-r2
def forb(p):
    X,Y,Z = p[:,0],p[:,1],p[:,2]
    return np.stack([X*Y, Y*Z, Z*X, X**2-Y**2, 3*Z**2-(X**2+Y**2+Z**2)],1)
F = forb(P)
norm = np.sqrt(np.einsum('k,ki->i', W, F**2))
F = F/norm
# cubic-field one-electron diagonal: t2g (0,1,2) -4Dq ; eg (3,4) +6Dq (in units of Dq)
h1 = np.diag([-4,-4,-4,6,6]).astype(float)

# ---------- group O (rotations) ----------
def Rz(t):
    c,s=np.cos(t),np.sin(t); return np.array([[c,-s,0],[s,c,0],[0,0,1]])
C4 = Rz(np.pi/2)
C3 = np.array([[0,0,1],[1,0,0],[0,1,0]],float)  # (x,y,z)->(z,x,y)
def key(R): return tuple(np.round(R,8).reshape(-1))
G = {key(np.eye(3)):np.eye(3)}
frontier=[np.eye(3)]
while frontier:
    new=[]
    for A in frontier:
        for g in (C4,C3):
            B = g@A
            if key(B) not in G:
                G[key(B)]=B; new.append(B)
    frontier=new
G = list(G.values())
assert len(G)==24, len(G)

def U5(R):
    Fp = forb(P@R)   # f_i(R p)
    # Fp = F @ Ut  -> solve
    Ut,_,_,_ = np.linalg.lstsq(F*np.sqrt(W)[:,None], Fp*np.sqrt(W)[:,None], rcond=None)
    return Ut  # Fp[:,i] = sum_j F[:,j] Ut[j,i]
Us = [U5(R) for R in G]
for U in Us: assert np.allclose(U.T@U, np.eye(5), atol=1e-8)

def char_class(R):
    tr = np.trace(R)
    if np.isclose(tr,3): return 'E'
    if np.isclose(tr,0): return 'C3'
    if np.isclose(tr,-1):
        ev,evec=np.linalg.eig(R); ax=np.real(evec[:,np.argmin(abs(ev-1))])
        ax=ax/np.max(abs(ax))
        return 'C2' if np.sum(np.isclose(abs(ax),0,atol=1e-6))==2 else "C2'"
    if np.isclose(tr,1): return 'C4'
classes=[char_class(R) for R in G]
irreps = {
 'A1':{'E':1,'C3':1,'C2':1,'C4':1,"C2'":1},
 'A2':{'E':1,'C3':1,'C2':1,'C4':-1,"C2'":-1},
 'E': {'E':2,'C3':-1,'C2':2,'C4':0,"C2'":0},
 'T1':{'E':3,'C3':0,'C2':-1,'C4':1,"C2'":-1},
 'T2':{'E':3,'C3':0,'C2':-1,'C4':-1,"C2'":1}}

# ---------- Fock space ----------
N=5; NS=10
states=[sum(1<<i for i in c) for c in itertools.combinations(range(NS),N)]
idx={s:i for i,s in enumerate(states)}
D=len(states)
def sgn(state,i): return (-1)**bin(state & ((1<<i)-1)).count('1')
def ann(i,s):
    if not (s>>i)&1: return None
    return sgn(s,i), s ^ (1<<i)
def cre(i,s):
    if (s>>i)&1: return None
    return sgn(s,i), s | (1<<i)

def onebody(h):
    M=np.zeros((D,D))
    for s in states:
        for a in range(NS):
            for b in range(NS):
                if h[a,b]==0: continue
                r=ann(b,s)
                if r is None: continue
                s1,s1s=r
                r2=cre(a,s1s)
                if r2 is None: continue
                s2,s2s=r2
                M[idx[s2s],idx[s]] += h[a,b]*s1*s2
    return M

# spin-orbital index: orbital i, spin sigma -> 2i+sigma (sigma 0 up,1 down)
h_so=np.zeros((NS,NS))
for i in range(5):
    for sg in range(2):
        h_so[2*i+sg,2*i+sg]=h1[i,i]
Hh = None

# two-electron integrals in orbital basis: a_k[(a,c),(b,d)] = int int phi_a(1)phi_c(1) P_k(1.2) phi_b(2)phi_d(2)
K = {}
cosg = P@P.T
for k in (2,4):
    Kk = eval_legendre(k,cosg)
    K[k]=Kk
Wsq=W
g = {}
ak={}
for k in (2,4):
    A=np.zeros((5,5,5,5))
    for a in range(5):
        for c in range(5):
            v1 = F[:,a]*F[:,c]*W
            for b in range(5):
                for d in range(5):
                    v2 = F[:,b]*F[:,d]
                    A[a,c,b,d]= v1@K[k]@v2
    ak[k]=A
# F0 term ignored (constant). Slater: F2, F4 from Racah B, C (units of B)
Bv=1.0; Cv=3473/800
F4=441*Cv/35*Bv; F2=(441*Bv+5*F4)/9
print("F2,F4 (B units):",F2,F4)
Fk={2:F2,4:F4}
# Two-body operator: 1/2 sum V_{ab,cd} c+_a c+_b c_d c_c with V=<ab|cd>, spins: a~c, b~d
Vso = np.zeros((NS,NS,NS,NS))
for a in range(NS):
    for b in range(NS):
        for c in range(NS):
            for d in range(NS):
                if (a%2)!=(c%2) or (b%2)!=(d%2): continue
                oa,ob,oc,od=a//2,b//2,c//2,d//2
                Vso[a,b,c,d]=sum(Fk[k]*ak[k][oa,oc,ob,od] for k in (2,4))
H2=np.zeros((D,D))
for s in states:
    for a in range(NS):
        for b in range(NS):
            for c in range(NS):
                for d in range(NS):
                    v=Vso[a,b,c,d]
                    if v==0: continue
                    r=ann(c,s)
                    if r is None: continue
                    s1,s1s=r
                    r=ann(d,s1s)
                    if r is None: continue
                    s2,s2s=r
                    r=cre(b,s2s)
                    if r is None: continue
                    s3,s3s=r
                    r=cre(a,s3s)
                    if r is None: continue
                    s4,s4s=r
                    H2[idx[s4s],idx[s]] += 0.5*v*s1*s2*s3*s4
# spin operators
Sp=np.zeros((NS,NS))
for i in range(5): Sp[2*i,2*i+1]=1
Spop=onebody(Sp)
Smop=Spop.T
Sz=np.zeros((NS,NS))
for i in range(5): Sz[2*i,2*i]=0.5; Sz[2*i+1,2*i+1]=-0.5
Szop=onebody(Sz)
S2=Smop@Spop+Szop@Szop+Szop
# Fock representation of group elements
def fock(U):
    M=np.kron(U,np.eye(2))
    Out=np.zeros((D,D))
    for s in states:
        occ=[i for i in range(NS) if (s>>i)&1]
        for T in states:
            tocc=[i for i in range(NS) if (T>>i)&1]
            Out[idx[T],idx[s]] = np.linalg.det(M[np.ix_(tocc,occ)])
    return Out
Hdq = None
def run(Dq):
    H = Dq*onebody(h_so/1.0) if False else None
    H = onebody(np.diag([0]*NS).astype(float))  # placeholder
    H = np.zeros((D,D))
    hd = np.zeros((NS,NS))
    for i in range(5):
        for sg in range(2): hd[2*i+sg,2*i+sg]=h1[i,i]*Dq
    H = onebody(hd) + H2
    return H
EOF
echo ok