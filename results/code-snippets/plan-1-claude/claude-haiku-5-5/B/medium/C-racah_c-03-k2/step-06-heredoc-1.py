import numpy as np, itertools
from scipy.special import sph_harm_y
ms=[-2,-1,0,1,2]
s2=np.sqrt(2)
def vec(d): return np.array([d.get(m,0) for m in ms],complex)
dz2=vec({0:1}); dxz=vec({1:-1/s2,-1:1/s2}); dyz=vec({1:-1j/s2,-1:-1j/s2})
dx2=vec({2:1/s2,-2:1/s2}); dxy=vec({2:-1j/s2,-2:1j/s2})
P=np.zeros((5,5),complex)
for v in [dz2,dx2]: P+=6*np.outer(v,np.conj(v))
for v in [dxz,dyz,dxy]: P+=-4*np.outer(v,np.conj(v))
print(np.round(np.linalg.eigvalsh(P),6))
