cd /tmp && cat > /tmp/chk.py << 'EOF'
import numpy as np, time
from scipy.special import sph_harm
t=time.time()
xg, wg = np.polynomial.legendre.leggauss(16)
phis = np.linspace(0, 2*np.pi, 32, endpoint=False); wp = 2*np.pi/32
TH, PH = np.meshgrid(np.arccos(xg), phis, indexing='ij')
W = np.outer(wg, np.full(len(phis), wp))
Ycache={(l,m): sph_harm(m,l,PH,TH) for l in (2,4) for m in range(-l,l+1)}
print(time.time()-t)
EOF
timeout 100 python3 /tmp/chk.py