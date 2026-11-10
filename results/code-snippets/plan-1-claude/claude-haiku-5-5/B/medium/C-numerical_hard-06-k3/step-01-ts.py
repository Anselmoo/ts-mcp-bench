import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import least_squares
from numpy.polynomial.legendre import leggauss

# angular grid for Gaunt-type integrals
x,w = leggauss(30); nphi=60
th = np.arccos(x); ph = np.arange(nphi)*2*np.pi/nphi
TH,PH = np.meshgrid(th,ph,indexing='ij'); W = np.outer(w, np.ones(nphi))*(2*np.pi/nphi)
def Y(l,m): return sph_harm(m,l,PH,TH)   # scipy: sph_harm(m,n,azimuth,polar)
ms=range(-2,3)
Yd={m:Y(2,m) for m in ms}
def integ(f): return np.sum(W*f)
# Y_k with k=0,2,4 for q
def Yk(k,q): return Y(k,q)
# angular tensor A[k][a,c,q] = int Y*_a Y*_kq Y_c
ang={}
for k in (0,2,4):
    T=np.zeros((5,5,2*k+1,5,5),complex)  # not used
# build Coulomb tensor C[k] for complex basis: V_ac,bd = sum_q (4pi/(2k+1)) * int Y*_a Y*_kq Y_c * int Y*_b Y_kq Y_d
Ck={}
for k in (0,2,4):
    M=np.zeros((5,5,5,5),complex)  # M[a,c,b,d] factor product summed over q
    for q in range(-k,k+1):
        Ykq=Y(k,q)
        P=np.zeros((5,5),complex); Qm=np.zeros((5,5),complex)
        for i,ma in enumerate(ms):
            for j,mc in enumerate(ms):
                P[i,j]=integ(np.conj(Yd[ma])*np.conj(Ykq)*Yd[mc])
                Qm[i,j]=integ(np.conj(Yd[ma])*Ykq*Yd[mc])
        M += (4*np.pi/(2*k+1))*np.einsum('ac,bd->acbd',P,Qm)
    Ck[k]=M
# real orbitals in complex basis (index m=-2..2 -> 0..4)
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
s2=np.sqrt(2)
orbs={
 'z2':vec({0:1}),
 'x2y2':vec({2:1/s2,-2:1/s2}),
 'xy':vec({-2:1/(1j*s2),2:-1/(1j*s2)}),
 'xz':vec({1:-1/s2,-1:1/s2}),
 'yz':vec({1:1j/s2,-1:1j/s2}),
}
eg={'z2','x2y2'}
# spin-orbital basis: index p = 2*orb + s  (orb in 0..4 for m=-2..2 complex)
def cubic_h(Dq):
    h=np.zeros((5,5),complex)
    for name,v in orbs.items():
        e = 6*Dq if name in eg else -4*Dq
        h += e*np.outer(v,np.conj(v))
    return h
# Fock space
states=[sum(1<<i for i in c) for c in itertools.combinations(range(10),6)]
idx={s:i for i,s in enumerate(states)}
def spin_orb(p): return p//2, p%2  # orbital m index 0..4, spin
def build(Dq,B,C):
    F2,F4 = None,None
    # Griffith: B=(9F2-5F4)/441, C=35F4/441
    F4 = 441*C/35.0
    F2 = (441*B+5*F4)/9.0
    Fk={0:0.0,2:F2,4:F4}
    h1=cubic_h(Dq)
    N=len(states); H=np.zeros((N,N),complex)
    # two-electron: (1/2) sum V_{abcd} c+_a c+_b c_d c_c, V_{abcd}=<ab|V|cd>
    # precompute V for spin-orbital indices
    V=np.zeros((10,10,10,10),complex)
    for a in range(10):
        for b in range(10):
            for c in range(10):
                for d in range(10):
                    oa,sa=spin_orb(a); ob,sb=spin_orb(b); oc,sc=spin_orb(c); od,sd=spin_orb(d)
                    if sa!=sc or sb!=sd: continue
                    val=0
                    for k in (0,2,4):
                        val+=Fk[k]*Ck[k][oa,oc,ob,od]
                    V[a,b,c,d]=val
    def apply_ops(state, ops):
        # ops list of (type,idx) applied right to left
        s=state; sign=1
        for typ,p in reversed(ops):
            occ = (s>>p)&1
            if typ=='c' and not occ: return None,0
            if typ=='d' and occ: return None,0
            # sign = (-1)^{number of occupied orbitals below p}
            n = bin(s & ((1<<p)-1)).count('1')
            sign *= (-1)**n
            s ^= (1<<p)
        return s,sign
    for i,s in enumerate(states):
        # one-body
        for a in range(10):
            for b in range(10):
                oa,sa=spin_orb(a); ob,sb=spin_orb(b)
                if sa!=sb or h1[oa,ob]==0: continue
                t,sg=apply_ops(s,[('c',a),('d',b)])
                if t is None: continue
                H[idx[t],i]+=sg*h1[oa,ob]
        # two-body
        for a in range(10):
            for b in range(10):
                if a==b: continue
                for c in range(10):
                    for d in range(10):
                        if c==d: continue
                        v=V[a,b,c,d]
                        if abs(v)<1e-12: continue
                        t,sg=apply_ops(s,[('c',a),('c',b),('d',d),('d',c)])
                        if t is None: continue
                        H[idx[t],i]+=0.5*sg*v
    # S^2 operator: S^2 = S-^S+ + Sz^2 + Sz ; build Sz, S+ 
    Sz=np.zeros((N,N)); Sp=np.zeros((N,N))
    for i,s in enumerate(states):
        sz=0
        for p in range(10):
            if (s>>p)&1: sz += 0.5 if p%2==0 else -0.5
        Sz[i,i]=sz
        for o in range(5):
            pa,pb=2*o,2*o+1  # alpha=even? spin: p%2==0 -> up
            # S+ : c_up^dag c_down
            if (s>>pb)&1 and not (s>>pa)&1:
                t,sg=apply_ops(s,[('c',pa),('d',pb)])
                Sp[idx[t],i]+=sg
    S2 = Sp.T@Sp + Sz@Sz - Sz  # S^2 = S- S+ + Sz^2 + Sz ... use S+^T S+ = S- S+
    S2 = Sp.T@Sp + Sz@Sz - Sz
    return H,S2

def singlet_levels(Dq,B,C=None):
    if C is None: C=4*B
    H,S2 = build(Dq,B,C)
    # restrict to Sz=0 sector
    sel=[i for i,s in enumerate(states) if sum((1 if p%2==0 else -1) for p in range(10) if (s>>p)&1)==0]
    Hs=H[np.ix_(sel,sel)]; S2s=S2[np.ix_(sel,sel)]
    # diagonalize H in singlet subspace: project by S2 eigen ~0
    w,v=np.linalg.eigh(S2s)
    P=v[:,np.abs(w)<1e-6]
    Hsing=P.conj().T@Hs@P
    e=np.sort(np.linalg.eigvalsh(Hsing).real)
    return e
if __name__=="__main__":
    import sys
    e=singlet_levels(2000.0,1000.0)
    print(np.round(e,1))
