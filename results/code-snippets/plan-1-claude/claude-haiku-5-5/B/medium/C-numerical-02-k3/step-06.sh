
cd /tmp/tsbench-run-zqezmkn7 && timeout 100 python3 -c "
import numpy as np
from scipy.special import sph_harm_y
nt, nph = 40, 80
x, w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.linspace(0, 2*np.pi, nph, endpoint=False)
TH, PH = np.meshgrid(th, ph, indexing='ij'); W = np.outer(w, np.full(nph, 2*np.pi/nph))
X = np.sin(TH)*np.cos(PH); Y = np.sin(TH)*np.sin(PH); Z = np.cos(TH)
r = {'xy':np.sqrt(15/(4*np.pi))*X*Y,'yz':np.sqrt(15/(4*np.pi))*Y*Z,'zx':np.sqrt(15/(4*np.pi))*Z*X,'x2y2':np.sqrt(15/(16*np.pi))*(X**2-Y**2),'z2':np.sqrt(5/(16*np.pi))*(3*Z**2-1)}
names=['xy','yz','zx','x2y2','z2']
print([round(float(np.sum(W*r[a]**2)),4) for a in names])
"