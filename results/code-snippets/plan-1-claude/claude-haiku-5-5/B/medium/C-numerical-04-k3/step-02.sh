mkdir -p /tmp/lf && cat > /tmp/lf/d7.py << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import least_squares

# angular grid
xg, wg = np.polynomial.legendre.leggauss(16)
nphi = 32
phis = np.arange(nphi)*2*np.pi/nphi
ct, ph = np.meshgrid(xg, phis, indexing='ij')
W = np.outer(wg, np.ones(nphi))*(2*np.pi/nphi)
th = np.arccos(ct)
def Y(l,m): return sph_harm(m, l, ph, th)   # scipy: sph_harm(m,n,azimuth,polar)
ms = [-2,-1,0,1,2]
Yd = {m: Y(2,m) for m in ms}
def integ(f): return np.sum(W*f)

# cubic field function f = x^4+y^4+z^4 - 3/5 r^4
x = np.sin(th)*np.cos(ph); y=np.sin(th)*np.sin(ph); z=np.cos(th)
f = x**4+y**4+z**4-0.6
Mf = np.array([[integ(np.conj(Yd[a])*f*Yd[b]) for b in ms] for a in ms])
Mf = Mf.real
ev = np.linalg.eigvalsh(Mf)
# ev: t2g (3) low, eg (2) high
t2 = ev[:3]; eg = ev[3:]
a = t2.mean(); b = eg.mean()
alpha = 10.0/(b-a); beta = -4 - alpha*a
Mcf = alpha*Mf + beta*np.eye(5)
print("single-particle eig (Dq units):", np.round(np.linalg.eigvalsh(Mcf),6))

# Coulomb angular tensors
K = [0,2,4]
T = {}
for k in K:
    for q in range(-k,k+1):
        Ykq = Y(k,q)
        Ta = np.array([[integ(np.conj(Yd[a_])*np.conj(Ykq)*Yd[c]) for c in ms] for a_ in ms])
        Tb = np.array([[integ(np.conj(Yd[b_])*Ykq*Yd[d]) for d in ms] for b_ in ms])
        T[(k,q)] = (Ta, Tb)
def Vang(k):
    # V[a,b,c,d] = (4pi/(2k+1)) sum_q Ta[a,c] Tb[b,d]
    V = np.zeros((5,5,5,5),dtype=complex)
    for q in range(-k,k+1):
        Ta,Tb = T[(k,q)]
        V += np.einsum('ac,bd->abcd', Ta, Tb)
    return V*4*np.pi/(2*k+1)
V2 = Vang(2); V4 = Vang(4); V0 = Vang(0)

# spin orbitals: index = 2*orb + s (s=0 up,1 down)
norb = 10
ne = 7
states = [sum(1<<i for i in c) for c in itertools.combinations(range(norb), ne)]
idx = {s:i for i,s in enumerate(states)}
def orbspin(i): return i//2, i%2

def apply_cdag_c(p, q, st):
    # c_p^dag c_q |st>, returns (sign, newstate) or None
    if not (st>>q)&1: return None
    s = st & ~(1<<q)
    sign = (-1)**bin(s & ((1<<q)-1)).count('1')
    if (s>>p)&1: return None
    sign *= (-1)**bin(s & ((1<<p)-1)).count('1')
    return sign, s | (1<<p)

