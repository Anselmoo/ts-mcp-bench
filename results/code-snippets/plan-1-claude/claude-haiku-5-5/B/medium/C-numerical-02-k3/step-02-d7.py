import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import least_squares
nt, nph = 40, 80
x, w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.linspace(0, 2*np.pi, nph, endpoint=False)
TH, PH = np.meshgrid(th, ph, indexing='ij'); W = np.outer(w, np.full(nph, 2*np.pi/nph))
X = np.sin(TH)*np.cos(PH); Y = np.sin(TH)*np.sin(PH); Z = np.cos(TH)
r = {'xy':np.sqrt(15/(4*np.pi))*X*Y,'yz':np.sqrt(15/(4*np.pi))*Y*Z,'zx':np.sqrt(15/(4*np.pi))*Z*X,
     'x2y2':np.sqrt(15/(16*np.pi))*(X**2-Y**2),'z2':np.sqrt(5/(16*np.pi))*(3*Z**2-1)}
names=['xy','yz','zx','x2y2','z2']
def Ylm(l,m): return sph_harm(m, l, PH, TH)
Ak={}
for k in [0,2,4]:
    T=np.zeros((5,5,5,5))
    for q in range(-k,k+1):
        Mac=np.array([[np.sum(W*r[a]*r[c]*np.conj(Ylm(k,q))) for c in names] for a in names])
        Mbd=np.array([[np.sum(W*r[b]*r[d]*Ylm(k,q)) for d in names] for b in names])
        T+=4*np.pi/(2*k+1)*np.einsum('ac,bd->abcd',Mac,Mbd)
    Ak[k]=T
np.save('Ak.npy', np.stack([Ak[0],Ak[2],Ak[4]]))
print('done', np.abs(Ak[0]).max(), np.abs(Ak[2]).max(), np.abs(Ak[4]).max())
