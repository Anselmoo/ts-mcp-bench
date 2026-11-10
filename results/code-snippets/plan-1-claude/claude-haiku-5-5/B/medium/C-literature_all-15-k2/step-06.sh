cat << 'EOF' | python3 -
import numpy as np, itertools
from scipy.special import sph_harm_y
nt, nphi = 30, 60
x, w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.arange(nphi)*2*np.pi/nphi
TH, PH = np.meshgrid(th, ph, indexing='ij')
W = np.outer(w, np.full(nphi, 2*np.pi/nphi))
X=np.sin(TH)*np.cos(PH); Yc=np.sin(TH)*np.sin(PH); Z=np.cos(TH)
raw=[X*Yc, Yc*Z, X*Z, X**2-Yc**2, 3*Z**2-1]
vals=np.array([v/np.sqrt(np.sum(W*v*v)) for v in raw])
def ang(k,a,b,c,d):
    s=0
    for q in range(-k,k+1):
        Yk=np.conj(sph_harm_y(k,q,TH,PH))
        s+= np.sum(W*a*c*Yk)*np.conj(np.sum(W*b*d*Yk))
    return 4*np.pi/(2*k+1)*s
for k in (2,4):
    A=np.array([[[[np.real(ang(k,vals[a],vals[b],vals[a],vals[b])) for b in range(5)] for a in range(5)]]])
    M=np.array([[np.real(ang(k,vals[a],vals[b],vals[a],vals[b])) for b in range(5)] for a in range(5)])
    print(k, np.round(M,5), "row sums", np.round(M.sum(1),8))
EOF