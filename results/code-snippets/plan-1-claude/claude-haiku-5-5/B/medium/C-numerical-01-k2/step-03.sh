mkdir -p /tmp/w && cd /tmp/w && cat > d2.py << 'EOF'
import numpy as np, itertools, sympy as sp
from sympy.functions.special.spherical_harmonics import Ynm
th,ph=sp.symbols('th ph')
xg,wg=np.polynomial.legendre.leggauss(30)
nphi=60
phis=np.arange(nphi)*2*np.pi/nphi
TH,PH=np.meshgrid(np.arccos(xg),phis,indexing='ij')
W=(wg[:,None]*np.ones((1,nphi)))*(2*np.pi/nphi)
def Ykq(k,q):
    f=sp.lambdify((th,ph),Ynm(k,q,th,ph).expand(complex=True),'numpy')
    return np.broadcast_to(np.array(f(TH,PH),dtype=complex),TH.shape)
Y={m:Ykq(2,m) for m in range(-2,3)}
so=[(m,s) for m in range(-2,3) for s in (1,-1)]
N=len(so)
Xk={};Zk={}
for k in (0,2,4):
    for q in range(-k,k+1):
        Yq=Ykq(k,q)
        Xk[(k,q)]=np.array([[np.sum(W*np.conj(Y[a])*np.conj(Yq)*Y[c]) for c in range(-2,3)] for a in range(-2,3)])
        Zk[(k,q)]=np.array([[np.sum(W*np.conj(Y[b])*Yq*Y[d]) for d in range(-2,3)] for b in range(-2,3)])
states=list(itertools.combinations(range(N),2))
idx={s:i for i,s in enumerate(states)}
def applyop(typ,i,occ):
    if typ=='a':
        if i not in occ: return None,0
        p=occ.index(i); return tuple(x for x in occ if x!=i),(-1)**p
    else:
        if i in occ: return None,0
        p=sum(1 for x in occ if x<i); return tuple(sorted(occ+(i,))),(-1)**p
def op2(k):
    M=np.zeros((len(states),len(states)),dtype=complex)
    for ci,s in enumerate(states):
        for a,b,c,d in itertools.product(range(N),repeat=4):
            ma,sa=so[a]; mb,sb=so[b]; mc,sc=so[c]; md,sd=so[d]
            if sa!=sc or sb!=sd: continue
            v=4*np.pi/(2*k+1)*sum(Xk[(k,q)][ma+2,mc+2]*Zk[(k,q)][mb+2,md+2] for q in range(-k,k+1))
            if abs(v)<1e-12: continue
            cur=s; sign=1; ok=True
            for typ,i in [('a',c),('a',d),('c',b),('c',a)]:
                cur,sg=applyop(typ,i,cur)
                if cur is None: ok=False;break
                sign*=sg
            if ok and cur in idx:
                M[idx[cur],ci]+=0.5*v*sign
    return M
M2=op2(2); M4=op2(4)
Y40=Ykq(4,0); Y44=Ykq(4,4); Y4m4=Ykq(4,-4)
Wop=Y40+np.sqrt(5/14)*(Y44+Y4m4)
Wm=np.array([[np.sum(W*np.conj(Y[a])*Wop*Y[c]) for c in range(-2,3)] for a in range(-2,3)])
Wc=(Wm+Wm.conj().T)/2
ev=np.linalg.eigvalsh(Wc)
print("W eig",ev)
np.savez('ops.npz',M2=M2,M4=M4,Wc=Wc,ev=ev)
print(np.abs(M2-M2.conj().T).max(), np.abs(M4-M4.conj().T).max())
EOF
time python3 d2.py