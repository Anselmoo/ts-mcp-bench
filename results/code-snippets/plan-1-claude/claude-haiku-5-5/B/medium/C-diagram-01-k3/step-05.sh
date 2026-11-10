mkdir -p /tmp/ts && cat > /tmp/ts/ts.py << 'EOF'
import numpy as np, itertools
from scipy.linalg import expm
from scipy.special import lpmv, factorial
from scipy.spatial.transform import Rotation as Rot

B=1.0; C=3390/828
F2=49*B+7*C; F4=63*C/5
# single-particle: orbital index i=m+2 (m=-2..2); spin orbital a = 2*i+s (s=0 up,1 down)
L=2; ms=np.arange(-2,3); n=5
Lz=np.diag(ms).astype(complex)
Lp=np.zeros((n,n),complex)
for i,m in enumerate(ms):
    if m<2: Lp[i+1,i]=np.sqrt(L*(L+1)-m*(m+1))
Lm=Lp.conj().T
Lx=(Lp+Lm)/2; Ly=(Lp-Lm)/(2j)
Lvec=[Lx,Ly,Lz]

def Ylm(l,m,th,ph):
    am=abs(m)
    norm=np.sqrt((2*l+1)/(4*np.pi)*factorial(l-am)/factorial(l+am))
    P=lpmv(am,l,np.cos(th))
    y=norm*P*np.exp(1j*am*ph)
    if m<0: y=(-1)**am*np.conj(y)
    return y
# quadrature
xg,wg=np.polynomial.legendre.leggauss(20)
nph=40
phs=np.arange(nph)*2*np.pi/nph
TH,PH=np.meshgrid(np.arccos(xg),phs,indexing='ij')
W=(wg[:,None]*np.ones((1,nph)))*(2*np.pi/nph)
Ymat={m:Ylm(2,m,TH,PH) for m in ms}
def integ(f): return np.sum(W*f)
# Gaunt-type: A_kq(a,b)=∫Y_a* Y_b Y_kq*, Bk(a,b)=∫Y_a* Y_b Y_kq
def Yk(k,q): return Ylm(k,q,TH,PH)
def coul(m1,m2,m3,m4):
    # <m1 m2|1/r12|m3 m4> angular part, F^k coefficient
    res={}
    for k in (0,2,4):
        s=0
        for q in range(-k,k+1):
            ykq=Yk(k,q)
            A=integ(np.conj(Ymat[m1])*Ymat[m3]*np.conj(ykq))
            Bb=integ(np.conj(Ymat[m2])*Ymat[m4]*ykq)
            s+=A*Bb
        res[k]=(4*np.pi/(2*k+1))*s
    return res
Fk={0:0.0,2:F2,4:F4}
# one-electron Dq part: h = 6Dq P_eg - 4Dq P_t2g  (units of B; Dq passed later)
Peg=np.zeros((n,n),complex); Pt=np.zeros((n,n),complex)
def idx(m): return m+2
# eg: Y20 and (Y22+Y2-2)/sqrt2
for v in [np.eye(n)[idx(0)], (np.eye(n)[idx(2)]+np.eye(n)[idx(-2)])/np.sqrt(2)]:
    Peg+=np.outer(v,v.conj())
for v in [(np.eye(n)[idx(2)]-np.eye(n)[idx(-2)])/(1j*np.sqrt(2)),
          (np.eye(n)[idx(1)]-np.eye(n)[idx(-1)])/np.sqrt(2),
          (np.eye(n)[idx(1)]+np.eye(n)[idx(-1)])/(1j*np.sqrt(2))]:
    Pt+=np.outer(v,v.conj())
hcf=6*Peg-4*Pt
# two-body tensor V[m1,m2,m3,m4]
Vt=np.zeros((n,n,n,n),complex)
for a,b,c,d in itertools.product(range(n),repeat=4):
    r=coul(ms[a],ms[b],ms[c],ms[d])
    Vt[a,b,c,d]=sum(Fk[k]*r[k] for k in (2,4))
# Fock space, 10 spin orbitals
NS=2*n
I2=np.eye(2); Z=np.diag([1.,-1.]); an=np.array([[0,1],[0,0]],float)  # annihilation on (empty,occupied)? use basis |0>=(1,0),|1>=(0,1)
def kron_list(ops):
    out=np.array([[1.0]])
    for o in ops: out=np.kron(out,o)
    return out
cops=[]
for a in range(NS):
    ops=[Z]*a+[an]+[I2]*(NS-a-1)
    cops.append(kron_list(ops))
# annihilation c_a with basis |0>=(1,0)=empty: c = |0><1| ; with an=[[0,1],[0,0]] = |0><1| ✓
cdag=[c.T.copy() for c in cops]
dim=2**NS
Ntot=sum(cdag[a]@cops[a] for a in range(NS))
occ=np.real(np.diag(Ntot))
sel=np.where(np.abs(occ-3)<1e-9)[0]
def restrict(M): return M[np.ix_(sel,sel)]
# one-body operator
def onebody(h):
    # h in orbital basis (n x n), spin diagonal
    O=np.zeros((dim,dim),complex)
    for i in range(n):
        for j in range(n):
            if abs(h[i,j])<1e-14: continue
            for s in (0,1):
                O+=h[i,j]*cdag[2*i+s]@cops[2*j+s]
    return O
# two-body: (1/2) sum V_{ijkl} c†_i c†_j c_l c_k, with <ij|V|kl>, spins: s_i=s_k, s_j=s_l
def twobody_full():
    O=np.zeros((dim,dim),complex)
    for i,j,k,l in itertools.product(range(n),repeat=4):
        v=Vt[i,j,k,l]
        if abs(v)<1e-13: continue
        for s1 in (0,1):
            for s2 in (0,1):
                O+=0.5*v*cdag[2*i+s1]@cdag[2*j+s2]@cops[2*l+s2]@cops[2*k+s1]
    return O
Hfull=onebody(hcf) 
H2=twobody_full()
np.save('/tmp/ts/H2.npy',restrict(H2))
np.save('/tmp/ts/Hcf.npy',restrict(Hfull))
np.save('/tmp/ts/Lx.npy',restrict(onebody(Lx))); np.save('/tmp/ts/Ly.npy',restrict(onebody(Ly))); np.save('/tmp/ts/Lz.npy',restrict(onebody(Lz)))
Sz=sum(0.5*(cdag[2*i]@cops[2*i]-cdag[2*i+1]@cops[2*i+1]) for i in range(n))
Sp=sum(cdag[2*i]@cops[2*i+1] for i in range(n)); Sm=Sp.conj().T
S2=Sm@Sp+Sz@Sz+Sz
np.save('/tmp/ts/Sz.npy',restrict(Sz)); np.save('/tmp/ts/S2.npy',restrict(S2))
print("dim",len(sel))
EOF
cd /tmp/ts && time python3 ts.py