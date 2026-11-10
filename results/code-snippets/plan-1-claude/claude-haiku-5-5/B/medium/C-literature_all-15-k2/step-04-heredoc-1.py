import numpy as np, itertools
from scipy.special import sph_harm
nt, nphi = 40, 80
x, w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.arange(nphi)*2*np.pi/nphi
TH, PH = np.meshgrid(th, ph, indexing='ij')
W = np.outer(w, np.full(nphi, 2*np.pi/nphi))
def Y(l,m,T,P): return sph_harm(m, l, P, T)
s=1/np.sqrt(2)
raw=[
 (Y(2,-2,TH,PH)-Y(2,2,TH,PH))*1j*s,
 (Y(2,-1,TH,PH)+Y(2,1,TH,PH))*(-s),
 (Y(2,-1,TH,PH)-Y(2,1,TH,PH))*1j*s,
 (Y(2,-2,TH,PH)+Y(2,2,TH,PH))*s,
 Y(2,0,TH,PH)]
vals=[]
for v in raw:
    v=np.array(v,dtype=complex)
    ph_=np.sum(W*v*np.conj(v))
    # remove global phase so that it's real
    idx=np.argmax(np.abs(v)); v=v*np.conj(v.flat[idx])/abs(v.flat[idx])
    assert np.abs(v.imag).max()<1e-9
    v=v.real
    v=v/np.sqrt(np.sum(W*v*v))
    vals.append(v)
vals=np.array(vals)
G=np.array([[np.sum(W*a*b) for b in vals] for a in vals])
print(np.round(G,6))
