mkdir -p /w && cat > /w/d3.py << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.optimize import brentq, fsolve
l=2
# quadrature
xg,wg=np.polynomial.legendre.leggauss(30)
phis=np.linspace(0,2*np.pi,60,endpoint=False); wp=2*np.pi/60
TH,PH=np.meshgrid(np.arccos(xg),phis,indexing='ij'); W=np.outer(wg,np.ones(len(phis)))*wp
ms=list(range(-2,3))
def Y(lm,th,ph): return sph_harm_y(lm[0],lm[1],th,ph)
Yc={m:Y((2,m),TH,PH) for m in ms}
def g(k,q,a,c):  # int conj(Y_a) Y_c conj(Y_kq)
    Ykq=Y((k,q),TH,PH) if abs(q)<=k else None
    return np.sum(W*np.conj(Yc[a])*Yc[c]*np.conj(Ykq))
# complex two-electron tensor, F^k factored out: V = sum_k F^k * coeff_k
Vc={k:np.zeros((5,5,5,5),complex) for k in (0,2,4)}
for k in (0,2,4):
  for ia,a in enumerate(ms):
    for ic,c in enumerate(ms):
      for ib,b in enumerate(ms):
        for id_,d in enumerate(ms):
          s=0
          for q in range(-k,k+1):
            s+=g(k,q,a,c)*np.sum(W*np.conj(Yc[b])*Yc[d]*Y((k,q),TH,PH))
          Vc[k][ia,ib,ic,id_]=4*np.pi/(2*k+1)*s
# real orbital transform: phi_a = sum_m U[a,m] Y_m
s2=np.sqrt(2)
# order: xy,yz,xz,z2,x2-y2 ; Y_m index m+2
U=np.zeros((5,5),complex)
def setU(name,terms):
    i=['xy','yz','xz','z2','x2y2'].index(name)
    for m,cf in terms: U[i,m+2]=cf
setU('xy',[(-2,1/(1j*s2)),(2,-1/(1j*s2))])
setU('yz',[(-1,1/(1j*s2)),(1,1/(s2))*0+(1,1/(1j*s2))*0+(1,1/(1j*s2))])
EOF
echo