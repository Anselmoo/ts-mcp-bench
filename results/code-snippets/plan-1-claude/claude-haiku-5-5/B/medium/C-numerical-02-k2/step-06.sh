cat > /dev/null << 'EOF'
EOF
python3 - << 'EOF'
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
print("LF eig", ev)
EOF