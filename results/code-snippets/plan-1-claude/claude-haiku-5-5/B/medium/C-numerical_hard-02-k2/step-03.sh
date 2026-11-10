mkdir -p ~/d4 && cd ~/d4 && cat << 'EOF' > d4.py
import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import minimize
from scipy.linalg import eigh
nt, nph = 30, 60
x, w = np.polynomial.legendre.leggauss(nt)
ph = np.arange(nph)*2*np.pi/nph
CT, PH = np.meshgrid(x, ph, indexing='ij')
W = np.outer(w, np.ones(nph))*(2*np.pi/nph)
TH = np.arccos(CT)
ms=[-2,-1,0,1,2]
def Y(l,m,th,phi): return sph_harm(m,l,phi,th)
Yd={m:Y(2,m,TH,PH) for m in ms}
def integ(f): return np.sum(W*f)
X=np.sin(TH)*np.cos(PH); Yy=np.sin(TH)*np.sin(PH); Z=np.cos(TH)
f=X**4+Yy**4+Z**4-0.6
M=np.array([[integ(np.conj(Yd[a])*f*Yd[b]) for b in ms] for a in ms])
ev,U=np.linalg.eigh(M)
print("cubic eig:",np.round(ev,4))
# 3-fold group = the one with 3 degenerate values; with ratio -2:3 the lower-magnitude-weighted; t2g has 3 states
# eigenvalues: eg pair has larger magnitude value (ratio -3/2 of t2g)
order=np.argsort(ev)
lo=ev[order[:3]]; hi=ev[order[3:]]
# t2g is the triple with eigenvalue sign opposite of eg; eg pair has larger |ev|
if abs(np.mean(hi))>abs(np.mean(lo)):
    t2idx=order[:3]; egidx=order[3:]
else:
    t2idx=order[2:]; egidx=order[:2]
t2=U[:,t2idx]; eg=U[:,egidx]
h=-4*t2@t2.conj().T+6*eg@eg.conj().T   # t2g:-4Dq, eg:+6Dq (per Dq unit)
# Fock space
norb=10
def spo(i,s): return 2*i+s  # i in 0..4 (ms index), s spin
# orbital index 'p' 0..9 : p=2*i+s
Nst=2**norb
# Jordan-Wigner annihilation ops as dense on full space is 1024x1024: ok
def ann(p):
    A=np.zeros((Nst,Nst))
    for s in range(Nst):
        if (s>>p)&1:
            s1=s^(1<<p)
            sign=(-1)**bin(s & ((1<<p)-1)).count('1')
            A[s1,s]=sign
    return A
c=[ann(p) for p in range(norb)]
cd=[a.T for a in c]
# N=4 projector
Ns=np.array([bin(s).count('1') for s in range(Nst)])
sel=np.where(Ns==4)[0]
def restrict(A): return A[np.ix_(sel,sel)]
# angular integrals
def akval(k,a,b,cc,d):
    s=0
    for q in range(-k,k+1):
        g1=integ(np.conj(Yd[a])*np.conj(Y(k,q,TH,PH))*Yd[cc])
        g2=integ(np.conj(Yd[b])*Y(k,q,TH,PH)*Yd[d])
        s+=g1*g2
    return 4*np.pi/(2*k+1)*s
def build(F):
    H=np.zeros((Nst,Nst))
    # one-body
    for i in range(5):
        for j in range(5):
            if abs(h[i,j])<1e-14: continue
            for s in (0,1):
                H+= h[i,j]*cd[2*i+s]@c[2*j+s]
    # two-body: 1/2 sum V_{pq,rs} c_p^+ c_q^+ c_s c_r, V_{pq,rs}=<pq|v|rs> with spin conservation
    for p in range(10):
        for q in range(10):
            for r in range(10):
                for s_ in range(10):
                    ip,sp_=divmod(p,2); iq,sq=divmod(q,2); ir,sr=divmod(r,2); is_,ss=divmod(s_,2)
                    if sp_!=sr or sq!=ss: continue
                    val=sum(Fk*akval(k,ip+0,iq,ir,is_) for k,Fk in F.items())
                    # ip index mapping: orbital index i in ms list = ip (0..4)
                    if abs(val)<1e-12: continue
                    H+=0.5*val*cd[p]@cd[q]@c[s_]@c[r]
    return H
EOF
python3 -c "
import sys; sys.path.insert(0,'.')
import d4; print('ok')"