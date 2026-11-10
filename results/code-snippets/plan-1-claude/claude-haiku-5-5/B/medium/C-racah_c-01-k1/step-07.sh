cat > /tmp/dbg.py << 'EOF'
exec(open('/dev/stdin').read()) if False else None
EOF
python3 - << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y
ms=[-2,-1,0,1,2]
xg,wg=np.polynomial.legendre.leggauss(30)
nphi=60
phis=np.arange(nphi)*2*np.pi/nphi
TH,PH=np.meshgrid(np.arccos(xg),phis,indexing='ij')
W=np.outer(wg,np.ones(nphi))*(2*np.pi/nphi)
Y=lambda l,m,th,ph: sph_harm_y(l,m,th,ph)
D=[Y(2,m,TH,PH) for m in ms]
# check orthonormality of D
G=np.array([[np.sum(W*np.conj(D[a])*D[b]) for b in range(5)] for a in range(5)])
print(np.round(G,6))
# check Ykq normalization / 1/r expansion coefficient for k=2 via Legendre test
EOF