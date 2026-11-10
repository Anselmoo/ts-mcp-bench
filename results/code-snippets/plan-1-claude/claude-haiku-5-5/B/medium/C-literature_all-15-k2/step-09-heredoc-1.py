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
A={k:np.zeros((5,5,5,5)) for k in (0,2,4)}
for k in (0,2,4):
    for a,b,c,d in itertools.product(range(5),repeat=4):
        A[k][a,b,c,d]=np.real(ang(k,vals[a],vals[b],vals[c],vals[d]))
# Known d-orbital Slater ratio check: <m=2,m=-2 > etc. Print a2 for (xy,xy)=? and a4(xy,xy)
print("a2 xy-xy",A[2][0,0,0,0],"a4 xy-xy",A[4][0,0,0,0],"a4 xy-z2 pair",A[4][0,4,0,4], "a2 xy,z2",A[2][0,4,0,4])
