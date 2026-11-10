
mkdir -p /tmp/tsbench-home-xehwqch9/w && cd /tmp/tsbench-home-xehwqch9/w && cat << 'EOF' > d5.py
import numpy as np, itertools
from scipy.special import sph_harm
from numpy.polynomial.legendre import leggauss
from scipy.linalg import eigh
nu,wu=leggauss(30); nphi=64
th=np.arccos(nu); ph=np.arange(nphi)*2*np.pi/nphi
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=(wu[:,None]*np.ones((1,nphi)))*(2*np.pi/nphi)
def Y(l,m): return sph_harm(m,l,PH,TH)
ms=list(range(-2,3))
d=[Y(2,m) for m in ms]
def ip(f,g): return np.sum(W*np.conj(f)*g)
x=np.sin(TH)*np.cos(PH); y=np.sin(TH)*np.sin(PH); z=np.cos(TH)
fop=x**4+y**4+z**4-0.6
M=np.array([[ip(d[a],fop*d[b]) for b in range(5)] for a in range(5)])
ev,U=np.linalg.eigh(M); print("LF eig",np.round(ev,5))
# one-electron cubic LF matrix: t2g=-4Dq, eg=+6Dq ; eigen of M: lower triplet?
# scale: H1 = s*M, with s so that (eg - t2g)=10 Dq ; set Dq=1 units
t2=[i for i in range(5) if ev[i]<0]; 
# identify: M eigen values -a (x3), +b(x2) with traceless
a=-ev[0]; b=ev[-1]
s=10/(ev[-1]-ev[0])  # eg-t2g = 10 Dq  -> H = s*M gives t2g=ev0*s, eg=ev4*s
H1=M*( (10)/( (ev[-1]-ev[0]) ))   # per unit Dq: eg - t2g = 10
# check: t2g value = ev[0]*10/(ev[-1]-ev[0]); need -4 => fix
print("t2g,eg per unit:", ev[0]*s, ev[-1]*s)
# rescale so that t2g=-4, eg=+6
H1 = M*(10/(ev[-1]-ev[0]))
# shift to make traceless already (M traceless? )
print("trace M",np.trace(M))
Tk={}
for k in (0,2,4):
    Yks={q:Y(k,q) for q in range(-k,k+1)}
    Tk[k]={}
    for q in range(-k,k+1):
        Ap=np.array([[np.sum(W*np.conj(d[a])*np.conj(Yks[q])*d[c]) for c in range(5)] for a in range(5)])
        Bp=np.array([[np.sum(W*np.conj(d[b])*Yks[q]*d[dd]) for dd in range(5)] for b in range(5)])
        Tk[k][q]=(Ap,Bp)
# two-electron tensor per Fk: V[a,b,c,d] = sum_k 4pi/(2k+1) F^k sum_q Ap*Bp
Vk={}
for k in (0,2,4):
    T=np.zeros((5,5,5,5),complex)
    for q in Tk[k]:
        Ap,Bp=Tk[k][q]
        T+=4*np.pi/(2*k+1)*np.einsum('ac,bd->abcd',Ap,Bp)
    Vk[k]=T
np.savez('/tmp/tsbench-home-xehwqch9/w/data.npz',H1=H1,V0=Vk[0],V2=Vk[2],V4=Vk[4],M=M)
print("saved")
EOF
python3 d5.py