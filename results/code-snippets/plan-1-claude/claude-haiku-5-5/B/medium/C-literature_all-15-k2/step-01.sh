
cat << 'EOF' > /tmp/d7.py
import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import least_squares

# angular quadrature
nt, nphi = 40, 80
x, w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.arange(nphi)*2*np.pi/nphi
TH, PH = np.meshgrid(th, ph, indexing='ij')
W = np.outer(w, np.full(nphi, 2*np.pi/nphi))

# real d orbital angular functions (unnormalized combos of Y2m), normalized numerically
def Ylm(l,m,T,P): return sph_harm(m, l, P, T)  # scipy: sph_harm(m,n,azimuth,polar)
def real_d():
    orbs=[]
    s=1/np.sqrt(2)
    # xy, yz, zx, x2-y2, z2 as combinations of Y_2^m
    orbs.append(lambda T,P: (Ylm(2,-2,T,P)-Ylm(2,2,T,P))*1j*s)  # xy-ish
    orbs.append(lambda T,P: (Ylm(2,-1,T,P)+Ylm(2,1,T,P))*s*(-1))  # yz
    orbs.append(lambda T,P: (Ylm(2,-1,T,P)-Ylm(2,1,T,P))*1j*s)   # zx
    orbs.append(lambda T,P: (Ylm(2,-2,T,P)+Ylm(2,2,T,P))*s)      # x2-y2
    orbs.append(lambda T,P: Ylm(2,0,T,P))                        # z2
    return orbs
orbs = real_d()
# evaluate and normalize
vals=[]
for f in orbs:
    v = f(TH,PH)
    # make real
    if np.abs(v.imag).max()>1e-10: v = v/1j if np.abs(v.real).max()<1e-10 else v
    v = np.real_if_close(v, tol=1e6)
    nrm = np.sqrt(np.sum(W*np.abs(v)**2))
    vals.append(v/nrm)
vals=np.array(vals)
# check orthonormality
G = np.array([[np.sum(W*np.conj(a)*b) for b in vals] for a in vals])
assert np.allclose(G,np.eye(5),atol=1e-8), np.round(G,6)

# X_kq(a,c) = int a* c Y_kq* dOmega
def Xk(k,q,a,c):
    Yk = np.conj(sph_harm(q,k,PH,TH))
    return np.sum(W*np.conj(a)*c*Yk)
# angular coefficient a_k(a,b,c,d) for <ab|1/r12|cd>: sum_k F_k * 4pi/(2k+1) sum_q X_kq(a,c) X_kq(b,d)^*  (conj of Y_kq* -> Y_kq)
def ang(k,a,b,c,d):
    s=0
    for q in range(-k,k+1):
        s += Xk(k,q,a,c)*np.conj(Xk(k,q,b,d))
    return 4*np.pi/(2*k+1)*s
A = {}
for k in (0,2,4):
    A[k]=np.zeros((5,5,5,5))
    for a,b,c,d in itertools.product(range(5),repeat=4):
        A[k][a,b,c,d]=np.real(ang(k,vals[a],vals[b],vals[c],vals[d]))

# spin orbitals: index 2*o+s, s=0 up,1 down
N=10
states=[sum(1<<i for i in c) for c in itertools.combinations(range(N),7)]
def build(Dq,F0,F2,F4,sector_Ms=None):
    # one-body CF in real basis
    h=np.zeros((5,5))
    h[0,0]=h[1,1]=h[2,2]=-4*Dq
    h[3,3]=h[4,4]=6*Dq
    sts=states
    if sector_Ms is not None:
        sts=[s for s in states if (sum(1 for o in range(5) if s>>(2*o)&1)-sum(1 for o in range(5) if s>>(2*o+1)&1))==sector_Ms]
    idx={s:i for i,s in enumerate(sts)}
    H=np.zeros((len(sts),len(sts)))
    Vee = {}
    # two-body integrals <ij|kl> with spin
    def V(i,j,k,l):
        oi,si=divmod(i,2); oj,sj=divmod(j,2); ok,sk=divmod(k,2); ol,sl=divmod(l,2)
        if si!=sk or sj!=sl: return 0.0
        return F0*A[0][oi,oj,ok,ol]+F2*A[2][oi,oj,ok,ol]+F4*A[4][oi,oj,ok,ol]
    def apply_c(s,i):  # annihilate i
        if not (s>>i)&1: return None,0
        sign=(-1)**bin(s&((1<<i)-1)).count('1')
        return s^(1<<i), sign
    def apply_cd(s,i):  # create i
        if (s>>i)&1: return None,0
        sign=(-1)**bin(s&((1<<i)-1)).count('1')
        return s|(1<<i), sign
    for s in sts:
        col=idx[s]
        # one-body
        for i in range(N):
            for j in range(N):
                if i%2!=j%2: continue
                hij=h[i//2,j//2]
                if hij==0: continue
                s1,sg1=apply_c(s,j)
                if s1 is None: continue
                s2,sg2=apply_cd(s1,i)
                if s2 is None: continue
                if s2 in idx: H[idx[s2],col]+=hij*sg1*sg2
        # two-body: 1/2 sum <ij|kl> c+_i c+_j c_l c_k
        for i,j,k,l in itertools.product(range(N),repeat=4):
            v=V(i,j,k,l)
            if v==0 or i==j or k==l: continue
            s1,sg1=apply_c(s,k)
            if s1 is None: continue
            s2,sg2=apply_c(s1,l)
            if s2 is None: continue
            s3,sg3=apply_cd(s2,j)
            if s3 is None: continue
            s4,sg4=apply_cd(s3,i)
            if s4 is None: continue
            if s4 in idx: H[idx[s4],col]+=0.5*v*sg1*sg2*sg3*sg4
    return H, sts

def quartet_levels(Dq,B,C):
    F4=C*441/35.0
    F2=(441*B+5*F4)/9.0
    H,_=build(Dq,0.0,F2,F4,sector_Ms=1.5)  # uses F0 irrelevant (shift)
    return np.linalg.eigvalsh(H)

if __name__=="__main__":
    ev=quartet_levels(1000,850,3500)
    print(np.round(ev,1))
EOF
cd /tmp && timeout 550 python3 d7.py
