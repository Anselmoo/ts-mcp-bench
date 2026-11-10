cat > ts.py << 'EOF'
import numpy as np, itertools
from scipy.special import lpmv, factorial
B=1.0; C=3390/828
F2=49*B+7*C; F4=63*C/5
L=2; ms=np.arange(-2,3); n=5
Lz=np.diag(ms).astype(complex)
Lp=np.zeros((n,n),complex)
for i,m in enumerate(ms):
    if m<2: Lp[i+1,i]=np.sqrt(L*(L+1)-m*(m+1))
Lm=Lp.conj().T
Lx=(Lp+Lm)/2; Ly=(Lp-Lm)/(2j)

def Ylm(l,m,th,ph):
    am=abs(m)
    norm=np.sqrt((2*l+1)/(4*np.pi)*factorial(l-am)/factorial(l+am))
    P=lpmv(am,l,np.cos(th))
    y=norm*P*np.exp(1j*am*ph)
    if m<0: y=(-1)**am*np.conj(y)
    return y
xg,wg=np.polynomial.legendre.leggauss(20)
nph=40
phs=np.arange(nph)*2*np.pi/nph
TH,PH=np.meshgrid(np.arccos(xg),phs,indexing='ij')
W=(wg[:,None]*np.ones((1,nph)))*(2*np.pi/nph)
Ymat={m:Ylm(2,m,TH,PH) for m in ms}
def integ(f): return np.sum(W*f)
def coul_F(m1,m2,m3,m4):
    out={}
    for k in (2,4):
        s=0
        for q in range(-k,k+1):
            ykq=Ylm(k,q,TH,PH)
            A=integ(np.conj(Ymat[m1])*Ymat[m3]*np.conj(ykq))
            Bb=integ(np.conj(Ymat[m2])*Ymat[m4]*ykq)
            s+=A*Bb
        out[k]=(4*np.pi/(2*k+1))*s
    return out
Fk={2:F2,4:F4}
def idx(m): return m+2
Peg=np.zeros((n,n),complex); Pt=np.zeros((n,n),complex)
E=np.eye(n)
for v in [E[idx(0)], (E[idx(2)]+E[idx(-2)])/np.sqrt(2)]:
    Peg+=np.outer(v,v.conj())
for v in [(E[idx(2)]-E[idx(-2)])/(1j*np.sqrt(2)),
          (E[idx(1)]-E[idx(-1)])/np.sqrt(2),
          (E[idx(1)]+E[idx(-1)])/(1j*np.sqrt(2))]:
    Pt+=np.outer(v,v.conj())
hcf=6*Peg-4*Pt   # times Dq
Vt=np.zeros((n,n,n,n),complex)
for a,b,c,d in itertools.product(range(n),repeat=4):
    r=coul_F(ms[a],ms[b],ms[c],ms[d])
    Vt[a,b,c,d]=sum(Fk[k]*r[k] for k in (2,4))
NS=2*n
I2=np.eye(2); an=np.array([[0,1],[0,0]],float); Z=np.diag([1.,-1.])
def kron_list(ops):
    out=np.array([[1.0]])
    for o in ops: out=np.kron(out,o)
    return out
cops=[kron_list([Z]*a+[an]+[I2]*(NS-a-1)) for a in range(NS)]
cdag=[c.T.copy() for c in cops]
dim=2**NS
Ntot=sum(cdag[a]@cops[a] for a in range(NS))
occ=np.real(np.diag(Ntot))
sel=np.where(np.abs(occ-3)<1e-9)[0]
def restrict(M): return M[np.ix_(sel,sel)]
def onebody(h):
    O=np.zeros((dim,dim),complex)
    for i in range(n):
        for j in range(n):
            if abs(h[i,j])<1e-14: continue
            for s in (0,1):
                O+=h[i,j]*cdag[2*i+s]@cops[2*j+s]
    return O
H2=np.zeros((dim,dim),complex)
for i,j,k,l in itertools.product(range(n),repeat=4):
    v=Vt[i,j,k,l]
    if abs(v)<1e-13: continue
    for s1 in (0,1):
        for s2 in (0,1):
            H2+=0.5*v*cdag[2*i+s1]@cdag[2*j+s2]@cops[2*l+s2]@cops[2*k+s1]
Sz=sum(0.5*(cdag[2*i]@cops[2*i]-cdag[2*i+1]@cops[2*i+1]) for i in range(n))
Sp=sum(cdag[2*i]@cops[2*i+1] for i in range(n)); Sm=Sp.conj().T
S2=Sm@Sp+Sz@Sz+Sz
np.savez('ops.npz',H2=restrict(H2),Hcf=restrict(onebody(hcf)),
         Lx=restrict(onebody(Lx)),Ly=restrict(onebody(Ly)),Lz=restrict(onebody(Lz)),
         Sz=restrict(Sz),S2=restrict(S2))
print("dim",len(sel), "F2,F4",F2,F4)
EOF
time python3 ts.py