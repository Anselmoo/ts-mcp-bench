cd ~ 2>/dev/null && pwd; mkdir -p ~/d6 && cd ~/d6 && cat << 'EOF' > d6.py
import numpy as np, itertools
from scipy.optimize import brentq

xg, wg = np.polynomial.legendre.leggauss(14)
nphi=28
pts=[]; ws=[]
for ct, w in zip(xg, wg):
    st=np.sqrt(1-ct*ct)
    for ph in np.linspace(0,2*np.pi,nphi,endpoint=False):
        pts.append([st*np.cos(ph), st*np.sin(ph), ct]); ws.append(w*2*np.pi/nphi)
P=np.array(pts); W=np.array(ws)
x,y,z=P.T
funcs=[x*y, y*z, x*z, 2*z*z-x*x-y*y, x*x-y*y]
F=[]
for f in funcs:
    n=np.sum(W*f*f); F.append(f/np.sqrt(n))
F=np.array(F)
g=np.clip(P@P.T,-1,1)
def legP(k,c): return np.polynomial.legendre.Legendre.basis(k)(c)
A=F*W
# Ik[k][a,c,b,d] = sum_{p,q} f_a(p) f_c(p) W_p * P_k(p.q) * f_b(q) f_d(q) W_q  (electron1: a,c ; electron2: b,d)
Ik={}
for k in [0,2,4]:
    M=legP(k,g)
    Ik[k]=np.einsum('ap,cp,pq,bq,dq->acbd', A, F, M, A, F, optimize=True)
    # sanity: here A has W, second F... fix below
EOF
python3 d6.py && echo ok