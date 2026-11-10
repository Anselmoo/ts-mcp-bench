cd /; cat > /tmp/tsbench-run-pge5dt8k/d7run.py << 'EOF'
import itertools
import numpy as np
from scipy.special import sph_harm_y
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
        Yc = np.conj(sph_harm_y(k,q,TH,PH))
        Mkq = np.zeros((5,5),complex)
        for a in range(5):
            for c in range(5):
                Mkq[a,c] = np.sum(orbs[a][1]*orbs[c][1]*Yc*W)
        Ang[(k,q)] = Mkq
G = {k: np.zeros((5,5,5,5),complex) for k in (0,2,4)}
for (k,q),Mkq in Ang.items():
    G[k] += 4*np.pi/(2*k+1) * np.einsum('ac,bd->abcd', Mkq, np.conj(Mkq))
nso=10
states = [sum(1<<i for i in c) for c in itertools.combinations(range(nso),7)]
idx = {s:i for i,s in enumerate(states)}
def ann(st,i):
    if not (st>>i)&1: return None,0
    return st & ~(1<<i), (-1)**bin(st & ((1<<i)-1)).count('1')
def cre(st,i):
    if (st>>i)&1: return None,0
    return st | (1<<i), (-1)**bin(st & ((1<<i)-1)).count('1')
# precompute two-body connections (independent of parameters)
conn=[]
for i,s in enumerate(states):
    for a in range(nso):
      for b in range(nso):
        if a==b: continue
        for c in range(nso):
          for d in range(nso):
            if c==d: continue
            if (a//5)!=(c//5) or (b//5)!=(d//5): continue
            st,s1=ann(s,c)
            if st is None: continue
            st,s2=ann(st,d)
            if st is None: continue
            st,s3=cre(st,b)
            if st is None: continue
            st,s4=cre(st,a)
            if st is None: continue
            conn.append((idx[st],i,a%5,b%5,c%5,d%5,0.5*s1*s2*s3*s4))
conn_arr=conn
diag=np.array([sum(eps[o%5] for o in range(nso) if (s>>o)&1) for s in states])
def build(B,C,Dq):
    F = {2:49*B+7*C, 4:12.6*C, 0:0.0}
    V = sum(G[k]*F[k] for k in (0,2,4)).real
    n=len(states); H=np.zeros((n,n))
    H[np.diag_indices(n)] = Dq*diag
    for (j,i,oa,ob,oc,od,sg) in conn_arr:
        H[j,i]+=sg*V[oa,ob,oc,od]
    return H
if __name__=='__main__':
    H=build(1000.,4500.,0.)
    print("sym", np.allclose(H,H.T))
    ev=np.linalg.eigvalsh(H)
    print(np.round(ev[:10]-ev[0],1))
EOF
cd /tmp/tsbench-run-pge5dt8k && python3 -B d7run.py