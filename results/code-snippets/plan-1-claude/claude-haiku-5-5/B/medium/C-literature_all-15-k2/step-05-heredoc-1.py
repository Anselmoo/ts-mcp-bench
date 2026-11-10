import numpy as np, itertools
from scipy.special import sph_harm_y
nt, nphi = 30, 60
x, w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.arange(nphi)*2*np.pi/nphi
TH, PH = np.meshgrid(th, ph, indexing='ij')
W = np.outer(w, np.full(nphi, 2*np.pi/nphi))
X=np.sin(TH)*np.cos(PH); Yc=np.sin(TH)*np.sin(PH); Z=np.cos(TH)
raw=[X*Yc, Yc*Z, X*Z, X**2-Yc**2, 3*Z**2-1]
vals=[]
for v in raw:
    v=v/np.sqrt(np.sum(W*v*v)); vals.append(v)
vals=np.array(vals)
G=np.array([[np.sum(W*a*b) for b in vals] for a in vals]); print(np.round(G,8))
def Ykq(k,q): return sph_harm_y(k,q,TH,PH)
def ang(k,a,b,c,d):
    s=0
    for q in range(-k,k+1):
        Yk=np.conj(Ykq(k,q))
        Xac=np.sum(W*a*c*Yk)
        Xbd=np.sum(W*b*d*Yk)
        s+= Xac*np.conj(Xbd)
    return 4*np.pi/(2*k+1)*s
A={}
for k in (0,2,4):
    A[k]=np.zeros((5,5,5,5))
    for a,b,c,d in itertools.product(range(5),repeat=4):
        A[k][a,b,c,d]=np.real(ang(k,vals[a],vals[b],vals[c],vals[d]))
print("A0 diag check", A[0][0,0,0,0], A[0][0,1,0,1], A[0][0,0,1,1])
print("A2 check", A[2][3,3,3,3], A[4][3,3,3,3])
np.save('/dev/null',0) if False else None
import pickle,sys
