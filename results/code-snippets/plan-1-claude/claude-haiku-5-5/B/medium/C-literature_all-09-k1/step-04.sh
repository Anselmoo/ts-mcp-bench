mkdir -p /tmp/w && cd /tmp/w && cat > d5.py << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.optimize import least_squares

ms = [-2,-1,0,1,2]
NSO=10
xg,wg = np.polynomial.legendre.leggauss(30)
nphi=40
phis = np.arange(nphi)*2*np.pi/nphi
TH,PH = np.meshgrid(np.arccos(xg), phis, indexing='ij')
W = np.outer(wg, np.ones(nphi))*(2*np.pi/nphi)
def Y(l,m): return sph_harm_y(l,m,TH,PH)
Yd = {m:Y(2,m) for m in ms}
def ang(k,a,b,c,d):
    s=0
    for q in range(-k,k+1):
        Ykq = Y(k,q)
        I1 = np.sum(W*np.conj(Yd[a])*np.conj(Ykq)*Yd[c])
        I2 = np.sum(W*np.conj(Yd[b])*Ykq*Yd[d])
        s += I1*I2
    return 4*np.pi/(2*k+1)*s
A = {k:np.zeros((5,5,5,5),complex) for k in (2,4)}
for k in (2,4):
    for a,b,c,d in itertools.product(range(5),repeat=4):
        A[k][a,b,c,d]=ang(k,ms[a],ms[b],ms[c],ms[d])

def dets_sub():
    out=[]
    for occ in itertools.combinations(range(NSO),5):
        nup=sum(1 for i in occ if i%2==0); ndn=5-nup
        if nup-ndn==3: out.append(occ)
    return out
basis = dets_sub()
index = {d:i for i,d in enumerate(basis)}
D=len(basis)

def apply_ops(ops, occ):
    occ=list(occ); sign=1
    for typ,o in ops:
        n_less = sum(1 for x in occ if x<o)
        if typ=='a':
            if o not in occ: return None,0
            sign *= (-1)**n_less; occ.remove(o)
        else:
            if o in occ: return None,0
            sign *= (-1)**n_less; occ.append(o); occ.sort()
    return tuple(occ), sign

def build(Vfun):
    M=np.zeros((D,D),complex)
    for col,occ in enumerate(basis):
        for i in range(NSO):
            for j in range(NSO):
                for k in range(NSO):
                    for l in range(NSO):
                        mi,si=divmod(i,2); mj,sj=divmod(j,2)
                        mk,sk=divmod(k,2); ml,sl=divmod(l,2)
                        if si!=sk or sj!=sl: continue
                        v=Vfun(mi,mj,mk,ml)
                        if abs(v)<1e-12: continue
                        new,sg=apply_ops([('a',k),('a',l),('c',j),('c',i)],occ)
                        if new is None or new not in index: continue
                        M[index[new],col]+=0.5*v*sg
    return M
M2=build(lambda a,b,c,d: A[2][a,b,c,d])
M4=build(lambda a,b,c,d: A[4][a,b,c,d])
print("hermitian", np.allclose(M2,M2.conj().T), np.allclose(M4,M4.conj().T), "D=",D)

vec20 = np.zeros(5,complex); vec20[ms.index(0)]=1
vece = np.zeros(5,complex); vece[ms.index(2)]=1/np.sqrt(2); vece[ms.index(-2)]=1/np.sqrt(2)
Peg = np.outer(vec20,vec20.conj())+np.outer(vece,vece.conj())
Wcub = -4*np.eye(5)+10*Peg
H1 = np.zeros((D,D),complex)
for col,occ in enumerate(basis):
    for i in range(NSO):
        for j in range(NSO):
            mi,si=divmod(i,2); mj,sj=divmod(j,2)
            if si!=sj: continue
            v=Wcub[mi,mj]
            if abs(v)<1e-14: continue
            new,sg=apply_ops([('a',j),('c',i)],occ)
            if new is None or new not in index: continue
            H1[index[new],col]+=v*sg
np.savez('ops.npz',H1=H1,M2=M2,M4=M4)
Bt,Ct=1000.,4000.
F4=441*Ct/35; F2=49*Bt+7*Ct
ev=np.linalg.eigvalsh(F2*M2+F4*M4)
print("free-ion levels rel. to lowest (B=1000,C=4000):")
print(np.round(ev-ev[0],1))
EOF
python3 d5.py