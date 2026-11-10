mkdir -p /tmp/w && cat > /tmp/w/ligand.py << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm
nt, nphi = 40, 80
xg, wg = np.polynomial.legendre.leggauss(nt)
phis = np.arange(nphi)*2*np.pi/nphi
TH = np.arccos(xg)[:,None]*np.ones((1,nphi)); PH = np.ones((nt,1))*phis[None,:]
W = (wg[:,None]*np.ones((1,nphi)))*(2*np.pi/nphi)
def Y(l,m): return sph_harm(m,l,PH,TH)
ms=list(range(-2,3))
nvec=np.stack([np.sin(TH)*np.cos(PH), np.sin(TH)*np.sin(PH), np.cos(TH)],-1)
Rs=[(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]
Vang=np.zeros(TH.shape)
for R in Rs:
    d=np.sqrt(((nvec-np.array(R))**2).sum(-1)); Vang+=1.0/d
Mlf=np.zeros((5,5),complex)
for i,m in enumerate(ms):
    for j,mp in enumerate(ms):
        Mlf[i,j]=np.sum(W*np.conj(Y(2,m))*Vang*Y(2,mp))
ev=np.sort(np.linalg.eigvalsh(Mlf))
t2=ev[:3].mean(); eg=ev[3:].mean()
h1=(Mlf-t2*np.eye(5))/(eg-t2)   # eg - t2g = 1 (i.e. 10Dq=1 unit) ; Dq-unit: h1*10Dq
print("LF eig", ev, "t2g,eg diag check", np.round(np.linalg.eigvalsh(h1),6))
# Two-electron angular coefficients
Yc={(k,q):Y(k,q) for k in range(0,5,2) for q in range(-k,k+1)}
def Ak(k,ma,mb,mc,md):
    tot=0
    for q in range(-k,k+1):
        Ykq=Yc[(k,q)]
        I1=np.sum(W*np.conj(Y(2,ma))*np.conj(Ykq)*Y(2,mc))
        I2=np.sum(W*np.conj(Y(2,mb))*Ykq*Y(2,md))
        tot+=I1*I2
    return 4*np.pi/(2*k+1)*tot
# precompute V[k][a,b,c,d]
V={}
for k in (0,2,4):
    T=np.zeros((5,5,5,5),complex)
    for a,b,c,d in itertools.product(range(5),repeat=4):
        T[a,b,c,d]=Ak(k,ms[a],ms[b],ms[c],ms[d])
    V[k]=T
np.save('/tmp/w/h1.npy',h1)
for k in V: np.save(f'/tmp/w/V{k}.npy',V[k])
print("done")
EOF
cd /tmp/w && python3 ligand.py