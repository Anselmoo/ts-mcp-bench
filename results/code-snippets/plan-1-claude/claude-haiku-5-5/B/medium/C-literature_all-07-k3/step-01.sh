
cat << 'EOF' > /tmp/d5.py
import numpy as np, itertools
from scipy.special import sph_harm
from numpy.polynomial.legendre import leggauss
# quadrature on sphere
nu,wu=leggauss(30); nphi=64
th=np.arccos(nu); ph=np.arange(nphi)*2*np.pi/nphi
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=(wu[:,None]*np.ones((1,nphi)))*(2*np.pi/nphi)
def Y(l,m): return sph_harm(m,l,PH,TH)   # scipy: sph_harm(m,n,azimuth,polar)
d=[Y(2,m) for m in range(-2,3)]
def ip(f,g): return np.sum(W*np.conj(f)*g)
# cubic ligand field operator f = x^4+y^4+z^4 - 3/5
x=np.sin(TH)*np.cos(PH); y=np.sin(TH)*np.sin(PH); z=np.cos(TH)
fop=x**4+y**4+z**4-0.6
M=np.array([[ip(d[a],fop*d[b]) for b in range(5)] for a in range(5)])
ev=np.linalg.eigvalsh(M); print("LF eig",np.round(ev,5))
# angular T^k_q
F=lambda k: None
def ee_angular(k):
    out={}
    for q in range(-k,k+1):
        Yk=Y(k,q)
        out[q]=np.array([[np.sum(W*np.conj(d[a])*Yk*d[c]) for c in range(5)] for a in range(5)])
    return out
ang={k:ee_angular(k) for k in (0,2,4)}
# Slater integrals F0,F2,F4 symbolic; V tensor as function of (F0,F2,F4)
def Vtensor(Fk):
    V=np.zeros((5,5,5,5),complex)  # <ab|1/r12|cd>
    for k in (0,2,4):
        pref=4*np.pi/(2*k+1)*Fk[k]
        for q in range(-k,k+1):
            # <ab|..|cd> : T(a,c) conj(Y_kq)-part, U(b,d)
            # use: sum_q [ int conj(a) conj(Yk_q) c ] [ int conj(b) Yk_q d ]
            A=ang[k][-q] if False else None
    return V
# simpler direct: compute numerically with conj convention
def Vt(Fk):
    V=np.zeros((5,5,5,5),complex)
    for k in (0,2,4):
        Yks={q:Y(k,q) for q in range(-k,k+1)}
        pref=4*np.pi/(2*k+1)*Fk[k]
        for q in range(-k,k+1):
            Ap=np.array([[np.sum(W*np.conj(d[a])*np.conj(Yks[q])*d[c]) for c in range(5)] for a in range(5)])
            Bp=np.array([[np.sum(W*np.conj(d[b])*Yks[q]*d[dd]) for dd in range(5)] for b in range(5)])
            V+=pref*np.einsum('ac,bd->abcd',Ap,Bp)
    return V
np.save('/tmp/M.npy',M)
import pickle
pickle.dump((M,),open('/tmp/M.pkl','wb'))
# store per-k tensors
Tk={}
for k in (0,2,4):
    Yks={q:Y(k,q) for q in range(-k,k+1)}
    Tk[k]={}
    for q in range(-k,k+1):
        Ap=np.array([[np.sum(W*np.conj(d[a])*np.conj(Yks[q])*d[c]) for c in range(5)] for a in range(5)])
        Bp=np.array([[np.sum(W*np.conj(d[b])*Yks[q]*d[dd]) for dd in range(5)] for b in range(5)])
        Tk[k][q]=(Ap,Bp)
pickle.dump((M,Tk),open('/tmp/data.pkl','wb'))
print("done")
EOF
python3 /tmp/d5.py
