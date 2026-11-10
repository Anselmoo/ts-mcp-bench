
cd /tmp && python3 - <<'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y
from numpy.polynomial.legendre import leggauss
nt,npn=40,80
x,wt=leggauss(nt); th=np.arccos(x); ph=np.arange(npn)*2*np.pi/npn; wp=2*np.pi/npn
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(wt,np.ones(npn))*wp
def Y(l,m): return sph_harm_y(l,m,TH,PH)
ms=list(range(-2,3))
Yd={m:Y(2,m) for m in ms}
print('norm', np.sum(W*np.abs(Yd[2])**2))
def ang(k,a,b,c,d):
    s=0
    for q in range(-k,k+1):
        g1=np.sum(W*np.conj(Yd[a])*Yd[c]*np.conj(Y(k,q)))
        g2=np.sum(W*np.conj(Yd[b])*Yd[d]*Y(k,q))
        s+=g1*g2
    return 4*np.pi/(2*k+1)*s
print('a0', ang(0,0,0,0,0), ang(0,2,-1,2,-1))
ANG={}
for k in (0,2,4):
    for a,b,c,d in itertools.product(ms,repeat=4):
        v=ang(k,a,b,c,d)
        if abs(v)>1e-10: ANG[(k,a,b,c,d)]=v
import pickle; pickle.dump(ANG,open('/tmp/ang.pkl','wb'))
print(len(ANG), ANG.get((0,0,0,0,0)), ANG.get((2,2,-2,-2,2)))
EOF
