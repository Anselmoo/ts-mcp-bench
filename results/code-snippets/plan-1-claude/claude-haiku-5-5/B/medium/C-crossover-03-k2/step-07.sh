python3 - << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y
nth,nph=40,80
x,w=np.polynomial.legendre.leggauss(nth); th=np.arccos(x); ph=np.arange(nph)*2*np.pi/nph
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.ones(nph))*(2*np.pi/nph)
ms=range(-2,3); Yd={m:sph_harm_y(2,m,TH,PH) for m in ms}
mx=0
for m1,m2,m3,m4 in itertools.product(ms,repeat=4):
    tot=0
    for k in (2,4):
        s=0
        for q in range(-k,k+1):
            Yk=sph_harm_y(k,q,TH,PH)
            s+=np.sum(W*np.conj(Yd[m1])*np.conj(Yk)*Yd[m3])*np.sum(W*np.conj(Yd[m2])*Yk*Yd[m4])
        tot+=s
    mx=max(mx,abs(tot.imag))
print("max imag of angular sum", mx)
EOF