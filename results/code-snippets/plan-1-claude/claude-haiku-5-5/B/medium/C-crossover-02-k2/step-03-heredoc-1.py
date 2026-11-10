import numpy as np, itertools
from scipy.special import lpmv, factorial
from math import pi, sqrt
B,C=621.0,2851.0
F2=49*B+7*C; F4=441*C/35.0
Fk={2:F2,4:F4}
xg,wg=np.polynomial.legendre.leggauss(30)
nphi=40
phis=np.arange(nphi)*2*pi/nphi
TH,PH=np.meshgrid(np.arccos(xg),phis,indexing='ij')
W=np.outer(wg,np.ones(nphi))*(2*pi/nphi)
def Ylm(l,m,th,ph):
    am=abs(m)
    norm=sqrt((2*l+1)/(4*pi)*factorial(l-am)/factorial(l+am))
    val=norm*lpmv(am,l,np.cos(th))*np.exp(1j*am*ph)
    if m<0: val=((-1)**am)*np.conj(val)
    return val
ms=list(range(-2,3))
Ym={m:Ylm(2,m,TH,PH) for m in ms}
Vc=np.zeros((5,5,5,5),complex)
for k in (2,4):
    for q in range(-k,k+1):
        Ykq=Ylm(k,q,TH,PH)
        A=np.array([[np.sum(W*np.conj(Ym[m1])*np.conj(Ykq)*Ym[m3]) for m3 in ms] for m1 in ms])
        Bm=np.array([[np.sum(W*np.conj(Ym[m2])*Ykq*Ym[m4]) for m4 in ms] for m2 in ms])
        Vc+= Fk[k]*4*pi/(2*k+1)*np.einsum('ac,bd->abcd',A,Bm)
x=np.sin(TH)*np.cos(PH); y=np.sin(TH)*np.sin(PH); z=np.cos(TH)
funcs=[x*y, x*z, y*z, x*x-y*y, 2*z*z-x*x-y*y]
U=np.zeros((5,5),complex)
for i,f in enumerate(funcs):
    nrm=np.sqrt(np.sum(W*f*f))
    for j,m in enumerate(ms):
        U[i,j]=np.sum(W*np.conj(Ym[m])*f)/nrm
print("UU^dag-I max:",np.abs(U@U.conj().T-np.eye(5)).max())
print("Vc sample:",Vc[2,2,2,2].real)
