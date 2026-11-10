mkdir -p /w && cat > /w/ni.py <<'EOF'
import numpy as np, itertools
from scipy.special import lpmv, factorial
from scipy.optimize import least_squares
# angular grid
xg,wg=np.polynomial.legendre.leggauss(40)
phis=np.linspace(0,2*np.pi,80,endpoint=False); wp=2*np.pi/80
TH,PH=np.meshgrid(np.arccos(xg),phis,indexing='ij'); W=(wg[:,None]*wp*np.ones_like(TH))
def Y(l,m,th,ph):
    am=abs(m)
    N=np.sqrt((2*l+1)/(4*np.pi)*factorial(l-am)/factorial(l+am))
    P=lpmv(am,l,np.cos(th))
    y=N*P*np.exp(1j*am*ph)
    if m<0: y=(-1)**am*np.conj(y)
    return y
ms=[-2,-1,0,1,2]
Yd={m:Y(2,m,TH,PH) for m in ms}
def ang(a,c,k,q):  # ∫ Y_a^* Y_c Y_kq^*
    return np.sum(W*np.conj(Yd[a])*Yd[c]*np.conj(Y(k,q,TH,PH)))
# Slater-like Coulomb: <a b|1/r|c d> spatial = sum_k F^k 4pi/(2k+1) sum_q A(a,c,k,q) A(b,d,k,-q)*(-1)^q-ish handled via conj
def Vsp(a,b,c,d,F):
    tot=0
    for k in (0,2,4):
        if k not in F: continue
        s=0
        for q in range(-k,k+1):
            if abs(q)>2: continue
            s+=ang(a,c,k,q)*np.conj(ang(b,d,k,q))*0  # placeholder
        tot+=0
    return tot
# precompute angular tables
Ang={}
for k in (0,2,4):
    for a in ms:
        for c in ms:
            for q in range(-k,k+1):
                Ang[(a,c,k,q)]=ang(a,c,k,q)
def Vspat(a,b,c,d,F):
    tot=0
    for k in (0,2,4):
        s=0
        for q in range(-k,k+1):
            s+=Ang[(a,c,k,q)]*Ang[(b,d,k,-q)]*(-1)**q
        tot+=F[k]*4*np.pi/(2*k+1)*s
    return tot
# spin-orbitals: index = 2*(m+2)+s
so=[(m,s) for m in ms for s in (0,1)]
n=10
def build(Dq,B,C):
    F4=441*C/35; F2=49*B+7*C
    F={0:0.0,2:F2,4:F4}
    # one-electron CF in complex basis
    # real eg/t2g projectors
    def vec(d):
        v=np.zeros(5,complex)
        for m,c in d.items(): v[m+2]=c
        return v
    s2=np.sqrt(2)
    # Y_{2,m} basis: vectors over ms
    z2=vec({0:1})
    x2c=vec({2:1/s2,-2:1/s2})
    xys=vec({2:-1j/s2,-2:1j/s2})   # Rs m=2 (xy)
    xzc=vec({1:-1/s2,-1:1/s2})
    yzs=vec({1:-1j/s2,-1:-1j/s2})
    eg=[z2,x2c]; t2=[xzc,yzs,xys]
    P=np.zeros((5,5),complex)
    for v in eg: P_=np.outer(v,v.conj()); P+=6*Dq*P_
    for v in t2: P+=-4*Dq*np.outer(v,v.conj())
    h1=np.zeros((10,10),complex)
    for i,(m1,s1) in enumerate(so):
        for j,(m2,s2_) in enumerate(so):
            if s1==s2_: h1[i,j]=P[m1+2,m2+2]
    # two-electron
    V=np.zeros((10,10,10,10),complex)
    for a in range(10):
        for b in range(10):
            for c in range(10):
                for d in range(10):
                    ma,sa=so[a]; mb,sb=so[b]; mc,sc=so[c]; md,sd=so[d]
                    if sa!=sc or sb!=sd: continue
                    V[a,b,c,d]=Vspat(ma,mb,mc,md,F)
    return h1,V
# Fock space ops, N=8 subspace
dim=2**10
def bits(x): return [i for i in range(10) if x>>i &1]
states=[x for x in range(dim) if bin(x).count('1')==8]
idx={x:i for i,x in enumerate(states)}
D=len(states)
def apply_c_dag_c(i,j):
    # c_i^dag c_j matrix on states
    M=np.zeros((D,D))
    for x in states:
        if not (x>>j)&1: continue
        s=(-1)**bin(x & ((1<<j)-1)).count('1')
        y=x^(1<<j)
        if (y>>i)&1: continue
        s*= (-1)**bin(y & ((1<<i)-1)).count('1')
        z=y|(1<<i)
        M[idx[z],idx[x]]+=s
    return M
def S2op():
    Sz=np.zeros(D); Sp=np.zeros((D,D))
    # S+ = sum_m c+_{m,up} c_{m,dn}
    for m in range(5):
        Sp+=apply_c_dag_c(2*m,2*m+1)
    Sz=np.zeros((D,D))
    for m in range(5):
        Sz+=0.5*(apply_c_dag_c(2*m,2*m)-apply_c_dag_c(2*m+1,2*m+1))
    S2=Sp.T@Sp+Sz@Sz-Sz  # S-^2 ... use S^2=S-S+ + Sz^2+Sz
    S2=Sp.T@Sp+Sz@Sz+Sz
    return S2
def spectrum(Dq,B,C,S2=None):
    h1,V=build(Dq,B,C)
    H=np.zeros((D,D),complex)
    cache={}
    def cdc(i,j):
        if (i,j) not in cache: cache[(i,j)]=apply_c_dag_c(i,j)
        return cache[(i,j)]
    for i in range(10):
        for j in range(10):
            if abs(h1[i,j])>1e-12: H+=h1[i,j]*cdc(i,j)
    # two-body: 1/2 sum V_abcd c+_a c+_b c_d c_c  ; c+_a c+_b c_d c_c = c+_a (c+_b c_d) c_c - delta_bd c+_a c_c
    # use direct: build via products of one-body ops
    for a in range(10):
        for b in range(10):
            for c in range(10):
                for d in range(10):
                    v=V[a,b,c,d]
                    if abs(v)<1e-12: continue
                    if a==b or c==d: continue
                    # c+_a c+_b c_d c_c = c+_a c_c c+_b c_d  - delta_bc c+_a c_d... use explicit
                    M=cdc2(a,b,c,d)
                    H+=0.5*v*M
    return H
def cdc2(a,b,c,d):
    # matrix of c+_a c+_b c_d c_c on states
    M=np.zeros((D,D))
    for x in states:
        # apply c_c
        if not (x>>c)&1: continue
        s1=(-1)**bin(x&((1<<c)-1)).count('1'); y=x^(1<<c)
        if not (y>>d)&1: continue
        s2=(-1)**bin(y&((1<<d)-1)).count('1'); y2=y^(1<<d)
        if (y2>>b)&1: continue
        s3=(-1)**bin(y2&((1<<b)-1)).count('1'); y3=y2|(1<<b)
        if (y3>>a)&1: continue
        s4=(-1)**bin(y3&((1<<a)-1)).count('1'); y4=y3|(1<<a)
        M[idx[y4],idx[x]]+=s1*s2*s3*s4
    return M
EOF
cd /w && python3 -c "
import ni,numpy as np,time
t=time.time()
H=ni.spectrum(0.0,1000,4000)
print(time.time()-t)
"