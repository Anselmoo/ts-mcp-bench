mkdir -p <SANDBOX_TMP>/ts && cd <SANDBOX_TMP>/ts && cat > ts.py << 'EOF'
import itertools, numpy as np
from scipy.special import sph_harm_y
from collections import Counter

C = 3660/859
B = 1.0
F4 = 441*C/35
F2 = (441*B + 5*F4)/9
Fk = {0: 0.0, 2: F2, 4: F4}

polys = [lambda x,y,z: 2*z*z-x*x-y*y,
         lambda x,y,z: x*x-y*y,
         lambda x,y,z: x*y,
         lambda x,y,z: x*z,
         lambda x,y,z: y*z]
def sph_pts(nth=24, nph=48):
    xg, wg = np.polynomial.legendre.leggauss(nth)
    ph = np.arange(nph)*2*np.pi/nph
    pts, w = [], []
    for ct, wt in zip(xg, wg):
        st = np.sqrt(1-ct*ct)
        for p in ph:
            pts.append([st*np.cos(p), st*np.sin(p), ct]); w.append(wt*2*np.pi/nph)
    return np.array(pts), np.array(w)
P, W = sph_pts()
X, Y, Z = P.T
raw = np.array([f(X,Y,Z) for f in polys]).T
norms = np.sqrt((raw**2 * W[:,None]).sum(0))
def psi(pts):
    x,y,z = pts.T
    return np.array([f(x,y,z) for f in polys]).T / norms
Psi = psi(P)
G = (Psi*W[:,None]).T @ Psi
assert np.allclose(G, np.eye(5), atol=1e-10)

ang = {}
th = np.arccos(np.clip(Z,-1,1)); ph = np.arctan2(Y,X)
for k in (0,2,4):
    qs = list(range(-k,k+1))
    A = np.zeros((5,5,len(qs)),dtype=complex)
    for iq,q in enumerate(qs):
        Yk = sph_harm_y(k, q, th, ph)
        A[:,:,iq] = np.einsum('pa,p,pc->ac', Psi, W*np.conj(Yk), Psi)
    ang[k] = (qs, A)
def ak(k,a,b,c,d):
    qs, A = ang[k]
    s = 0
    for iq,q in enumerate(qs):
        s += A[a,c,iq] * np.conj(A[b,d,iq])
    return (4*np.pi/(2*k+1))*s
Vr = np.zeros((5,5,5,5))
for a,b,c,d in itertools.product(range(5),repeat=4):
    v = 0
    for k in (2,4):
        v += Fk[k]*ak(k,a,b,c,d)
    Vr[a,b,c,d] = v.real
NSO = 10
Vso = np.zeros((NSO,)*4)
for i,j,k,l in itertools.product(range(NSO),repeat=4):
    ai,si = divmod(i,2); aj,sj = divmod(j,2); ak_,sk = divmod(k,2); al,sl = divmod(l,2)
    if si==sk and sj==sl:
        Vso[i,j,k,l] = Vr[ai,aj,ak_,al]

dets = []
for occ in itertools.combinations(range(NSO),7):
    m = 0
    for o in occ: m |= 1<<o
    dets.append(m)
dets = sorted(dets)
idx_of = {m:i for i,m in enumerate(dets)}
ND = len(dets)
def occ_list(m): return [i for i in range(NSO) if (m>>i)&1]
def par(m,j): return (-1)**bin(m & ((1<<j)-1)).count('1')

def one_body(h):
    M = np.zeros((ND,ND))
    for n,m in enumerate(dets):
        for i in range(NSO):
            for j in range(NSO):
                if h[i,j]==0 or not (m>>j)&1: continue
                s = par(m,j); m2 = m ^ (1<<j)
                if (m2>>i)&1: continue
                s *= par(m2,i); m3 = m2 | (1<<i)
                M[idx_of[m3], n] += s*h[i,j]
    return M

def two_body(V):
    M = np.zeros((ND,ND))
    nz = [(i,j,k,l) for i,j,k,l in itertools.product(range(NSO),repeat=4) if V[i,j,k,l]!=0]
    for n,m in enumerate(dets):
        for (i,j,k,l) in nz:
            if not (m>>k)&1: continue
            s = par(m,k); mm = m ^ (1<<k)
            if not (mm>>l)&1: continue
            s *= par(mm,l); mm ^= 1<<l
            if (mm>>j)&1: continue
            s *= par(mm,j); mm |= 1<<j
            if (mm>>i)&1: continue
            s *= par(mm,i); mm |= 1<<i
            M[idx_of[mm], n] += 0.5*s*V[i,j,k,l]
    return M

