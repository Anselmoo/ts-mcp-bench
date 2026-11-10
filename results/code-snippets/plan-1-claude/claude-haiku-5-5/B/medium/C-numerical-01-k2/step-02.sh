mkdir -p /w && cat > /w/d2.py << 'EOF'
import numpy as np, itertools, sympy as sp
from scipy.optimize import least_squares
from sympy.functions.special.spherical_harmonics import Ynm
th,ph=sp.symbols('th ph')
# quadrature
xg,wg=np.polynomial.legendre.leggauss(30)
nphi=60
phis=np.arange(nphi)*2*np.pi/nphi
TH,PH=np.meshgrid(np.arccos(xg),phis,indexing='ij')
W=(wg[:,None]*np.ones((1,nphi)))*(2*np.pi/nphi)
ls=2
Y={}
for m in range(-2,3):
    f=sp.lambdify((th,ph),Ynm(2,m,th,ph).expand(complex=True),'numpy')
    Y[(2,m)]=np.broadcast_to(np.array(f(TH,PH),dtype=complex),TH.shape)
def Ykq(k,q):
    f=sp.lambdify((th,ph),Ynm(k,q,th,ph).expand(complex=True),'numpy')
    return np.broadcast_to(np.array(f(TH,PH),dtype=complex),TH.shape)
# orbital index m=-2..2 ; spin orbitals (m,s)
so=[(m,s) for s in (1,-1) for m in range(-2,3)]
so=[(m,s) for m in range(-2,3) for s in (1,-1)]
N=len(so)
def ang(a,b,c=None):
    pass
# angular X_kq(a,c)=∫ a* Y_kq* c
Xk={}
for k in (0,2,4):
    for q in range(-k,k+1):
        Yc=np.conj(Ykq(k,q))
        Xk[(k,q)]=np.array([[np.sum(W*np.conj(Y[(2,a)])*Yc*Y[(2,c)]) for c in range(-2,3)] for a in range(-2,3)])
# two-electron matrix elements of 1/r12 angular part for k: V_abcd = F^k * (4pi/(2k+1)) sum_q X_kq(a,c) X'_kq(b,d)
# where X'_kq(b,d)=∫ b* Y_kq d  (no conj on Y) -> Ykq(k,q) = conj(Y_k,-q)*(-1)^q ; compute directly
Zk={}
for k in (0,2,4):
    for q in range(-k,k+1):
        Yq=Ykq(k,q)
        Zk[(k,q)]=np.array([[np.sum(W*np.conj(Y[(2,b)])*Yq*Y[(2,d)]) for d in range(-2,3)] for b in range(-2,3)])
def Vang(k,a,b,c,d):  # orbital indices 0..4
    return 4*np.pi/(2*k+1)*sum(Xk[(k,q)][a,c]*Zk[(k,q)][b,d] for q in range(-k,k+1))
# check: k=0 should give 1/(4pi)*... sanity
# build 2e operator matrices M_k in determinant basis
states=list(itertools.combinations(range(N),2))
idx={s:i for i,s in enumerate(states)}
def apply_ops(ops,state):
    # ops: list of (type,i) applied right-to-left: list given in order of application (first applied first)
    occ=list(state); sign=1
    for typ,i in ops:
        if typ=='a':  # annihilate
            if i not in occ: return None,0
            p=occ.index(i); sign*= (-1)**p; occ.pop(p)
        else:
            if i in occ: return None,0
            # insert at sorted position
            p=sum(1 for x in occ if x<i); sign*=(-1)**p; occ.insert(p,i)
    return tuple(occ),sign
def op2(k):
    M=np.zeros((len(states),len(states)),dtype=complex)
    for ci,s in enumerate(states):
        for a in range(N):
          for b in range(N):
            for c in range(N):
              for d in range(N):
                ma,sa=so[a]; mb,sb=so[b]; mc,sc=so[c]; md,sd=so[d]
                if sa!=sc or sb!=sd: continue
                v=Vang(k,ma+2,mb+2,mc+2,md+2)
                if abs(v)<1e-12: continue
                # 1/2 sum a†_a a†_b a_d a_c : apply a_c first, then a_d, then a†_b, then a†_a
                st,sg=apply_ops([('a',c),('a',d),('c',b),('c',a)],s) if False else (None,0)
                ops=[('a',c),('a',d),('c',b),('c',a)]
                occ=s; sign=1; ok=True
                cur=s
                for typ,i in ops:
                    cur,sgn=apply_ops([(typ,i)],cur)
                    if cur is None: ok=False;break
                    sign*=sgn
                if not ok: continue
                if cur in idx:
                    M[idx[cur],ci]+=0.5*v*sign
    return M
M2=op2(2); M4=op2(4)
# one-electron CF: angular operator W = Y40 + sqrt(5/14)(Y44+Y4-4)
Y40=Ykq(4,0); Y44=Ykq(4,4); Y4m4=Ykq(4,-4)
Wop=Y40+np.sqrt(5/14)*(Y44+Y4m4)
Wm=np.array([[np.sum(W*np.conj(Y[(2,a)])*Wop*Y[(2,c)]) for c in range(-2,3)] for a in range(-2,3)])
ev=np.linalg.eigvalsh((Wm+Wm.conj().T)/2)
print("W eig",ev)
# identify eg (2 states) and t2g (3): eg is top with larger magnitude; eigen values
h1=np.zeros((N,N),dtype=complex)
# build 1e matrix: one-electron operator in spin orbitals (spin diagonal)
Wc=(Wm+Wm.conj().T)/2
# normalize: eg - t2g = 10 Dq, with t2g=-4, eg=+6 in units of Dq
wt2=ev[0]; weg=ev[-1]
# scale so that splitting: unit vector
def h1mat(Dq):
    scale=10*Dq/(weg-wt2) # eg-t2g=10Dq; need consistent sign: eg=+6Dq
    # ev ascending: ev[0..2] t2g (3 states), ev[3..4] eg (2)
    return scale*Wc
# check ordering
print(ev)
np.save('/w/ops.npy',np.array([M2,M4]))
np.save('/w/Wc.npy',Wc)
np.save('/w/states.npy',np.array(states))
EOF
cd /w && time python3 d2.py