import numpy as np, itertools
import scipy.sparse as sps
from scipy.special import sph_harm
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
order=np.argsort(ev)
lo=ev[order[:3]]; hi=ev[order[3:]]
if abs(np.mean(hi))>abs(np.mean(lo)):
    t2idx=order[:3]; egidx=order[3:]
else:
    t2idx=order[2:]; egidx=order[:2]
t2=U[:,t2idx]; eg=U[:,egidx]
h=-4*t2@t2.conj().T+6*eg@eg.conj().T
norb=10; Nst=2**norb
def ann(p):
    rows=[];cols=[];vals=[]
    for s in range(Nst):
        if (s>>p)&1:
            s1=s^(1<<p)
            sign=(-1)**bin(s & ((1<<p)-1)).count('1')
            rows.append(s1); cols.append(s); vals.append(sign)
    return sps.csr_matrix((vals,(rows,cols)),shape=(Nst,Nst))
c=[ann(p) for p in range(norb)]
cd=[a.T.tocsr() for a in c]
Ns=np.array([bin(s).count('1') for s in range(Nst)])
sel=np.where(Ns==4)[0]
# angular integrals cache
from functools import lru_cache
@lru_cache(None)
def akval(k,a,b,cc,d):
    s=0
    for q in range(-k,k+1):
        g1=integ(np.conj(Yd[a])*np.conj(Y(k,q,TH,PH))*Yd[cc])
        g2=integ(np.conj(Yd[b])*Y(k,q,TH,PH)*Yd[d])
        s+=g1*g2
    return (4*np.pi/(2*k+1)*s).real
def build(F):
    H=sps.csr_matrix((Nst,Nst))
    for i in range(5):
        for j in range(5):
            if abs(h[i,j])<1e-14: continue
            for s in (0,1):
                H=H+ h[i,j].real*(cd[2*i+s]@c[2*j+s])
    for p in range(10):
        for q in range(10):
            for r in range(10):
                for s_ in range(10):
                    ip,sp_=divmod(p,2); iq,sq=divmod(q,2); ir,sr=divmod(r,2); is_,ss=divmod(s_,2)
                    if sp_!=sr or sq!=ss: continue
                    val=sum(Fk*akval(k,ip,iq,ir,is_) for k,Fk in F.items())
                    if abs(val)<1e-12: continue
                    H=H+0.5*val*(cd[p]@cd[q]@c[s_]@c[r])
    return H
# S^2 operator: S^2 = S-^S+ + Sz(Sz+1)
def Sops():
    Sp=sps.csr_matrix((Nst,Nst)); Sz=sps.csr_matrix((Nst,Nst))
    for i in range(5):
        Sp=Sp+cd[2*i+0]@c[2*i+1]
        Sz=Sz+0.5*(cd[2*i+0]@c[2*i+0]-cd[2*i+1]@c[2*i+1])
    S2=Sp.T@Sp+Sz@Sz-Sz  # S-S+ = S^2 - Sz^2 - Sz  => S^2 = S-S+ + Sz^2 + Sz ; S-S+ = Sp.T@Sp
    return S2
S2=Sops()
