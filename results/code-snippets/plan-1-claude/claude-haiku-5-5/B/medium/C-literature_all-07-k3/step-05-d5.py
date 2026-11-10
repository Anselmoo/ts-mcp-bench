import numpy as np
from scipy.special import sph_harm
from numpy.polynomial.legendre import leggauss
nu,wu=leggauss(30); nphi=64
th=np.arccos(nu); ph=np.arange(nphi)*2*np.pi/nphi
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=(wu[:,None]*np.ones((1,nphi)))*(2*np.pi/nphi)
def Y(l,m): return sph_harm(m,l,PH,TH)
d=[Y(2,m) for m in range(-2,3)]
def ip(f,g): return np.sum(W*np.conj(f)*g)
x=np.sin(TH)*np.cos(PH); y=np.sin(TH)*np.sin(PH); z=np.cos(TH)
fop=x**4+y**4+z**4-0.6
M=np.array([[ip(d[a],fop*d[b]) for b in range(5)] for a in range(5)])
ev=np.linalg.eigvalsh(M); print("LF eig",np.round(ev,6), "trace",np.trace(M).real)
H1=M.real*(10/(ev[-1]-ev[0]))
print("H1 eig",np.round(np.linalg.eigvalsh(H1),6))
Vk={}
for k in (0,2,4):
    T=np.zeros((5,5,5,5),complex)
    for q in range(-k,k+1):
        Yq=Y(k,q)
        Ap=np.array([[np.sum(W*np.conj(d[a])*np.conj(Yq)*d[c]) for c in range(5)] for a in range(5)])
        Bp=np.array([[np.sum(W*np.conj(d[b])*Yq*d[e]) for e in range(5)] for b in range(5)])
        T+=4*np.pi/(2*k+1)*np.einsum('ac,bd->abcd',Ap,Bp)
    Vk[k]=T
np.savez('data.npz',H1=H1,V0=Vk[0],V2=Vk[2],V4=Vk[4])
print("saved", np.abs(Vk[0]).max())
