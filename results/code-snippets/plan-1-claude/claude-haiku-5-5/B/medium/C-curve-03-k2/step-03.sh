
cd /tmp && python3 - <<'EOF'
import numpy as np, itertools
from scipy.special import sph_harm
from numpy.polynomial.legendre import leggauss
# quadrature
nt,npn=40,80
x,wt=leggauss(nt); th=np.arccos(x); ph=np.arange(npn)*2*np.pi/npn; wp=2*np.pi/npn
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(wt,np.ones(npn))*wp
def Y(l,m): return sph_harm(m,l,PH,TH)
ms=list(range(-2,3))
Yd={m:Y(2,m) for m in ms}
def gaunt_k(k,a,c):
    # returns dict q-> integral Y_a^* Y_c Y_kq^*  (integrate over sphere)
    out={}
    for q in range(-k,k+1):
        out[q]=np.sum(W*np.conj(Yd[a])*Yd[c]*np.conj(Y(k,q)))
    return out
def ang(k,a,b,c,d):
    # <a b|1/r12|c d>/F^k angular: 4pi/(2k+1) sum_q g(a,c,q) * g(b,d,-q)... use conj for electron2 consistent
    g1=gaunt_k(k,a,c); g2={}
    # electron2: Y_b^* Y_d Y_kq (since 1/r has Y_kq^*(1) Y_kq(2))
    for q in range(-k,k+1):
        g2[q]=np.sum(W*np.conj(Yd[b])*Yd[d]*Y(k,q))
    return 4*np.pi/(2*k+1)*sum(g1[q]*g2[q] for q in range(-k,k+1))
# check normalization of Yd
print('norm', np.sum(W*np.abs(Yd[2])**2))
# check: ang(0,a,a,a,a)=1 ?  
print('a0 same', ang(0,0,0,0,0), ang(0,2,-1,2,-1))
# F^k ang coefficients table for d orbitals
ANG={}
for k in (0,2,4):
    for a,b,c,d in itertools.product(ms,repeat=4):
        v=ang(k,a,b,c,d)
        if abs(v)>1e-12: ANG[(k,a,b,c,d)]=v.real
import pickle
pickle.dump(ANG,open('/tmp/ang.pkl','wb'))
print(len(ANG))
EOF