Hee = two_body(Vso)
ecf = np.array([6,6,-4,-4,-4.0])
Hcf = one_body(np.diag([ecf[i//2] for i in range(NSO)]))

Ep = np.zeros((NSO,NSO)); Em = np.zeros((NSO,NSO)); Sz1 = np.zeros((NSO,NSO))
for a in range(5):
    Ep[2*a, 2*a+1] = 1
    Em[2*a+1, 2*a] = 1
    Sz1[2*a,2*a] = 0.5; Sz1[2*a+1,2*a+1] = -0.5
Sp = one_body(Ep); Sm = one_body(Em); Sz = one_body(Sz1)
S2 = Sm@Sp + Sz@Sz + Sz

def rot(axis, th):
    axis = np.array(axis,float); axis/=np.linalg.norm(axis)
    K = np.array([[0,-axis[2],axis[1]],[axis[2],0,-axis[0]],[-axis[1],axis[0],0]])
    return np.eye(3)+np.sin(th)*K+(1-np.cos(th))*K@K
PS = P[::7]; PsiS = psi(PS)
def Dmat(R):
    D, *_ = np.linalg.lstsq(PsiS, psi(PS @ R.T), rcond=None)
    return D
hh = 1e-5
Gs = [(Dmat(rot(ax,hh))-Dmat(rot(ax,-hh)))/(2*hh) for ax in ([1,0,0],[0,1,0],[0,0,1])]
Lr = [one_body(np.kron(G, np.eye(2))) for G in Gs]
L2 = -(Lr[0]@Lr[0]+Lr[1]@Lr[1]+Lr[2]@Lr[2])

C4 = np.array([[0,-1,0],[1,0,0],[0,0,1.]])
C3 = np.array([[0,0,1],[1,0,0],[0,1,0.]])
els = [np.eye(3)]
changed=True
while changed:
    changed=False
    for g in list(els):
        for h in (C4,C3):
            n = g@h
            if not any(np.allclose(n,e) for e in els):
                els.append(n); changed=True
assert len(els)==24, len(els)
def cls(R):
    t = np.trace(R)
    if np.allclose(R,np.eye(3)): return 'E'
    if abs(t)<1e-9: return 'C3'
    if abs(t-1)<1e-9: return 'C4'
    if abs(t+1)<1e-9:
        return 'C2' if np.allclose(R, np.diag(np.diag(R))) else "C2'"
classes = [cls(R) for R in els]
order = ['E','C3','C2','C4',"C2'"]
irreps = {'A1':[1,1,1,1,1],'A2':[1,1,1,-1,-1],'E':[2,-1,2,0,0],'T1':[3,0,-1,1,-1],'T2':[3,0,-1,-1,1]}
dimI = {'A1':1,'A2':1,'E':2,'T1':3,'T2':3}

def many_body(D):
    W1 = np.kron(D, np.eye(2))
    Sl = np.array([occ_list(m) for m in dets])
    sub = W1[Sl[:,None,:,None], Sl[None,:,None,:]]
    return np.linalg.det(sub)
Us = [many_body(Dmat(R)) for R in els]
EOF
python3 -c "
exec(open('ts.py').read())
print(Counter(classes))
print('F2,F4',F2,F4)
print('S2 eig', np.unique(np.round(np.linalg.eigvalsh(S2),6)))
print('L2 eig', np.unique(np.round(np.linalg.eigvalsh(L2),6)))
H0 = Hee
print('Hee sym', np.allclose(Hee,Hee.T), 'commutes S2', np.allclose(H0@S2,S2@H0), 'commutes L2', np.allclose(H0@L2,L2@H0))
# homomorphism check
for i in range(24):
  for j in range(24):
    R = els[i]@els[j]
    k = [t for t in range(24) if np.allclose(els[t],R)][0]
    if not np.allclose(Us[i]@Us[j], Us[k]): print('not hom', i,j); raise SystemExit
print('hom ok')
"