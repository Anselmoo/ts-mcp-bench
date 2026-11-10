cd /tmp/tsbench-run-tnbk5hz6 2>/dev/null || cd /; python3 - << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm
from numpy.polynomial.legendre import leggauss
from scipy.optimize import brentq

x,w = leggauss(30); nphi=60
th = np.arccos(x); ph = np.arange(nphi)*2*np.pi/nphi
TH,PH = np.meshgrid(th,ph,indexing='ij'); W = np.outer(w, np.ones(nphi))*(2*np.pi/nphi)
def Y(l,m): return sph_harm(m,l,PH,TH)
ms=list(range(-2,3))
Yd={m:Y(2,m) for m in ms}
def integ(f): return np.sum(W*f)
Ck={}
for k in (0,2,4):
    M=np.zeros((5,5,5,5),complex)
    for q in range(-k,k+1):
        Ykq=Y(k,q)
        P=np.zeros((5,5),complex); Qm=np.zeros((5,5),complex)
        for i,ma in enumerate(ms):
            for j,mc in enumerate(ms):
                P[i,j]=integ(np.conj(Yd[ma])*np.conj(Ykq)*Yd[mc])
                Qm[i,j]=integ(np.conj(Yd[ma])*Ykq*Yd[mc])
        M += (4*np.pi/(2*k+1))*np.einsum('ac,bd->acbd',P,Qm)
    Ck[k]=M
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
s2=np.sqrt(2)
orbs={'z2':vec({0:1}),'x2y2':vec({2:1/s2,-2:1/s2}),'xy':vec({-2:1/(1j*s2),2:-1/(1j*s2)}),
      'xz':vec({1:-1/s2,-1:1/s2}),'yz':vec({1:1j/s2,-1:1j/s2})}
eg={'z2','x2y2'}
def cubic_h(Dq):
    h=np.zeros((5,5),complex)
    for name,v in orbs.items():
        e = 6*Dq if name in eg else -4*Dq
        h += e*np.outer(v,np.conj(v))
    return h
states=[sum(1<<i for i in c) for c in itertools.combinations(range(10),6)]
idx={s:i for i,s in enumerate(states)}
def spin_orb(p): return p//2, p%2
def apply_ops(state, ops):
    s=state; sign=1
    for typ,p in reversed(ops):
        occ=(s>>p)&1
        if typ=='c' and occ: return None,0
        if typ=='d' and not occ: return None,0
        n=bin(s & ((1<<p)-1)).count('1')
        sign*= (-1)**n
        s^=(1<<p)
    return s,sign
# precompute V in spin-orbital indices (orbital m index o, spin sigma=p%2)
Vo={}  # (oa,ob,oc,od) orbital-level ; spin deltas applied separately
def build_parts(Dq,B,C):
    F4=441*C/35.0; F2=(441*B+5*F4)/9.0
    Fk={0:0.0,2:F2,4:F4}
    Vorb=sum(Fk[k]*Ck[k] for k in (0,2,4))
    h1=cubic_h(Dq)
    N=len(states)
    H1=np.zeros((N,N),complex); H2=np.zeros((N,N),complex)
    # build one-body and two-body operators
    for i,s in enumerate(states):
        for a in range(10):
            for b in range(10):
                oa,sa=spin_orb(a); ob,sb=spin_orb(b)
                if sa!=sb or abs(h1[oa,ob])<1e-14: continue
                t,sg=apply_ops(s,[('c',a),('d',b)])
                if t is None: continue
                H1[idx[t],i]+=sg*h1[oa,ob]
        for a in range(10):
            for b in range(10):
                if a==b: continue
                oa,sa=spin_orb(a); ob,sb=spin_orb(b)
                for c in range(10):
                    oc,sc=spin_orb(c)
                    if sc!=sa: continue
                    for d in range(10):
                        od,sd=spin_orb(d)
                        if sd!=sb or c==d: continue
                        v=Vorb[oa,ob,oc,od]
                        if abs(v)<1e-12: continue
                        t,sg=apply_ops(s,[('c',a),('c',b),('d',d),('d',c)])
                        if t is None: continue
                        H2[idx[t],i]+=0.5*sg*v
    return H1,H2
# S^2 and Sz
N=len(states)
Sz=np.zeros((N,N)); Sp=np.zeros((N,N))
for i,s in enumerate(states):
    Sz[i,i]=sum((0.5 if p%2==0 else -0.5) for p in range(10) if (s>>p)&1)
    for o in range(5):
        pa,pb=2*o,2*o+1
        if (s>>pb)&1 and not (s>>pa)&1:
            t,sg=apply_ops(s,[('c',pa),('d',pb)])
            Sp[idx[t],i]+=sg
S2=Sp.T@Sp+Sz@Sz-Sz
sel=[i for i,s in enumerate(states) if abs(Sz[i,i])<1e-9]
w_,v_=np.linalg.eigh(S2[np.ix_(sel,sel)])
Psing=v_[:,np.abs(w_)<1e-6]
Psing_full=np.zeros((N,Psing.shape[1]),complex); Psing_full[sel,:]=Psing
# Only ops in Sz=0 sector; singlet projection
def singlet_levels(Dq,B,C=None):
    if C is None: C=4*B
    H1,H2=build_parts(Dq,B,C)
    H=H1+H2
    Hs=Psing_full.conj().T@H@Psing_full
    return np.sort(np.linalg.eigvalsh(Hs).real)
# verify: free ion term energies with B only, Dq=0. Ground 1S? Check d6 free ion lowest singlet ~ 1I etc.
e=singlet_levels(0.0,1000.0)
print("free-ion singlets (Dq=0,B=1000):", np.round(e[:10],1))
print("count singlets", len(e))
np.save('/dev/null',[])
import pickle
EOF