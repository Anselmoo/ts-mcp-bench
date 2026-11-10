cd /; python3 -B - << 'EOF'
import itertools
import numpy as np
from scipy.special import sph_harm
from scipy.optimize import least_squares
nt, nphi = 40, 80
x, w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.arange(nphi)*2*np.pi/nphi
TH, PH = np.meshgrid(th, ph, indexing='ij')
W = np.outer(w, np.full(nphi, 2*np.pi/nphi))
X = np.sin(TH)*np.cos(PH); Y = np.sin(TH)*np.sin(PH); Z = np.cos(TH)
def norm(f): return np.sqrt(np.sum(f*f*W))
orbs = [('t2g',X*Y),('t2g',Y*Z),('t2g',Z*X),('eg',X**2-Y**2),('eg',3*Z**2-1)]
orbs = [(s, f/norm(f)) for s,f in orbs]
Mo = np.array([[np.sum(a[1]*b[1]*W) for b in orbs] for a in orbs])
assert np.allclose(Mo, np.eye(5))
eps = np.array([-4.0 if s=='t2g' else 6.0 for s,_ in orbs])
Ang = {}
for k in (0,2,4):
    for q in range(-k,k+1):
        Yc = np.conj(sph_harm(q,k,PH,TH))
        Mkq = np.zeros((5,5),complex)
        for a in range(5):
            for c in range(5):
                Mkq[a,c] = np.sum(orbs[a][1]*orbs[c][1]*Yc*W)
        Ang[(k,q)] = Mkq
G = {k: np.zeros((5,5,5,5),complex) for k in (0,2,4)}
for (k,q),Mkq in Ang.items():
    G[k] += 4*np.pi/(2*k+1) * np.einsum('ac,bd->abcd', Mkq, np.conj(Mkq))
# check: F0 coefficient G[0] should be ~ identity-like; check G2/G4 values are real
print("G0 diag sample", G[0][0,0,0,0].real, G[0][0,1,0,1].real)
nso=10
states = [sum(1<<i for i in c) for c in itertools.combinations(range(nso),7)]
idx = {s:i for i,s in enumerate(states)}
def ann(st,i):
    if not (st>>i)&1: return None,0
    return st & ~(1<<i), (-1)**bin(st & ((1<<i)-1)).count('1')
def cre(st,i):
    if (st>>i)&1: return None,0
    return st | (1<<i), (-1)**bin(st & ((1<<i)-1)).count('1')
def build(B,C,Dq):
    F = {2:49*B+7*C, 4:12.6*C, 0:0.0}
    V = sum(G[k]*F[k] for k in (0,2,4))
    n=len(states); H=np.zeros((n,n))
    for i,s in enumerate(states):
        H[i,i] += sum(Dq*eps[o%5] for o in range(nso) if (s>>o)&1)
    for i,s in enumerate(states):
        for a in range(nso):
          for b in range(nso):
            if a==b: continue
            for c in range(nso):
              for d in range(nso):
                if c==d: continue
                oa,sa=a%5,a//5; ob,sb=b%5,b//5; oc,sc=c%5,c//5; od,sd=d%5,d//5
                if sa!=sc or sb!=sd: continue
                v=V[oa,ob,oc,od].real
                if abs(v)<1e-12: continue
                st,s1=ann(s,c)
                if st is None: continue
                st,s2=ann(st,d)
                if st is None: continue
                st,s3=cre(st,b)
                if st is None: continue
                st,s4=cre(st,a)
                if st is None: continue
                H[idx[st],i]+=0.5*v*s1*s2*s3*s4
    return H
H=build(1000.,4500.,0.)
print("sym", np.allclose(H,H.T))
ev=np.linalg.eigvalsh(H)
print(np.round(ev[:10]-ev[0],1))
np.save('/dev/null',H) if False else None
import pickle, sys
# Save matrix for later param fitting via stdin-only approach: rebuild each time
EOF