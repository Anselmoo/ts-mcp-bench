import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import brentq, least_squares
# angular grid
nt, nphi = 40, 80
xg, wg = np.polynomial.legendre.leggauss(nt)
phis = np.arange(nphi)*2*np.pi/nphi
TH = np.arccos(xg)[:,None]*np.ones((1,nphi)); PH = np.ones((nt,1))*phis[None,:]
W = (wg[:,None]*np.ones((1,nphi)))*(2*np.pi/nphi)
def Y(l,m):  # scipy sph_harm(m, l, azimuth, polar)
    return sph_harm(m,l,PH,TH)
ms=list(range(-2,3)); ls=2
orb=[(ls,m) for m in ms]
# one-electron oct field: point charges at +-x,+-y,+-z, unit distance
nvec=np.stack([np.sin(TH)*np.cos(PH), np.sin(TH)*np.sin(PH), np.cos(TH)],-1)
Rs=[(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]
Vang=np.zeros(TH.shape)
for R in Rs:
    d=np.sqrt(((nvec-np.array(R))**2).sum(-1))
    Vang+=1.0/d
Mlf=np.zeros((5,5),complex)
for i,m in enumerate(ms):
    for j,mp in enumerate(ms):
        Mlf[i,j]=np.sum(W*np.conj(Y(2,m))*Vang*Y(2,mp))
ev=np.sort(np.linalg.eigvalsh(Mlf))
print("LF angular eigenvalues",ev)
# t2g = lower triplet, eg = upper doublet
t2=ev[:3].mean(); eg=ev[3:].mean()
scale=1.0/(eg-t2)  # so that eg-t2g = 1 ; then Dq unit: 10Dq = eg-t2g
h1=(Mlf-t2*np.eye(5))*scale  # eg-t2g=1 ; in units of 10Dq -> Dq = 0.1 * h1 scaled
# Two-electron angular coefficients A_k
def A(k,a,b,c,d):
    # a,b,c,d indices into orb ; <ab|V|cd> = sum_k F^k * A_k
    la,ma=orb[a]; lb,mb=orb[b]; lc,mc=orb[c]; ld,md=orb[d]
    tot=0
    for q in range(-k,k+1):
        Ykq=Y(k,q)
        I1=np.sum(W*np.conj(Y(2,ma))*Ykq*0+W*np.conj(Y(2,ma))*np.conj(Ykq)*Y(2,mc))
        I2=np.sum(W*np.conj(Y(2,mb))*Ykq*Y(2,md))
        tot+=I1*I2
    return 4*np.pi/(2*k+1)*tot
