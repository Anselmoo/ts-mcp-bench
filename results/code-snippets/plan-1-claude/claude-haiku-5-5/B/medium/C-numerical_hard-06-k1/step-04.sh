
cat << 'EOF' > /dev/shm/d6.py
import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import least_squares
N=40
x,w=np.polynomial.legendre.leggauss(N)
phi=np.linspace(0,2*np.pi,2*N,endpoint=False)
T,P=np.meshgrid(np.arccos(x),phi,indexing='ij'); W=np.outer(w,np.ones(2*N))*(2*np.pi/(2*N))
X=np.sin(T)*np.cos(P);Y=np.sin(T)*np.sin(P);Z=np.cos(T)
c=np.sqrt(15/(4*np.pi))
d=[np.sqrt(5/(16*np.pi))*(3*Z**2-1), c*X*Z, c*Y*Z, c*X*Y, c/2*(X**2-Y**2)]
# real orbitals index: 0 z2,1 xz,2 yz,3 xy,4 x2y2
def ang(k):
    Yc={m:sph_harm(m,k,P,T) for m in range(-k,k+1)}
    A=np.zeros((2*k+1,5,5),complex)
    for i,m in enumerate(range(-k,k+1)):
        for a in range(5):
            for cc in range(5):
                A[i,a,cc]=np.sum(W*d[a]*Yc[m]*d[cc])
    G=np.zeros((5,5,5,5),complex)
    Bm=np.zeros((2*k+1,5,5),complex)
    for i,m in enumerate(range(-k,k+1)):
        for b in range(5):
            for dd in range(5):
                Bm[i,b,dd]=np.sum(W*d[b]*np.conj(Yc[m])*d[dd])
    G=np.einsum('iac,ibd->acbd',A,Bm)*4*np.pi/(2*k+1)
    return G
Gs={k:ang(k) for k in (0,2,4)}
print('imag max',max(np.abs(Gs[k].imag).max() for k in Gs))
G0,G2,G4=[Gs[k].real for k in (0,2,4)]
# spin-orbitals: index = 2*orb + spin
orbs=[]
def build_H(Dq,F2,F4):
    F0=0.0
    # one-electron
    h1=np.zeros((5,5)); 
    h1=np.diag([6*Dq,-4*Dq,-4*Dq,-4*Dq,6*Dq])
    # two-electron tensor V[a,b,c,d] for spin orbitals <ab|1/r|cd>
    Vo=F0*G0+F2*G2+F4*G4   # orbital (real) <ab|1/r|cd> with a,c for electron1, b,d electron2 -> G[a,c,b,d]
    # build determinant basis
    states=[s for s in itertools.combinations(range(10),6)]
    idx={s:i for i,s in enumerate(states)}
    n=len(states)
    H=np.zeros((n,n))
    def occ_to_bits(s): return sum(1<<i for i in s)
    for j,s in enumerate(states):
        occ=set(s)
        # one-body
        for p in s:
            # diagonal
            pass
        # build by applying operators
        sv=set(s)
        for p in sv:
            H[j,j]+=h1[p//2,p//2] if p%2==0 or True else 0
        # two-body: H2 = 1/2 sum V[a,b,c,d] a+_a a+_b a_d a_c, with spin-orbital V = Vo[orb_a,orb_c,orb_b,orb_d]*delta(spin_a,spin_c)*delta(spin_b,spin_d)
        for a in range(10):
          for cc in range(10):
            if (a%2)!=(cc%2): continue
            for b in range(10):
              for dd in range(10):
                if (b%2)!=(dd%2): continue
                v=Vo[a//2,cc//2,b//2,dd//2]
                if abs(v)<1e-12: continue
                # a_c first then a_d then a+_b then a+_a ; operator a+_a a+_b a_d a_c
                # acting on |s>: annihilate cc, then dd, create b, then a
                if cc not in sv: continue
                l=list(s); 
                sign=1
                pos=l.index(cc); sign*=(-1)**pos; l.pop(pos)
                if dd in l: continue
                pos=sorted(l+[dd]).index(dd); sign*=(-1)**(sum(1 for q in l if q<dd)); l=sorted(l+[dd])
                if b in l: continue
                sign*=(-1)**(sum(1 for q in l if q<b)); l=sorted(l+[b])
                if a in l and a!=cc: 
                    continue
                # a+_a
                if a in l: continue
                sign*=(-1)**(sum(1 for q in l if q<a)); l=sorted(l+[a])
                t=tuple(l)
                if t in idx:
                    H[idx[t],j]+=0.5*sign*v
    return H,states
EOF
echo done