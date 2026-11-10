python3 - << 'EOF'
import numpy as np
from scipy.special import sph_harm_y
xg,wg=np.polynomial.legendre.leggauss(30)
nphi=60
ph=np.arange(nphi)*2*np.pi/nphi
TH,PH=np.meshgrid(np.arccos(xg),ph,indexing='ij')
W=(wg[:,None]*np.ones(nphi)[None,:])*(2*np.pi/nphi)
x=np.sin(TH)*np.cos(PH); y=np.sin(TH)*np.sin(PH); z=np.cos(TH)
orbs={'xy':x*y,'yz':y*z,'zx':z*x,'x2y2':x*x-y*y,'z2':3*z*z-1}
names=list(orbs)
for n in names:
    orbs[n]=orbs[n]/np.sqrt(np.sum(W*orbs[n]**2))
def sph(l,m,TH,PH): return sph_harm_y(l,m,TH,PH)
def realY(l,m,TH,PH):
    if m==0: return sph(l,0,TH,PH).real
    if m>0: return np.sqrt(2)*(-1)**m*sph(l,m,TH,PH).real
    return np.sqrt(2)*(-1)**m*sph(l,-m,TH,PH).imag
def Vang(k):
    Yk=[realY(k,q,TH,PH) for q in range(-k,k+1)]
    M=np.zeros((5,5,len(Yk)))
    for i,a in enumerate(names):
        for j,c in enumerate(names):
            for q,Y in enumerate(Yk):
                M[i,j,q]=np.sum(W*orbs[a]*orbs[c]*Y)
    return np.einsum('acq,bdq->acbd',M,M)*4*np.pi/(2*k+1)
A2=Vang(2);A4=Vang(4)
print("norm", np.sum(W*realY(2,1,TH,PH)**2), np.sum(W*realY(2,-2,TH,PH)**2))
np.save('/tmp/tsbench-run-0_bugcww/A2.npy',A2) if False else None
import pickle
pickle.dump((A2,A4,names),open('/tmp/A.pkl','wb')) 
print("ok")
EOF