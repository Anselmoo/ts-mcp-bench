mkdir -p /w && cat > /w/d5.py << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.optimize import least_squares

ms = [-2,-1,0,1,2]
# spin-orbitals: idx = 2*(mi)+s, s=0 up,1 down
def so(mi,s): return 2*mi+s
NSO=10

# angular integrals via quadrature
xg,wg = np.polynomial.legendre.leggauss(30)
nphi=40
phis = np.arange(nphi)*2*np.pi/nphi
TH,PH = np.meshgrid(np.arccos(xg), phis, indexing='ij')
W = np.outer(wg, np.ones(nphi))*(2*np.pi/nphi)
def Y(l,m): return sph_harm_y(l,m,TH,PH)

Yd = {m:Y(2,m) for m in ms}
def ang(k,a,b,c,d):
    # <a b|1/r12 (k-part angular)|c d>, electron1: a* c ; electron2: b* d
    s=0
    for q in range(-k,k+1):
        Ykq = Y(k,q)
        I1 = np.sum(W*np.conj(Yd[a])*np.conj(Ykq)*Yd[c])
        I2 = np.sum(W*np.conj(Yd[b])*Ykq*Yd[d])
        s += I1*I2
    return 4*np.pi/(2*k+1)*s

A = {k:np.zeros((5,5,5,5),complex) for k in (2,4)}
for k in (2,4):
    for a,b,c,d in itertools.product(range(5),repeat=4):
        A[k][a,b,c,d]=ang(k,ms[a],ms[b],ms[c],ms[d])

# build two-body operators M2, M4 on determinant basis (N=5), restricted to Sz=3/2 (n_up-n_down=3)
def dets_sub():
    out=[]
    for occ in itertools.combinations(range(NSO),5):
        nup=sum(1 for i in occ if i%2==0); ndn=5-nup
        if nup-ndn==3: out.append(occ)
    return out
basis = dets_sub()
index = {d:i for i,d in enumerate(basis)}
D=len(basis)

def apply_ops(ops, occ):
    # ops: list applied right-to-left order given as sequence of (type,orb) in order of application
    occ=list(occ); sign=1
    for typ,o in ops:
        n_less = sum(1 for x in occ if x<o)
        if typ=='a':
            if o not in occ: return None,0
            sign *= (-1)**n_less; occ.remove(o)
        else:
            if o in occ: return None,0
            sign *= (-1)**n_less; occ.append(o); occ.sort()
    return tuple(occ), sign

def build(Vfun):
    M=np.zeros((D,D),complex)
    for col,occ in enumerate(basis):
        for i in range(NSO):
            for j in range(NSO):
                for k in range(NSO):
                    for l in range(NSO):
                        mi,si=divmod(i,2); mj,sj=divmod(j,2)
                        mk,sk=divmod(k,2); ml,sl=divmod(l,2)
                        if si!=sk or sj!=sl: continue
                        v=Vfun(mi,mj,mk,ml)
                        if v==0: continue
                        # a†_i a†_j a_l a_k
                        new,sg=apply_ops([('a',k),('a',l),('c',j),('c',i)],occ)
                        if new is None: continue
                        if new not in index: continue
                        M[index[new],col]+=0.5*v*sg
    return M

M2 = build(lambda a,b,c,d: F2unit(a,b,c,d)) if False else None
def mk(k):
    return build(lambda a,b,c,d: A[k][a,b,c,d])
M2=mk(2); M4=mk(4)
print("hermitian check", np.allclose(M2,M2.conj().T), np.allclose(M4,M4.conj().T))

# cubic one-body: W = -4 I + 10 P_eg ; P_eg = |Y20><Y20| + |e><e|, e=(Y22+Y2-2)/sqrt2
vec20 = np.zeros(5,complex); vec20[ms.index(0)]=1
vece = np.zeros(5,complex); vece[ms.index(2)]=1/np.sqrt(2); vece[ms.index(-2)]=1/np.sqrt(2)
Peg = np.outer(vec20,vec20.conj())+np.outer(vece,vece.conj())
Wcub = -4*np.eye(5)+10*Peg
H1 = np.zeros((D,D),complex)
for col,occ in enumerate(basis):
    for i in range(NSO):
        for j in range(NSO):
            mi,si=divmod(i,2); mj,sj=divmod(j,2)
            if si!=sj: continue
            v=Wcub[mi,mj]
            if abs(v)<1e-14: continue
            new,sg=apply_ops([('a',j),('c',i)],occ)
            if new is None or new not in index: continue
            H1[index[new],col]+=v*sg

def spectrum(Dq,F2,F4):
    H = H1*Dq + F2*M2 + F4*M4
    return np.linalg.eigvalsh(H)

np.save('/w/ops.npy', np.stack([H1,M2,M4]))
# free ion check: energies relative to sextet, Dq=0
Bt,Ct=1000.,4000.
F4=441*Ct/35; F2=49*Bt+7*Ct
ev=spectrum(0,F2,F4)
print("free ion levels (rel to lowest):", np.round(ev-ev[0],1)[:30])
EOF
cd /w && python3 d5.py