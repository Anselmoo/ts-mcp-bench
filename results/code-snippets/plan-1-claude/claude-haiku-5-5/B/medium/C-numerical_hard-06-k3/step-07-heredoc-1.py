import numpy as np, itertools
from scipy.special import sph_harm_y
from numpy.polynomial.legendre import leggauss
from scipy.optimize import least_squares
x,w = leggauss(30); nphi=60
th = np.arccos(x); ph = np.arange(nphi)*2*np.pi/nphi
TH,PH = np.meshgrid(th,ph,indexing='ij'); W = np.outer(w, np.ones(nphi))*(2*np.pi/nphi)
def Y(l,m): return sph_harm_y(l,m,TH,PH)
ms=list(range(-2,3)); Yd={m:Y(2,m) for m in ms}
def integ(f): return np.sum(W*f)
Ck={}
for k in (0,2,4):
    M=np.zeros((5,5,5,5),complex)  # M[a,b,c,d] = <ab|V_k|cd> angular
    for q in range(-k,k+1):
        Ykq=Y(k,q)
        P=np.zeros((5,5),complex); Qm=np.zeros((5,5),complex)
        for i,ma in enumerate(ms):
            for j,mc in enumerate(ms):
                P[i,j]=integ(np.conj(Yd[ma])*np.conj(Ykq)*Yd[mc])
                Qm[i,j]=integ(np.conj(Yd[ma])*Ykq*Yd[mc])
        # <ab|V|cd> = P[a,c]*Q[b,d]
        M += (4*np.pi/(2*k+1))*np.einsum('ac,bd->abcd',P,Qm)
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
        h += (6*Dq if name in eg else -4*Dq)*np.outer(v,np.conj(v))
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
        sign*= (-1)**bin(s & ((1<<p)-1)).count('1')
        s^=(1<<p)
    return s,sign
N=len(states)
Sz=np.zeros((N,N)); Sp=np.zeros((N,N))
for i,s in enumerate(states):
    Sz[i,i]=sum((0.5 if p%2==0 else -0.5) for p in range(10) if (s>>p)&1)
    for o in range(5):
        pa,pb=2*o,2*o+1
        if (s>>pb)&1 and not (s>>pa)&1:
            t,sg=apply_ops(s,[('c',pa),('d',pb)]); Sp[idx[t],i]+=sg
S2=Sp.T@Sp+Sz@Sz-Sz
sel=[i for i,s in enumerate(states) if abs(Sz[i,i])<1e-9]
w_,v_=np.linalg.eigh(S2[np.ix_(sel,sel)])
Pf=np.zeros((N,(np.abs(w_)<1e-6).sum()),complex); Pf[sel,:]=v_[:,np.abs(w_)<1e-6]
# singlet sector full (for S=0 check); also the full Hilbert H
one=[];two=[]
for a in range(10):
    for b in range(10):
        oa,sa=spin_orb(a); ob,sb=spin_orb(b)
        if sa==sb:
            rows=[]
            for i,s in enumerate(states):
                t,sg=apply_ops(s,[('c',a),('d',b)])
                if t is not None: rows.append((idx[t],i,sg))
            one.append(((oa,ob),rows))
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
                rows=[]
                for i,s in enumerate(states):
                    t,sg=apply_ops(s,[('c',a),('c',b),('d',d),('d',c)])
                    if t is not None: rows.append((idx[t],i,sg))
                two.append(((oa,ob,oc,od),rows))
def H_of(Dq,B,C):
    F4=441*C/35.0; F2=(441*B+5*F4)/9.0
    Vorb=sum({0:0.0,2:F2,4:F4}[k]*Ck[k] for k in (0,2,4))
    h1=cubic_h(Dq)
    H=np.zeros((N,N),complex)
    for (oa,ob),rows in one:
        for r,c,sg in rows: H[r,c]+=sg*h1[oa,ob]
    for (oa,ob,oc,od),rows in two:
        v=Vorb[oa,ob,oc,od]
        if abs(v)<1e-12: continue
        for r,c,sg in rows: H[r,c]+=0.5*sg*v
    return H
H0=H_of(0,1000,4000)
ev=np.sort(np.linalg.eigvalsh(H0))
# group degeneracies
groups=[]; 
for e in ev:
    if groups and abs(e-groups[-1][0])<1e-3: groups[-1][1]+=1
    else: groups.append([e,1])
print("free-ion terms (E-E0, mult):")
print([(round(g[0]-ev[0],1),g[1]) for g in groups])
Hs=Pf.conj().T@H0@Pf
print("singlet energies free ion:", np.round(np.sort(np.linalg.eigvalsh(Hs).real)-ev[0],1))
import pickle
