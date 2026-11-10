mkdir -p /dev/shm/d4 && cd /dev/shm/d4 && cat << 'EOF' > d4.py
import numpy as np
import scipy.sparse as sps
from scipy.special import sph_harm_y
from functools import lru_cache
nt, nph = 30, 60
x, w = np.polynomial.legendre.leggauss(nt)
ph = np.arange(nph)*2*np.pi/nph
CT, PH = np.meshgrid(x, ph, indexing='ij')
W = np.outer(w, np.ones(nph))*(2*np.pi/nph)
TH = np.arccos(CT)
ms=[-2,-1,0,1,2]
def Y(l,m,th,phi): return sph_harm_y(l,m,th,phi)
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
h_unit=-4*t2@t2.conj().T+6*eg@eg.conj().T
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
@lru_cache(None)
def akval(k,a,b,cc,d):
    a,b,cc,d=ms[a],ms[b],ms[cc],ms[d]
    s=0
    for q in range(-k,k+1):
        g1=integ(np.conj(Yd[a])*np.conj(Y(k,q,TH,PH))*Yd[cc])
        g2=integ(np.conj(Yd[b])*Y(k,q,TH,PH)*Yd[d])
        s+=g1*g2
    return float((4*np.pi/(2*k+1)*s).real)
def twobody_ops():
    ops={0:sps.csr_matrix((Nst,Nst)),2:sps.csr_matrix((Nst,Nst)),4:sps.csr_matrix((Nst,Nst))}
    for p in range(10):
        for q in range(10):
            for r in range(10):
                for s_ in range(10):
                    ip,sp_=divmod(p,2); iq,sq=divmod(q,2); ir,sr=divmod(r,2); is_,ss=divmod(s_,2)
                    if sp_!=sr or sq!=ss: continue
                    T=None
                    for k in (0,2,4):
                        v=akval(k,ip,iq,ir,is_)
                        if abs(v)<1e-12: continue
                        if T is None: T=cd[p]@cd[q]@c[s_]@c[r]
                        ops[k]=ops[k]+0.5*v*T
    return ops
OPS=twobody_ops()
def onebody(hmat):
    H=sps.csr_matrix((Nst,Nst))
    for i in range(5):
        for j in range(5):
            if abs(hmat[i,j])<1e-14: continue
            for s in (0,1):
                H=H+float(hmat[i,j].real)*(cd[2*i+s]@c[2*j+s])
    return H
Sp=sps.csr_matrix((Nst,Nst)); Sz=sps.csr_matrix((Nst,Nst))
for i in range(5):
    Sp=Sp+cd[2*i+0]@c[2*i+1]
    Sz=Sz+0.5*(cd[2*i+0]@c[2*i+0]-cd[2*i+1]@c[2*i+1])
S2=(Sp.T@Sp + Sz@Sz + Sz)
def levels(nel, F, hmat, S=1):
    sel=np.where(Ns==nel)[0]
    H=sum(F[k]*OPS[k] for k in (0,2,4)) + onebody(hmat)
    H=H[np.ix_(sel,sel)].toarray()
    S2s=S2[np.ix_(sel,sel)].toarray()
    Q=S2s-S*(S+1)*np.eye(len(sel))
    e,v=np.linalg.eigh(H+1e5*Q@Q)
    out=[e[i] for i in range(len(e)) if abs(v[:,i]@S2s@v[:,i]-S*(S+1))<1e-6 and e[i]<1e5*0.5]
    out=np.array(sorted(out))
    uniq=[]
    for x_ in out:
        if not uniq or abs(x_-uniq[-1][0])>1e-6: uniq.append([x_,1])
        else: uniq[-1][1]+=1
    return uniq
EOF
cat << 'EOF' > run.py
import numpy as np, itertools
from d4 import *
B=1.0; C=4.3*B
F4=441*C/35; F2=(441*B+5*F4)/9
F={0:0.0,2:F2,4:F4}
obs=np.array([22900,23730,24580.])
xs=np.arange(2.0,7.0,0.02)
table=[]
for xx in xs:
    lv=levels(4,F,xx*h_unit,1)
    E0=lv[0][0]
    table.append(([e_-E0 for e_,m in lv[1:8]],[m for e_,m in lv[1:8]]))
best=[]
for xi,xx in enumerate(xs):
    tau,deg=table[xi]
    for trip in itertools.combinations(range(6),3):
        t=np.array([tau[i] for i in trip])
        # least squares B: obs ~ B*t
        Bf=np.dot(t,obs)/np.dot(t,t)
        r=np.sqrt(np.mean((Bf*t-obs)**2))
        best.append((r,xx,Bf,trip,tuple(deg[i] for i in trip)))
best.sort()
for b in best[:12]:
    r,xx,Bf,trip,dg=b
    print("rms=%.1f  Dq/B=%.3f  B=%.1f  Dq=%.0f  levels=%s deg=%s"%(r,xx,Bf,xx*Bf,trip,dg))
EOF
timeout 550 python3 run.py 2>&1 | tail -20