def build(Fk):
    # Fk: dict k->F^k ; Coulomb H = 1/2 sum V_{abcd} c^+_a c^+_b c_d c_c with spin-orbital two-body
    N = len(states); H = np.zeros((N,N))
    # one-body CF
    # two-body: sum over spin-orbital pairs
    Vfull = {}
    Vtot = Fk[0]*V0 + Fk[2]*V2 + Fk[4]*V4
    Vtot = Vtot.real
    for i,st in enumerate(states):
        occ = [j for j in range(norb) if (st>>j)&1]
        # one-body
        for q in occ:
            pass
        # two-body: loop over pairs of occupied spin-orbitals (c,d) to annihilate, and (a,b) created
        for c_ in occ:
            for d_ in occ:
                if c_==d_: continue
                oc, sc = orbspin(c_); od, sd = orbspin(d_)
                # annihilate d then c: c_d c_c applied to st: c_c first? operator c^+_a c^+_b c_d c_c : apply c_c then c_d
                r1 = apply_cdag_c(d_,d_,st)  # placeholder
                s1 = st & ~(1<<c_)
                sg1 = (-1)**bin(st & ((1<<c_)-1)).count('1')
                s2 = s1 & ~(1<<d_)
                sg2 = (-1)**bin(s1 & ((1<<d_)-1)).count('1')
                sg = sg1*sg2
                for a_ in range(norb):
                    for b_ in range(norb):
                        if a_==b_: continue
                        oa, sa = orbspin(a_); ob, sb = orbspin(b_)
                        if sa!=sc or sb!=sd: continue
                        v = Vtot[oa,ob,oc,od]
                        if abs(v)<1e-14: continue
                        if (s2>>b_)&1 or (s2>>a_)&1: continue
                        # create b then a: c^+_a c^+_b : apply c_b^+ first
                        s3 = s2 | (1<<b_); sg3 = (-1)**bin(s2 & ((1<<b_)-1)).count('1')
                        s4 = s3 | (1<<a_); sg4 = (-1)**bin(s3 & ((1<<a_)-1)).count('1')
                        tot = sg*sg3*sg4
                        H[idx[s4], i] += 0.5*v*tot
    return H

def build_cf():
    N=len(states); H=np.zeros((N,N))
    for i,st in enumerate(states):
        for p in range(norb):
            for q in range(norb):
                op, sp = orbspin(p); oq, sq = orbspin(q)
                if sp!=sq: continue
                v = Mcf[op,oq]
                if abs(v)<1e-14: continue
                r = apply_cdag_c(p,q,st)
                if r is None: continue
                sg, ns = r
                H[idx[ns], i] += v*sg
    return H

# total spin S^2
def S2op():
    N=len(states); Sz=np.zeros((N,N)); S2=np.zeros((N,N))
    Sp=np.zeros((N,N))
    for i,st in enumerate(states):
        for m in range(5):
            pu = 2*m; pd = 2*m+1
            # Sz
            nu = (st>>pu)&1; nd=(st>>pd)&1
            Sz[i,i] += 0.5*(nu-nd)
            # S+ = sum c^+_{m,up} c_{m,dn}
            r = apply_cdag_c(pu,pd,st)
            if r is not None:
                sg,ns = r; Sp[idx[ns],i]+=sg
    Sm = Sp.T
    S2 = Sm@Sp + Sz@Sz + Sz
    return S2

S2 = S2op()
Hcf = build_cf()
def energies(Dq,B,ratio=0.625):
    # F2,F4 from B and F4/F2 ratio: B=(9F2-5F4)/441
    F2 = B*441/(9-5*ratio); F4 = ratio*F2
    H = build({0:0.0,2:F2,4:F4}) + Dq*Hcf
    # quartet subspace: S2=15/4
    w,U = np.linalg.eigh(H + 1e3*(S2-15/4*np.eye(len(states)))@(S2-15/4*np.eye(len(states))))
    # select states with S^2 close 15/4
    Hq = U.conj().T @ H @ U
    res=[]
    for j in range(len(w)):
        v = U[:,j]
        s2 = np.real(np.vdot(v, S2@v))
        if abs(s2-15/4)<1e-6: res.append(w[j])
    return np.sort(np.array(res))
# need only quartet block: project
def quartet_levels(Dq,B,ratio=0.625):
    F2 = B*441/(9-5*ratio); F4 = ratio*F2
    H = build({0:0.0,2:F2,4:F4}) + Dq*Hcf
    # S^2 eigen-decomposition
    P = np.eye(len(states))
    Q = S2 - 15/4*np.eye(len(states))
    # quartet subspace = null space of Q
    u,s,vh = np.linalg.svd(Q)
    null = vh[np.abs(s)<1e-8] if False else None
    w,V = np.linalg.eigh(S2)
    Vq = V[:, np.abs(w-15/4)<1e-6]
    Hq = Vq.T @ H @ Vq
    return np.sort(np.linalg.eigvalsh(Hq)), Vq.shape[1]

if __name__=="__main__":
    for ratio in [0.5,0.625]:
        lev,n = quartet_levels(1000.0, 1000.0, ratio)
        print("ratio",ratio,"n quartet states", n, np.round(lev-lev[0],2))
    # check mixing by Dq and B: ground state energy
    print("Hcf eig:", np.round(np.linalg.eigvalsh(Hcf),3)[:5])
EOF
cd /tmp/lf && python3 d7.py