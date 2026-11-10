
cat << 'EOF' > /tmp/d6.py
import numpy as np, itertools
from scipy.optimize import brentq
from scipy.special import sph_harm
# angular grid
nt, nphi = 24, 48
x, w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.arange(nphi)*2*np.pi/nphi
TH, PH = np.meshgrid(th, ph, indexing='ij'); W = np.outer(w, np.ones(nphi))*(2*np.pi/nphi)
def Y(l,m): return sph_harm(m, l, PH, TH)  # scipy: sph_harm(m,n,azimuth,polar)
ms = range(-2,3)
Ylm = {m: Y(2,m) for m in ms}
def integ(f): return np.sum(W*f)
# G(m1,m3,k,q)=∫ Y_m1^* Y_kq^* Y_m3
def G(m1,m3,k,q): return integ(np.conj(Ylm[m1])*np.conj(Y(k,q))*Ylm[m3])
def H(m2,m4,k,q): return integ(np.conj(Ylm[m2])*Y(k,q)*Ylm[m4])
def Vsp(m1,m2,m3,m4,Fk):
    tot=0
    for k,F in Fk.items():
        s=0
        for q in range(-k,k+1):
            s+= G(m1,m3,k,q)*H(m2,m4,k,q)
        tot+= F*4*np.pi/(2*k+1)*s
    return tot
# spatial orbital index 0..4 for m=-2..2
orbs=list(ms)
# Build spin-orbital index: i = 2*o + s
def build(Dq_over_B, B=1.0):
    F2=80.5*B; F4=0.70435*F2*B/B  # F4 = 0.70435*F2
    F4=0.70435*F2
    Fk={2:F2,4:F4}
    # one-electron: projectors
    ket=lambda m: np.eye(5)[m+2].astype(complex)
    t2g_vecs=[ket(1),ket(-1),(ket(2)-ket(-2))/(1j*np.sqrt(2))]
    eg_vecs=[ket(0),(ket(2)+ket(-2))/np.sqrt(2)]
    h=np.zeros((5,5),complex)
    for v in t2g_vecs: h+= -4*Dq_over_B*np.outer(v,v.conj())
    for v in eg_vecs: h+= 6*Dq_over_B*np.outer(v,v.conj())
    # spatial two-electron tensor
    Vt=np.zeros((5,5,5,5),complex)
    for a,b,c,d in itertools.product(range(5),repeat=4):
        Vt[a,b,c,d]=Vsp(orbs[a],orbs[b],orbs[c],orbs[d],Fk)
    # spin-orbitals: index 2*o+s
    n=10
    h_so=np.kron(h,np.eye(2))
    V_so=np.zeros((n,n,n,n),complex)
    for i,j,k,l in itertools.product(range(n),repeat=4):
        oi,si=divmod(i,2); oj,sj=divmod(j,2); ok,sk=divmod(k,2); ol,sl=divmod(l,2)
        if si==sk and sj==sl:
            V_so[i,j,k,l]=Vt[oi,oj,ok,ol]
    # determinants with 6 electrons
    dets=[sum(1<<i for i in c) for c in itertools.combinations(range(n),6)]
    idx={d:k for k,d in enumerate(dets)}
    D=len(dets); Hm=np.zeros((D,D),complex)
    def apply_ops(state, ops):
        # ops list of (type,index) applied right to left: ops given as sequence to apply in order (first applied first)
        s=state; sign=1
        for typ,i in ops:
            occ=(s>>i)&1
            if typ=='a':  # annihilate
                if not occ: return None,0
                sign*= (-1)**bin(s & ((1<<i)-1)).count('1')
                s ^= (1<<i)
            else:
                if occ: return None,0
                sign*= (-1)**bin(s & ((1<<i)-1)).count('1')
                s ^= (1<<i)
        return s,sign
    for col,d in enumerate(dets):
        # one-body
        for i in range(n):
            for j in range(n):
                if h_so[i,j]==0: continue
                s,sg=apply_ops(d,[('a',j),('c',i)])
                if s is not None: Hm[idx[s],col]+=h_so[i,j]*sg
        # two-body 1/2 sum V_ijkl c†i c†j c_l c_k
        for i,j,k,l in itertools.product(range(n),repeat=4):
            v=V_so[i,j,k,l]
            if v==0: continue
            s,sg=apply_ops(d,[('a',k),('a',l),('c',j),('c',i)])
            if s is not None: Hm[idx[s],col]+=0.5*v*sg
    # S_z=0 projection: choose states with Sz=0 : count up minus down =0 -> 3 up 3 down
    # and spin singlet: use S^2 eigen. Simpler: build total S^2 and diagonalize within Sz=0 then select S=0
    Sz=np.array([sum(0.5 if (i&1)==0 else -0.5 for i in range(n) if (d>>i)&1) for d in dets])
    sel=[k for k,d in enumerate(dets) if abs(Sz[k])<1e-9]
    Hs=Hm[np.ix_(sel,sel)]
    # S^2 = S-S+ + Sz(Sz+1); compute S+ matrix
    selset=sel
    Sp=np.zeros((len(sel),len(sel)),complex)
    sidx={dets[k]:m for m,k in enumerate(sel)}
    for m,k in enumerate(sel):
        d=dets[k]
        for o in range(5):
            up=2*o; dn=2*o+1
            if (d>>dn)&1 and not (d>>up)&1:
                s,sg=apply_ops(d,[('a',dn),('c',up)])
                if s in sidx: Sp[sidx[s],m]+=sg
    S2=Sp.conj().T@Sp  # S-S+ ... Sz=0: S^2 = S- S+ ; S-=S+^†
    # S^2 = S_-S_+ + Sz^2 + Sz ; Sz=0 -> S^2 = S_-S_+
    ev,vec=np.linalg.eigh(Hs+1e6*S2)  # push non-singlets up
    # singlets are those with S2 ~0 -> eigenvalue ~ energy
    ev_s=[]
    for e,v in zip(ev,vec.T):
        s2=np.real(v.conj()@S2@v)
        if s2<1e-6: ev_s.append(e)
    return np.sort(np.array(ev_s))
if __name__=="__main__":
    import sys
    for x in [1.0,2.0]:
        print(x, build(x)[:12])
EOF
cd /tmp && timeout 900 python3 d6.py
