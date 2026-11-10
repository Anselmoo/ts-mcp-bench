
cd /dev/shm && sed -i 's/from scipy.special import sph_harm/from scipy.special import sph_harm_y/; s/def Ylm(l,m): return sph_harm(m,l,PH,TH)/def Ylm(l,m): return sph_harm_y(l,m,TH,PH)/' d3.py && python3 -c "
import sys;sys.path.insert(0,'/dev/shm');import d3,numpy as np
M=d3.build(1.0,0.0,0.0)
print('herm',np.allclose(M,M.T.conj()))
print(np.round(np.linalg.eigvalsh(d3.S2),3)[::1][:5], np.unique(np.round(np.linalg.eigvalsh(d3.S2),3)))
print(np.round(d3.A[2][0,0,0,0],4), np.round(d3.A[2][2,2,2,2],4))
"